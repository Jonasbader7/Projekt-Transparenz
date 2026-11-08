"""Local catalogue of SEC observations. Explicit gaps, no invented global denominator."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import replace
from datetime import UTC, datetime

from sqlalchemy import select

from transparenz.config.licensing import license_block_reasons
from transparenz.config.settings import CONFIG_DIR, get_settings
from transparenz.database.models import MarketRecordRow, UpdateRun
from transparenz.database.repository import active_versions
from transparenz.entities.enums import UpdateStatus
from transparenz.entities.markets import MarketObservation
from transparenz.ingestion.external import atomic_json, atomic_write, encoded
from transparenz.services.context import AppContext, create_context
from transparenz.services.swiss_foundation import foundation_lock

EXPORT_SCHEMA = 3  # Increase when parsing, identity, classification or viewer semantics change.


def create_market_context() -> AppContext:
    settings = get_settings()
    settings = replace(settings, sources_config=CONFIG_DIR / "market_sources.toml",
                       database_url="sqlite:///" +
                       (settings.processed_dir / "markets.sqlite").as_posix(),
                       raw_dir=settings.raw_dir / "external/manifests")
    return create_context(settings)


def _evidence(row: dict, source: str) -> dict:
    return {"source_key": source, **{k: row.get(k) for k in
            ("source_url", "original_sha256", "accession", "report_date", "filing_date")}}


def build_catalogue(records: dict[str, list[dict]]) -> tuple[list[dict], dict]:
    """Only exact SEC class IDs merge. CIK is the registrant, never a class identity."""
    listings = records.get("sec_exchange_tickers", [])
    current = records.get("sec_fund_classes", [])
    reports = records.get("sec_ncen", [])
    funds = defaultdict(list)
    report_classes = defaultdict(list)
    class_claims = defaultdict(list)
    for row in reports:
        if row["record_type"] == "ncen_fund":
            funds[(row["cik"], row["series_id"])].append(row)
        else:
            report_classes[row["fund_id"]].append(row)
            if row["class_id"] and row["class_id"] != "C000000000":
                class_claims[row["class_id"]].append(row)
    current_classes = defaultdict(list)
    for row in current:
        current_classes[row["class_id"]].append(row)
    items = []
    counts = Counter()
    for class_id in sorted(set(current_classes) | set(class_claims)):
        claims = current_classes[class_id] + class_claims[class_id]
        identities = {(r["cik"], r["series_id"]) for r in claims}
        conflict = len(identities) != 1
        cik, series = next(iter(identities)) if not conflict else (None, None)
        candidates = funds.get((cik, series), [])
        best = max(((r["report_date"], r["filing_date"]) for r in candidates), default=None)
        latest = [r for r in candidates if (r["report_date"], r["filing_date"]) == best]
        # Ties stay unresolved: don't choose an accession by lexical order.
        report = latest[0] if len(latest) == 1 else None
        members = report_classes[report["fund_id"]] if report else []
        own = [r for r in members if r["class_id"] == class_id]
        classification = "fund_class_unclassified"
        basis = "Kein eindeutiger aktueller N-CEN-Nachweis für die Anteilsklasse."
        if conflict:
            classification = "identity_conflict"
            basis = "Class-ID mit widersprüchlichem Registrant/Serie; keine Fusion."
        elif report and own and report["series_is_etf"] is True:
            classification = "etf_series_class_unresolved"
            basis = "Serie meldet ETF; bei mehreren Klassen bleibt die einzelne Klasse offen."
            if len(members) == 1 and len(own) == 1:
                classification = "etf_reported_single_class"
                basis = "N-CEN: Serie meldet ETF und genau diese eine Anteilsklasse."
        elif report and own and report["series_is_etf"] is False:
            classification = "fund_class_reported_non_etf"
            basis = "N-CEN: Serie meldet zum Berichtsdatum IS_ETF=N."
        counts[classification] += 1
        # Current search symbols and historical reported symbols remain separate.
        tickers = sorted({r["ticker"] for r in current_classes[class_id] if r["ticker"]})
        old_tickers = sorted({r["ticker"] for r in own if r["ticker"]})
        items.append({
            "catalogue_key": "sec:class:" + class_id, "name": report["name"] if report else None,
            "class_name": own[0]["class_name"] if len(own) == 1 else None,
            "registrant_cik": cik, "series_id": series, "class_id": class_id,
            "isin": None, "tickers": tickers, "reported_tickers": old_tickers,
            "exchange": None, "market_scope": "US SEC", "classification": classification,
            "classification_basis": basis, "report_date": report["report_date"] if report else None,
            "filing_date": report["filing_date"] if report else None,
            "current_sec_ticker_reference": bool(current_classes[class_id]),
            "currently_tradable": None, "issuer_country": None, "identity_conflict": conflict,
            "evidence": [_evidence(r, "sec_fund_classes") for r in current_classes[class_id]] +
                        ([_evidence(report, "sec_ncen")] if report else []),
            "conflicting_claims": claims if conflict else []})
    for row in listings:
        counts["listed_instrument_unclassified"] += 1
        items.append({
            "catalogue_key": "sec:ticker-claim:" + row["record_key"], "name": row["name"],
            "class_name": None, "registrant_cik": row["cik"], "series_id": None,
            "class_id": None, "isin": None, "tickers": [row["ticker"]], "reported_tickers": [],
            "exchange": row["exchange"], "market_scope": "US SEC",
            "classification": "listed_instrument_unclassified",
            "classification_basis": "SEC-Ticker-/Börsenzuordnung; Instrumenttyp unbestätigt.",
            "report_date": None, "filing_date": None, "current_sec_ticker_reference": True,
            "currently_tradable": None, "issuer_country": None, "identity_conflict": False,
            "evidence": [_evidence(row, "sec_exchange_tickers")], "conflicting_claims": []})
    return items, dict(counts)


def export_market(ctx: AppContext) -> dict:
    output = ctx.settings.processed_dir / "market"
    with ctx.session_factory() as session:
        versions = active_versions(session)
        records = {}
        source_status = {}
        for cfg in ctx.catalog.sources:
            version = versions.get(cfg.key)
            last = session.scalars(select(UpdateRun).where(UpdateRun.source_key == cfg.key)
                                   .order_by(UpdateRun.id.desc())).first()
            source_status[cfg.key] = {
                "active_version": version.id if version else None,
                "hash": version.content_hash if version else None,
                "fetched_at": version.fetched_at.isoformat() if version else None,
                "data_as_of": str(version.data_as_of) if version and version.data_as_of else None,
                "license_block_reasons": license_block_reasons(cfg, datetime.now(UTC).date()),
                "last_run": last.status if last else "never_run",
                "last_message": last.message if last else None,
                "attribution": cfg.attribution}
            payloads = session.scalars(select(MarketRecordRow.payload_json).where(
                MarketRecordRow.dataset_version_id == version.id)) if version else []
            records[cfg.key] = [MarketObservation.model_validate_json(r).model_dump(mode="json")
                                for r in payloads]
    items, counts = build_catalogue(records)
    report = {
        "export_schema_version": EXPORT_SCHEMA, "complete_world": False,
        "world_coverage_percent": None, "unique_instrument_count": None,
        "catalogue_entry_count": len(items), "classification_counts": counts,
        "raw_observation_counts": {k: len(v) for k, v in records.items()}, "sources": source_status,
        "unresolved_ncen_observations": sum(
            not r["series_id"] or (r["record_type"] == "ncen_class" and not r["class_id"])
            for r in records.get("sec_ncen", [])),
        "coverage": [
            {"market": "US SEC", "status": "partial", "complete": False,
             "gaps": ["Tickerlisten ohne garantierte Abdeckung und ohne verlässlichen Typ.",
                      "N-CEN jährlich; Schema-3.1-Meldungen fehlen laut SEC im Bulkbestand.",
                      "Mehrklassen-ETF-Serien bleiben auf Anteilsklassenebene unbestätigt.",
                      "Keine ISIN/MIC-Währungsauflösung; kein Echtzeit-Handelsstatus."]},
            {"market": "Schweiz / SIX", "status": "rights_unresolved", "complete": False},
            {"market": "Europa / FIRDS", "status": "rights_unresolved", "complete": False},
            {"market": "Übrige Weltmärkte", "status": "not_integrated", "complete": False}],
        "notes": ["Katalogeinträge sind Quellenbeobachtungen, "
                  "keine Zahl weltweit eindeutiger Papiere.",
                  "SEC-Registranten können ausländisch sein. US SEC ist kein Emittentendomizil.",
                  "Fonds-Anteilsklassen enthalten auch nicht börsengehandelte Publikumsfonds.",
                  "Fehlende Klassifikation bedeutet unbekannt, nicht automatisch Aktie/ETF.",
                  "Keine Kurse, Fondspositionen, Anlageempfehlungen oder Nachhaltigkeitsurteile."]}
    fingerprint = hashlib.sha256(encoded({"schema": EXPORT_SCHEMA,
                                         "versions": {k: v["hash"] for k, v in
                                                      source_status.items()}})).hexdigest()[:24]
    generation = output / "generations" / fingerprint
    if not all((generation / name).is_file() for name in
               ("catalogue.json", "quality_report.json", "catalogue.html")):
        atomic_json(generation / "catalogue.json", items)
        atomic_json(generation / "quality_report.json", report)
        from transparenz.reports.market_catalog import render_catalogue

        atomic_write(generation / "catalogue.html", render_catalogue(items, report).encode("utf-8"))
    atomic_json(output / "latest_status.json", report)
    # Publish the pointer only when all files have been built.
    atomic_json(output / "current.json", {"generation": "generations/" + fingerprint,
                                          "entry_count": len(items)})
    return report


def update_market(force: bool = False, source: str | None = None,
                  export_only: bool = False) -> tuple[dict, bool]:
    folder = get_settings().processed_dir / "market"
    with foundation_lock(folder):
        ctx = create_market_context()
        try:
            failed = False
            if not export_only:
                configs = [ctx.catalog.source(source)] if source else ctx.catalog.sources
                for cfg in configs:
                    outcome = ctx.updates.run_source(cfg.key, force=force, trigger="market-update")
                    print(f"{cfg.key}: {outcome.status.value}: {outcome.message}", flush=True)
                    for error in outcome.errors[:5]:
                        print(error, flush=True)
                    failed |= outcome.status in {UpdateStatus.FEHLGESCHLAGEN, UpdateStatus.GESPERRT}
            report = export_market(ctx)
            pointer = json.loads((folder / "current.json").read_bytes())
            print(json.dumps(report["classification_counts"], ensure_ascii=False, indent=2))
            print(f"Katalog öffnen: {folder / pointer['generation'] / 'catalogue.html'}")
            print("Weltweite Vollständigkeit: nicht erreicht; Abdeckung im Qualitätsbericht.")
            return report, failed
        finally:
            ctx.engine.dispose()


def search_market(query: str, limit: int = 20) -> list[dict]:
    folder = get_settings().processed_dir / "market"
    pointer = json.loads((folder / "current.json").read_bytes())
    generation = (folder / pointer["generation"]).resolve()
    if not generation.is_relative_to((folder / "generations").resolve()):
        raise ValueError("Ungültiger Exportpfad")
    items = json.loads((generation / "catalogue.json").read_bytes())
    needle = query.casefold()
    matches = [r for r in items if needle in " ".join(str(r.get(k) or "") for k in
               ("name", "class_name", "registrant_cik", "series_id", "class_id", "tickers",
                "reported_tickers")).casefold()]
    # Exact current ticker first: AAPL should show Apple before funds mentioning AAPL.
    matches.sort(key=lambda r: not any(t.casefold() == needle for t in r["tickers"]))
    return matches[:limit]
