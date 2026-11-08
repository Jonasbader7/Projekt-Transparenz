"""Local Swiss foundation: same update manager, separate DB, reproducible exports."""
from __future__ import annotations

import json
import logging
import os
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from transparenz.config.catalog import SourceConfig
from transparenz.config.licensing import license_block_reasons
from transparenz.config.settings import CONFIG_DIR, Settings, get_settings
from transparenz.database.models import UpdateRun
from transparenz.database.repository import active_versions
from transparenz.entities.enums import UpdateStatus
from transparenz.entities.identifiers import normalize_company_name
from transparenz.ingestion.external import atomic_json, atomic_write, encoded, normalize_uid
from transparenz.services.context import AppContext, create_context

log = logging.getLogger(__name__)
EXPORT_SCHEMA_VERSION = 1  # Increase when parsing/merging changes exported data semantics.
EXPORT_FILES = (
    "companies", "identified_companies", "securities", "security_candidates", "funds",
    "facilities", "possible_duplicates", "identifier_conflicts", "companies_without_lei",
    "unresolved_relationships", "excluded_records", "quarantined_identifiers",
)


def _source_status(cfg: SourceConfig, last: UpdateRun | None) -> dict:
    return {
        "license_block_reasons": license_block_reasons(cfg, datetime.now(UTC).date()),
        "license": cfg.model_dump(mode="json"), "enabled": cfg.enabled,
        "disabled_reason": cfg.disabled_reason,
        "latest_update_status": last.status if last else "never_run",
        "latest_update_message": last.message if last else None,
        "latest_update_errors": json.loads(last.errors_json or "[]") if last else [],
    }


def _reuse_current_export(ctx: AppContext) -> dict | None:
    """Reuse a complete generation only when its data versions and schema still match.

    This is a freshness check, not a full raw-data audit. Immutable generations stay
    unchanged; current operational/licensing diagnostics go to latest_status.json.
    """
    output = ctx.settings.processed_dir / "swiss"
    try:
        pointer = json.loads((output / "current.json").read_bytes())
        generation = (output / pointer["generation"]).resolve()
        if not generation.is_relative_to((output / "generations").resolve()):
            return None
        previous = json.loads((generation / "quality_report.json").read_bytes())
        if previous.get("export_schema_version", 1) != EXPORT_SCHEMA_VERSION:
            return None
        if pointer["counts"] != previous["counts"]:
            return None
        if any(not (generation / f"{name}.json").is_file() for name in EXPORT_FILES):
            return None
        if set(previous["sources"]) != {cfg.key for cfg in ctx.catalog.sources}:
            return None
        report = {**previous, "sources": {}}
        with ctx.session_factory() as session:
            versions = active_versions(session)
            if set(versions) != {k for k, s in previous["sources"].items()
                                 if s["active_version"] is not None}:
                return None
            for cfg in ctx.catalog.sources:
                old = previous["sources"][cfg.key]
                active = versions.get(cfg.key)
                if active is not None and (old["active_version"] != active.id
                                           or old["manifest_sha256"] != active.content_hash):
                    return None
                last = session.scalars(select(UpdateRun).where(UpdateRun.source_key == cfg.key)
                                       .order_by(UpdateRun.id.desc())).first()
                report["sources"][cfg.key] = {**old, **_source_status(cfg, last)}
        report.update(checked_at=datetime.now(UTC).isoformat(), reused_export=True,
                      generation=pointer["generation"], export_schema_version=EXPORT_SCHEMA_VERSION)
        atomic_json(output / "latest_status.json", report)
        return report
    except (OSError, ValueError, KeyError, TypeError):
        # A missing/incomplete old export must be regenerated from active versions.
        return None


def create_swiss_context(settings: Settings | None = None) -> AppContext:
    settings = settings or get_settings()
    root = settings.project_root
    return create_context(replace(
        settings, sources_config=CONFIG_DIR / "swiss_sources.toml",
        database_url=f"sqlite:///{(root / 'data/processed/swiss.sqlite').as_posix()}",
        raw_dir=root / "data/raw/external/manifests"))


def resolve_companies(attributes: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    """Merge only exact unambiguous identifiers; never similar names.

    UID shared by multiple LEIs is quarantined (not a first-match merge).
    Name equality produces review candidates only.
    """
    uid_leis: dict[str, set[str]] = defaultdict(set)
    for row in attributes:
        if row.get("uid") and row.get("lei"):
            uid_leis[row["uid"]].add(row["lei"])
    conflicts = [{"uid": uid, "leis": sorted(leis), "reason": "multiple_leis_for_uid"}
                 for uid, leis in sorted(uid_leis.items()) if len(leis) > 1]
    merged: dict[str, dict] = {}
    for original in attributes:
        row = dict(original)
        uid, lei = row.get("uid"), row.get("lei")
        if uid and len(uid_leis[uid]) == 1 and not lei:
            lei = next(iter(uid_leis[uid]))
        # UID conflicts preserve source records, including the UID-only record.
        key = f"lei:{lei}" if lei else row["company_key"]
        item = merged.setdefault(key, {
            "company_key": key, "name": row["name"], "lei": lei, "uid": uid,
            "country": row.get("country"), "wikidata_id": row.get("wikidata_id"),
            "exchange": None, "equity_isin": None, "ticker": None, "industry": None,
            "parent": None, "sources": [], "source_records": [],
            "identity_status": "identifier_conflict" if uid and len(uid_leis[uid]) > 1
            else "identified", "identity_method": "exact_lei_or_uid"})
        for field_name in ("uid", "country", "wikidata_id"):
            if item.get(field_name) is None:
                item[field_name] = row.get(field_name)
        item["sources"].append(row["source_key"])
        item["source_records"].append(row)
    names: dict[str, list[str]] = defaultdict(list)
    for key, row in merged.items():
        row["sources"] = sorted(set(row["sources"]))
        names[normalize_company_name(row["name"])].append(key)
    duplicates = [{"normalized_name": name, "company_keys": sorted(keys),
                   "status": "review_only_not_merged"}
                  for name, keys in sorted(names.items()) if len(keys) > 1]
    return sorted(merged.values(), key=lambda r: r["company_key"]), conflicts, duplicates


def export_foundation(ctx: AppContext, *, reuse_existing: bool = True) -> dict:
    """Export only active, hash-verified versions into an immutable generation.

    current.json is atomically switched after all files exist. A failed source can
    coexist with its previous active snapshot and is visible in the quality report.
    """
    if reuse_existing and (reused := _reuse_current_export(ctx)) is not None:
        print("Daten unverändert: vorhandener Export wird weiterverwendet.", flush=True)
        return reused
    print("Export wird aus aktiven Datenständen aufgebaut; das kann einige Minuten dauern.",
          flush=True)
    attributes, funds, facilities, unresolved, excluded, candidates = [], [], [], [], [], []
    quarantined = []
    source_conflicts = []
    source_reports = {}
    with ctx.session_factory() as session:
        versions = active_versions(session)
        for cfg in ctx.catalog.sources:
            last = session.scalars(select(UpdateRun).where(UpdateRun.source_key == cfg.key)
                                   .order_by(UpdateRun.id.desc())).first()
            source_reports[cfg.key] = {**_source_status(cfg, last), "active_version": None}
            version = versions.get(cfg.key)
            if version is None:
                continue
            parsed = ctx.updates.adapter(cfg.key).parse(Path(version.raw_path).read_bytes())
            if not parsed.is_valid:
                raise ValueError(f"Aktive Rohdaten beschädigt: {cfg.key}: {parsed.errors}")
            extra = parsed.extra
            attributes.extend(extra.get("company_attributes", []))
            funds.extend(extra.get("funds", []))
            facilities.extend(extra.get("facilities", []))
            unresolved.extend(extra.get("unresolved_relationships", []))
            excluded.extend(extra.get("excluded", []))
            candidates.extend(extra.get("security_candidates", []))
            quarantined.extend(extra.get("quarantined_identifiers", []))
            source_conflicts.extend(extra.get("identifier_conflicts", []))
            source_reports[cfg.key].update(
                active_version=version.id, manifest_sha256=version.content_hash,
                manifest_path=version.raw_path,
                original_files=json.loads(Path(version.raw_path).read_bytes())["pages"],
                data_as_of=str(parsed.data_as_of) if parsed.data_as_of else None,
                fetched_at=version.fetched_at.isoformat(), coverage=parsed.coverage,
                companies=len(parsed.records["companies"]),
                funds=len(extra.get("funds", [])), facilities=len(extra.get("facilities", [])),
                quarantined_identifiers=len(extra.get("quarantined_identifiers", [])),
                warnings=[str(x) for x in parsed.warnings])
    companies, conflicts, duplicates = resolve_companies(attributes)
    conflicts.extend(source_conflicts)
    by_uid: dict[str, list[str]] = defaultdict(list)
    for company in companies:
        if company.get("uid") and company["identity_status"] != "identifier_conflict":
            by_uid[company["uid"]].append(company["company_key"])
    for facility in facilities:
        attrs = facility["attributes"]
        # Exact validated UID only, irrespective of source column capitalisation.
        uids = {uid for value in attrs.values() if isinstance(value, str)
                and (uid := normalize_uid(value))}
        matches = {key for uid in uids for key in by_uid.get(uid, [])}
        if len(uids) == 1 and len(matches) == 1:
            facility["company_key"] = next(iter(matches))
            facility["mapping_status"] = "exact_uid_operator_only"
    no_lei = [c for c in companies if not c["lei"]]
    # No unreviewed company-level Wikidata ISIN becomes a confirmed equity mapping.
    securities: list[dict] = []
    report = {
        "export_schema_version": EXPORT_SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "counts": {"companies_legal_entities": len(companies),
                   "identified_companies": sum(c["identity_status"] == "identified"
                                               for c in companies),
                   "securities_confirmed": len(securities), "security_candidates": len(candidates),
                   "funds_legal_entities": len(funds),
                   "funds_with_isin": sum(bool(f.get("isin")) for f in funds),
                   "fund_holdings": 0, "facilities": len(facilities),
                   "facilities_exact_uid_matched": sum(bool(f["company_key"]) for f in facilities),
                   "possible_duplicate_groups": len(duplicates),
                   "identifier_conflict_groups": len(conflicts),
                   "companies_without_lei": len(no_lei),
                   "unresolved_relationships": len(unresolved),
                   "excluded_gleif_records": len(excluded)},
        "quarantined_identifier_count": len(quarantined),
        "legal_forms": dict(Counter(str(a.get("legal_form")) for a in attributes
                                     if a["source_key"] == "zefix_lindas")),
        "sources": source_reports,
        "coverage_notes": [
            "Rechtseinheiten umfassen auch Vereine, Stiftungen, Einzelunternehmen usw.",
            "GLEIF FUND ist ein Fondsrechtsträger, kein ETF-Nachweis und keine Anteilsklasse.",
            "Kein vollständiges Schweizer Aktien-/ETF-Universum; keine geprüfte SIX-Abdeckung.",
            "Standorte: nur eindeutige UID zum Betreiber; keine Mutterzurechnung.",
            "Standortemissionen, Vorwürfe, amtliche Feststellungen und Branchenrisiken getrennt.",
            "Kein negativer Befund bedeutet hier keine Nachhaltigkeitsaussage.",
            "Zefix: Abfrageseiten zeitversetzt, kein atomarer Gesamtsnapshot."]}
    output = ctx.settings.processed_dir / "swiss"
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    generation = output / "generations" / stamp
    def identity_summary(company):
        return {k: company.get(k) for k in
                ("company_key", "name", "uid", "lei", "identity_status", "sources")}

    files = {"companies": companies, "identified_companies": [
        identity_summary(c) for c in companies if c["identity_status"] == "identified"],
        "securities": securities, "security_candidates": candidates,
        "funds": funds, "facilities": facilities,
        "possible_duplicates": duplicates, "identifier_conflicts": conflicts,
        "companies_without_lei": [identity_summary(c) for c in no_lei],
        "unresolved_relationships": unresolved,
        "excluded_records": excluded, "quality_report": report}
    files["quarantined_identifiers"] = quarantined
    for name, records in files.items():
        atomic_json(generation / f"{name}.json", records)
    atomic_write(output / "current.json", encoded({"generation": f"generations/{stamp}",
                                                  "counts": report["counts"]}))
    atomic_json(output / "latest_status.json", {
        **report, "generation": f"generations/{stamp}", "reused_export": False,
        "checked_at": datetime.now(UTC).isoformat(),
    })
    return report


@contextmanager
def foundation_lock(folder: Path):
    """OS lock releases even after a process crash; no stale lock-file deletion."""
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "swiss-update.lock").open("a+b") as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError(
                "Ein Schweizer Import/Export läuft bereits; später erneut starten."
            ) from exc
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def update_foundation(force: bool = False, source: str | None = None,
                      export_only: bool = False) -> tuple[dict, bool]:
    with foundation_lock(get_settings().processed_dir):
        return _update_foundation(force, source, export_only)


def _update_foundation(force: bool, source: str | None, export_only: bool) -> tuple[dict, bool]:
    ctx = create_swiss_context()
    failed = False
    try:
        if not export_only:
            configs = [ctx.catalog.source(source)] if source else ctx.catalog.sources
            for cfg in configs:
                if not cfg.enabled and source is None:
                    print(f"{cfg.key}: deaktiviert: "
                          f"{cfg.disabled_reason or 'in Quellenkonfiguration deaktiviert'}",
                          flush=True)
                    continue
                outcome = ctx.updates.run_source(cfg.key, force=force, trigger="swiss-update")
                print(f"{cfg.key}: {outcome.status.value}: {outcome.message}", flush=True)
                for error in outcome.errors[:5]:
                    print(f"  {error}", flush=True)
                failed |= outcome.status in {UpdateStatus.FEHLGESCHLAGEN, UpdateStatus.GESPERRT}
        report = export_foundation(ctx, reuse_existing=not export_only)
        print(json.dumps(report["counts"], ensure_ascii=False, indent=2))
        print(f"Exportzeiger: {ctx.settings.processed_dir / 'swiss/current.json'}")
        return report, failed
    finally:
        ctx.engine.dispose()
