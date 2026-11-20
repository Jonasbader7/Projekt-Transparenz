"""SEC N-PORT im Update-System: eigene Datenbank, Aktualisierung und Qualitätsbericht (D-054).

Alle Messwerte stammen per SQL aus dem aktiven Datenstand; nichts wird geschätzt. Zähler
und Nenner werden immer zusammen ausgewiesen. Was nicht gemessen werden kann (z. B. «LEI bei
GLEIF aktiv» ohne vollständige GLEIF-Liste), steht ausdrücklich als «nicht gemessen» da.
"""

from __future__ import annotations

import json
import statistics
from collections import Counter
from dataclasses import replace
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import select, text

from transparenz.config.settings import (
    CONFIG_DIR,
    get_settings,
    local_data_dir,
    resolve_data_path,
)
from transparenz.database.models import DatasetVersion, UpdateRun
from transparenz.database.repository import active_versions
from transparenz.entities.enums import UpdateStatus
from transparenz.ingestion.external import atomic_json
from transparenz.ingestion.gleif_level1 import latest_snapshot, load_lei_records
from transparenz.ingestion.sec_nport import SOURCE_KEY
from transparenz.services.context import AppContext, create_context
from transparenz.services.provenance import verified_manifest
from transparenz.services.swiss_foundation import foundation_lock

REPORT_SCHEMA = 2


def create_nport_context() -> AppContext:
    settings = get_settings()
    settings = replace(settings, sources_config=CONFIG_DIR / "nport_sources.toml",
                       database_url="sqlite:///" +
                       (settings.processed_dir / "nport.sqlite").as_posix(),
                       raw_dir=settings.raw_dir / "external/manifests")
    return create_context(settings)


def _share(part: int, whole: int) -> dict[str, Any]:
    return {"count": part, "of": whole,
            "percent": round(100 * part / whole, 2) if whole else None}


def _rows(conn, sql: str, **params: Any) -> list[tuple]:
    return [tuple(r) for r in conn.execute(text(sql), params)]


def _one(conn, sql: str, **params: Any) -> Any:
    return conn.execute(text(sql), params).scalar()


def _month(value: Any) -> str:
    return str(value)[:7]


def _summarize(weights: dict[str, int], records: dict[str, Any]) -> dict[str, Any]:
    """LEI zählen (je LEI und gewichtet mit der Zahl der Positionen)."""
    leis = len(weights)
    holdings = sum(weights.values())
    entity: Counter = Counter()
    registration: Counter = Counter()
    weighted: Counter = Counter()
    for lei, n in weights.items():
        rec = records.get(lei)
        if rec is None:
            entity["NOT_FOUND"] += 1
            registration["NOT_FOUND"] += 1
            weighted["not_found"] += n
            continue
        entity[rec.entity_status or "(leer)"] += 1
        registration[rec.registration_status] += 1
        weighted["found"] += n
        if rec.entity_status == "ACTIVE":
            weighted["active"] += n
            if rec.registration_status == "ISSUED":
                weighted["active_and_issued"] += n
    active_issued = sum(1 for lei in weights if (rec := records.get(lei)) is not None
                        and rec.entity_status == "ACTIVE" and rec.registration_status == "ISSUED")
    return {
        "leis": leis,
        "found": _share(leis - entity["NOT_FOUND"], leis),
        "entity_status": {k: _share(v, leis) for k, v in entity.most_common()},
        "registration_status": {k: _share(v, leis) for k, v in registration.most_common()},
        "active_and_issued": _share(active_issued, leis),
        "holdings_weighted": {
            "holdings": holdings,
            "found": _share(weighted["found"], holdings),
            "entity_active": _share(weighted["active"], holdings),
            "entity_active_and_issued": _share(weighted["active_and_issued"], holdings)},
    }


def gleif_check(issuer_counts: dict[str, int], series_leis: set[str], data_dir: Path | None,
                cache_dir: Path | None, nport_hash: str) -> dict[str, Any]:
    """Gemeldete LEI gegen die lokale GLEIF-Liste Level 1 prüfen (Ergebnis zwischengespeichert)."""
    snapshot = latest_snapshot(data_dir) if data_dir is not None else None
    if snapshot is None:
        return {"status": "not_measured", "reason": "Keine lokale GLEIF-Liste Level 1 "
                "(raw/external/gleif_lei2_golden_copy)."}
    cache = (cache_dir / f"gleif_check_{snapshot.sha256[:16]}_{nport_hash[:16]}.json"
             if cache_dir is not None else None)
    if cache is not None and cache.is_file():
        return json.loads(cache.read_bytes())
    assert data_dir is not None
    records, rows = load_lei_records(data_dir / snapshot.path, set(issuer_counts) | series_leis)
    result = {
        "status": "measured",
        "gleif_file": snapshot.as_dict(),
        "gleif_rows_read": rows,
        "issuer_lei": _summarize(issuer_counts, records),
        "series_lei": _summarize({lei: 1 for lei in series_leis}, records),
        "definitions": {
            "found": "LEI steht in der GLEIF-Liste Level 1 (alle je vergebenen LEI).",
            "entity_active": "Entity.EntityStatus = ACTIVE: Rechtsträger besteht laut GLEIF.",
            "issued": "Registration.RegistrationStatus = ISSUED: Datensatz gepflegt; LAPSED = "
                      "Verlängerung überfällig, Angaben evtl. veraltet.",
            "timing": "GLEIF-Stand vom Stichtag der Datei, N-PORT-Stichtage einige Monate "
                      "früher: ein seither erloschener Rechtsträger zählt als nicht aktiv.",
        },
    }
    if cache is not None:
        atomic_json(cache, result)
    return result


def quality_report(ctx: AppContext, data_dir: Path | None = None,
                   cache_dir: Path | None = None) -> dict[str, Any]:
    """Messwerte des aktiven N-PORT-Datenstands (Phase 1 der Roadmap)."""
    with ctx.session_factory() as session:
        version: DatasetVersion | None = active_versions(session).get(SOURCE_KEY)
        last = session.scalars(select(UpdateRun).where(UpdateRun.source_key == SOURCE_KEY)
                               .order_by(UpdateRun.id.desc())).first()
        if version is None:
            return {"report_schema": REPORT_SCHEMA, "active_version": None,
                    "last_run": last.status if last else "never_run",
                    "last_message": last.message if last else None}
        v = version.id
        conn = session.connection()
        manifest = {}
        base = data_dir or local_data_dir()
        if version.raw_path:
            # Manifest gegen den aktiven Datenstand prüfen (D-061); die Archive selbst prüft
            # der Import bei jedem Lauf gegen ihre Begleitdatei (D-054).
            content, _ = verified_manifest(
                resolve_data_path(version.raw_path), base, SOURCE_KEY,
                version.content_hash,
                f"nport.sqlite: dataset_versions.content_hash, Datenstand {version.id}",
                base / "raw/external" / SOURCE_KEY)
            manifest = json.loads(content)
        load_stats = [
            {"quarter": q, "table": t, "read": r, "accepted": a, **json.loads(j)}
            for q, t, r, a, j in _rows(conn, "SELECT quarter, table_name, rows_read, "
                                       "rows_accepted, rejected_json FROM nport_load_stats "
                                       "WHERE dataset_version_id = :v ORDER BY id", v=v)]

        subs = _rows(conn, "SELECT sub_type, report_date, filing_date, fiscal_year_end, "
                     "selection, fund_key, cik, series_lei, series_lei_reported "
                     "FROM nport_submissions WHERE dataset_version_id = :v", v=v)
        selection = Counter(r[4] for r in subs)
        report_months = Counter(_month(r[1]) for r in subs)
        filing_months = Counter(_month(r[2]) for r in subs)
        # Prüfung «nur der dritte Monat je Geschäftsquartal öffentlich»: Liegt der Stichtag
        # in einem Quartalsendmonat, gemessen am gemeldeten Geschäftsjahresende?
        with_fye = [r for r in subs if r[3]]
        quarter_end = sum(1 for r in with_fye
                          if (date.fromisoformat(str(r[1])).month
                              - date.fromisoformat(str(r[3])).month) % 3 == 0)
        lag = [(date.fromisoformat(str(r[2])) - date.fromisoformat(str(r[1]))).days
               for r in subs]
        current = [r for r in subs if r[4] == "current"]
        funds = {r[5] for r in subs if r[5]}
        series = {f for f in funds if f.startswith("S")}

        scope = ("FROM nport_holdings h JOIN nport_submissions s ON s.dataset_version_id = "
                 "h.dataset_version_id AND s.quarter = h.quarter AND s.accession = h.accession "
                 "WHERE h.dataset_version_id = :v AND s.selection = 'current'")
        holdings_all = _one(conn, "SELECT COUNT(*) FROM nport_holdings "
                            "WHERE dataset_version_id = :v", v=v)
        total = _one(conn, f"SELECT COUNT(*) {scope}", v=v)
        isin_status = dict(_rows(conn, f"SELECT h.isin_status, COUNT(*) {scope} "
                                 "GROUP BY h.isin_status", v=v))
        lei_status = dict(_rows(conn, f"SELECT h.issuer_lei_status, COUNT(*) {scope} "
                                "GROUP BY h.issuer_lei_status", v=v))
        both = _one(conn, f"SELECT COUNT(*) {scope} AND h.isin IS NOT NULL "
                    "AND h.issuer_lei IS NOT NULL", v=v)
        by_asset = _rows(conn, f"SELECT COALESCE(h.asset_cat, '(leer)'), COUNT(*), "
                         "SUM(h.isin IS NOT NULL), SUM(h.issuer_lei IS NOT NULL), "
                         "SUM(h.isin IS NOT NULL AND h.issuer_lei IS NOT NULL) "
                         f"{scope} GROUP BY 1 ORDER BY 2 DESC", v=v)
        distinct_isin = _one(conn, f"SELECT COUNT(DISTINCT h.isin) {scope}", v=v)
        distinct_lei = _one(conn, f"SELECT COUNT(DISTINCT h.issuer_lei) {scope}", v=v)
        na_tokens = _rows(conn, f"SELECT h.issuer_lei_reported, COUNT(*) {scope} AND "
                          "h.issuer_lei_status IN ('not_applicable', 'invalid_format') "
                          "GROUP BY 1 ORDER BY 2 DESC LIMIT 10", v=v)
        pct_sums = [r[0] for r in _rows(conn, f"SELECT SUM(h.percentage) {scope} "
                                        "GROUP BY h.quarter, h.accession", v=v)
                    if r[0] is not None]
        issuer_counts = dict(_rows(conn, f"SELECT h.issuer_lei, COUNT(*) {scope} "
                                   "AND h.issuer_lei IS NOT NULL GROUP BY 1", v=v))
        orphan_ids = _one(conn, "SELECT COUNT(*) FROM nport_identifiers i WHERE "
                          "i.dataset_version_id = :v AND NOT EXISTS (SELECT 1 FROM "
                          "nport_holdings h WHERE h.dataset_version_id = i.dataset_version_id "
                          "AND h.quarter = i.quarter AND h.holding_id = i.holding_id)", v=v)

    gleif = gleif_check(issuer_counts, {r[7] for r in current if r[7]}, data_dir, cache_dir,
                        version.content_hash)

    def status_shares(counts: dict[str, int]) -> dict[str, Any]:
        return {k: _share(n, total) for k, n in sorted(counts.items(), key=lambda x: -x[1])}

    return {
        "report_schema": REPORT_SCHEMA,
        "source_key": SOURCE_KEY,
        "active_version": version.id,
        "content_hash": version.content_hash,
        "data_as_of": str(version.data_as_of) if version.data_as_of else None,
        "fetched_at": version.fetched_at.isoformat(),
        "last_run": last.status if last else None,
        "last_message": last.message if last else None,
        "archives": manifest.get("archives", []),
        "load_stats": load_stats,
        "filings": {
            "total": len(subs),
            "by_sub_type": dict(Counter(r[0] for r in subs)),
            "selection": dict(selection),
            "report_month": dict(sorted(report_months.items())),
            "filing_month": dict(sorted(filing_months.items())),
            "report_date_in_fiscal_quarter_end_month": _share(quarter_end, len(with_fye)),
            "days_report_to_filing": {
                "min": min(lag, default=None), "median": statistics.median(lag) if lag else None,
                "max": max(lag, default=None)},
        },
        "funds": {
            "funds_distinct": len(funds),
            "series_distinct": len(series),
            "registrants_without_series": len(funds - series),
            "funds_with_current_filing": len({r[5] for r in current}),
            "registrants_distinct": len({r[6] for r in subs if r[6]}),
            "current_filings_with_valid_series_lei": _share(sum(1 for r in current if r[7]),
                                                            len(current)),
        },
        "holdings": {
            "all_filings": holdings_all,
            "current_filings": total,
            "isin_status": status_shares(isin_status),
            "issuer_lei_status": status_shares(lei_status),
            "isin_and_issuer_lei_valid": _share(both, total),
            "distinct_valid_isin": distinct_isin,
            "distinct_valid_issuer_lei": distinct_lei,
            "by_asset_cat": [
                {"asset_cat": cat, "holdings": n, "isin_valid": _share(i, n),
                 "issuer_lei_valid": _share(lei, n), "both_valid": _share(b, n)}
                for cat, n, i, lei, b in by_asset],
            "most_frequent_unusable_lei_values": [
                {"reported": value, "count": n} for value, n in na_tokens],
            "percentage_sum_per_filing": {
                "filings": len(pct_sums),
                "median": round(statistics.median(pct_sums), 4) if pct_sums else None,
                "between_95_and_105": _share(sum(1 for s in pct_sums if 95 <= s <= 105),
                                             len(pct_sums))},
            "identifiers_without_holding": orphan_ids,
        },
        "gleif_check": gleif,
        "notes": [
            "Scope der Positionswerte: nur Meldungen mit Auswahl «current» (jüngster Stichtag "
            "je Fonds, letzte Einreichung). Fonds = Serie, ohne Serie der Registrant. "
            "Unsere Auswahlregel, nicht von der SEC.",
            "Gültig heisst: Prüfziffer nach ISO 6166 (ISIN) bzw. ISO 17442 (LEI) stimmt. "
            "Das sagt nichts darüber, ob die Kennung zum gemeldeten Papier passt.",
            "Gemeldet von den Fonds («as filed»); die SEC garantiert die Richtigkeit nicht.",
            "Nur in den USA registrierte Fonds; kein Weltbestand.",
        ],
    }


def update_nport(force: bool = False, report_only: bool = False) -> tuple[dict, bool]:
    folder = get_settings().processed_dir / "nport"
    with foundation_lock(folder):
        ctx = create_nport_context()
        try:
            failed = False
            if not report_only:
                outcome = ctx.updates.run_source(SOURCE_KEY, force=force, trigger="nport-update")
                print(f"{SOURCE_KEY}: {outcome.status.value}: {outcome.message}", flush=True)
                for line in (outcome.errors + outcome.warnings)[:20]:
                    print(f"  {line}", flush=True)
                failed = outcome.status in {UpdateStatus.FEHLGESCHLAGEN, UpdateStatus.GESPERRT}
            report = quality_report(ctx, ctx.settings.data_dir, folder)
            atomic_json(folder / "quality_report.json", report)
            print(f"Qualitätsbericht: {folder / 'quality_report.json'}")
            return report, failed
        finally:
            ctx.engine.dispose()
