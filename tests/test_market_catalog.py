"""Identity, ETF evidence, raw integrity and activation regression checks (synthetic data)."""

import csv
import hashlib
import io
import json
import zipfile
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import select

from transparenz.config.catalog import Catalog, load_catalog
from transparenz.config.licensing import license_block_reasons
from transparenz.config.settings import CONFIG_DIR, get_settings
from transparenz.database.models import DatasetVersion, MarketRecordRow
from transparenz.entities.enums import UpdateStatus
from transparenz.ingestion.external import encoded
from transparenz.ingestion.fetchers import FetchError, FetchResult
from transparenz.ingestion.markets import (
    FORMAT,
    MarketFetcher,
    build_market_adapter,
    parse_ncen,
    parse_tickers,
)
from transparenz.reports.market_catalog import render_catalogue
from transparenz.services.context import AppContext
from transparenz.services.market_catalog import build_catalogue, export_market, search_market
from transparenz.services.update_manager import DataUpdateManager

PAGE = {"url": "https://www.sec.gov/files/synthetic-test.json", "sha256": "a" * 64}
ACCESSION = "0000000001-26-000001"
FUND_ID = ACCESSION + "_0000000001_S000000001"


def ncen_zip(classes=1, series="S000000001", flag="Y", report="31-DEC-2025",
             accession=ACCESSION):
    fund_id = accession + "_0000000001_" + series
    tables = {
        "SUBMISSION.tsv": [{"ACCESSION_NUMBER": accession, "CIK": "1",
                            "FILING_DATE": "02-MAR-2026", "REPORT_ENDING_PERIOD": report}],
        "FUND_REPORTED_INFO.tsv": [{"FUND_ID": fund_id, "ACCESSION_NUMBER": accession,
                                    "FUND_NAME": "Synthetic test fund", "SERIES_ID": series,
                                    "IS_ETF": flag, "IS_ETMF": "N"}],
        "SHARES_OUTSTANDING.tsv": [
            {"FUND_ID": fund_id, "CLASS_NAME": f"Synthetic class {i}",
             "CLASS_ID": f"C{i:09d}", "TICKER": f"TEST{i}"} for i in range(1, classes + 1)]}
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        for name, rows in tables.items():
            text = io.StringIO()
            writer = csv.DictWriter(text, fieldnames=list(rows[0]), delimiter="\t")
            writer.writeheader()
            writer.writerows(rows)
            z.writestr(name, text.getvalue())
    return out.getvalue()


def reports(**kwargs):
    return [r.model_dump(mode="json") for r in parse_ncen(ncen_zip(**kwargs), PAGE)]


def current(classes=1):
    return [r.model_dump(mode="json") for r in parse_tickers({
        "fields": ["cik", "seriesId", "classId", "symbol"],
        "data": [[1, "S000000001", f"C{i:09d}", f"TEST{i}"] for i in range(1, classes + 1)]
    }, "sec_fund_classes", PAGE)]


@pytest.fixture
def market_catalog() -> Catalog:
    return load_catalog(CONFIG_DIR / "market_sources.toml", CONFIG_DIR / "criteria.toml")


def test_reviewed_market_sources_pass_license_gate(market_catalog):
    assert all(not license_block_reasons(c, datetime(2026, 11, 8).date())
               for c in market_catalog.sources)


def test_listing_does_not_imply_equity_type_country_or_tradability():
    rows = parse_tickers({"fields": ["cik", "name", "ticker", "exchange"],
                          "data": [[1, "Synthetic warrant", "TEST-W", "Nasdaq"]]},
                         "sec_exchange", PAGE)
    items, _ = build_catalogue({"sec_exchange_tickers": [r.model_dump() for r in rows]})
    assert items[0]["classification"] == "listed_instrument_unclassified"
    assert items[0]["issuer_country"] is None
    assert items[0]["currently_tradable"] is None
    assert items[0]["isin"] is None


def test_single_class_etf_has_report_and_original_proof():
    items, counts = build_catalogue({"sec_fund_classes": current(), "sec_ncen": reports()})
    assert counts == {"etf_reported_single_class": 1}
    assert items[0]["report_date"] == "2025-12-31"
    assert items[0]["evidence"][1]["accession"] == ACCESSION
    assert items[0]["evidence"][1]["original_sha256"] == "a" * 64


def test_etf_series_does_not_classify_all_mutual_fund_classes():
    items, counts = build_catalogue({"sec_fund_classes": current(2),
                                    "sec_ncen": reports(classes=2)})
    assert counts == {"etf_series_class_unresolved": 2}
    assert len({x["catalogue_key"] for x in items}) == 2
    assert len({x["registrant_cik"] for x in items}) == 1


def test_latest_report_replaces_old_etf_classification():
    rows = reports() + reports(flag="N", report="31-JAN-2026",
                               accession="0000000001-26-000002")
    items, _ = build_catalogue({"sec_fund_classes": current(), "sec_ncen": rows})
    assert items[0]["classification"] == "fund_class_reported_non_etf"


def test_missing_class_in_latest_report_does_not_keep_old_etf_proof():
    newer = reports(report="31-JAN-2026", accession="0000000001-26-000002")[:1]
    items, _ = build_catalogue({"sec_fund_classes": current(), "sec_ncen": reports() + newer})
    assert items[0]["classification"] == "fund_class_unclassified"


def test_tied_reports_leave_classification_unresolved():
    rows = reports() + reports(flag="N", accession="0000000001-26-000002")
    items, _ = build_catalogue({"sec_fund_classes": current(), "sec_ncen": rows})
    assert items[0]["classification"] == "fund_class_unclassified"


def test_conflicting_class_identity_is_separate():
    rows = current()
    rows.append({**rows[0], "cik": "0000000002"})
    items, _ = build_catalogue({"sec_fund_classes": rows, "sec_ncen": reports()})
    assert items[0]["classification"] == "identity_conflict"
    assert items[0]["registrant_cik"] is None
    assert len(items[0]["conflicting_claims"]) == 3


def test_nonstandard_reported_series_is_preserved_without_valid_sec_series():
    rows = parse_ncen(ncen_zip(series="CEF0000002"), PAGE)
    assert all(r.series_id is None for r in rows)
    assert rows[0].reported_series_id == "CEF0000002"


def test_archive_missing_columns_is_rejected():
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        z.writestr("SUBMISSION.tsv", "CIK\n1\n")
    with pytest.raises(ValueError, match="Pflichtspalten"):
        parse_ncen(out.getvalue(), PAGE)


def bundle(tmp_path: Path, cfg, content: bytes, digest=None):
    folder = tmp_path / "data/raw/external" / cfg.key / "objects"
    folder.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256(content).hexdigest()
    path = folder / (h + ".json")
    path.write_bytes(content)
    return encoded({"format": FORMAT, "source_key": cfg.key, "mode": cfg.external_mode,
                    "pages": [{"path": "objects/" + path.name, "url": PAGE["url"],
                               "sha256": digest or h}]})


def test_raw_hash_mismatch_is_rejected(tmp_path, market_catalog):
    cfg = market_catalog.source("sec_exchange_tickers")
    ds = build_market_adapter(cfg, market_catalog, tmp_path, "").parse(
        bundle(tmp_path, cfg, b"{}", digest="0" * 64))
    assert not ds.is_valid
    assert "prüfsumme" in str(ds.errors[0])


def test_manifest_cannot_read_outside_source_objects(tmp_path, market_catalog):
    cfg = market_catalog.source("sec_exchange_tickers")
    content = json.loads(bundle(tmp_path, cfg, b"{}"))
    content["pages"][0]["path"] = "../../../../.env"
    ds = build_market_adapter(cfg, market_catalog, tmp_path, "").parse(encoded(content))
    assert not ds.is_valid
    assert "ausserhalb" in str(ds.errors[0])


def test_missing_contact_is_explicit_failure_before_network(tmp_path, market_catalog, monkeypatch):
    monkeypatch.delenv("TRANSPARENZ_SEC_CONTACT", raising=False)
    with pytest.raises(FetchError, match="Kontakt-E-Mail"):
        MarketFetcher(market_catalog.sources[0], tmp_path).fetch()


def test_market_pipeline_keeps_active_version_on_corrupt_original(
        tmp_path, market_catalog, session_factory):
    cfg = market_catalog.source("sec_exchange_tickers")
    adapter = build_market_adapter(cfg, market_catalog, tmp_path, "")
    raw = encoded({"fields": ["cik", "name", "ticker", "exchange"],
                   "data": [[1, "Synthetic issuer", "TEST", "NYSE"]]})
    good = bundle(tmp_path, cfg, raw)
    adapter.fetcher.fetch = lambda **_: FetchResult(origin="test", content=good)
    manager = DataUpdateManager(session_factory, market_catalog, tmp_path, tmp_path / "manifests",
                                adapters={cfg.key: adapter}, clock=lambda: datetime(2026, 11, 8))
    first = manager.run_source(cfg.key, force=True)
    assert first.status == UpdateStatus.ERFOLGREICH
    bad = bundle(tmp_path, cfg, raw + b" ", digest="f" * 64)
    adapter.fetcher.fetch = lambda **_: FetchResult(origin="test", content=bad)
    assert manager.run_source(cfg.key, force=True).status == UpdateStatus.FEHLGESCHLAGEN
    with session_factory() as s:
        assert s.scalar(select(DatasetVersion.id).where(DatasetVersion.status == "active")) == (
            first.version_id)
        assert len(list(s.scalars(select(MarketRecordRow)))) == 1


def test_source_names_cannot_end_json_script():
    hostile = '</script><script>alert("test")</script>'
    html = render_catalogue([{"name": hostile}], {"catalogue_entry_count": 1, "coverage": [],
                                                 "sources": {}})
    assert hostile not in html
    assert "\\u003c/script>" in html


def test_same_generation_stays_immutable_while_run_status_updates(
        tmp_path, market_catalog, session_factory):
    cfg = market_catalog.source("sec_exchange_tickers")
    adapter = build_market_adapter(cfg, market_catalog, tmp_path, "")

    def fail(**_):
        raise FetchError("synthetic failure", transient=False)

    adapter.fetcher.fetch = fail
    manager = DataUpdateManager(session_factory, market_catalog, tmp_path, tmp_path / "manifests",
                                adapters={cfg.key: adapter}, clock=lambda: datetime(2026, 11, 8))
    ctx = AppContext(replace(get_settings(), project_root=tmp_path), market_catalog,
                     session_factory.kw["bind"], session_factory, manager)
    first = export_market(ctx)
    folder = tmp_path / "data/processed/market"
    pointer = json.loads((folder / "current.json").read_bytes())
    generation = folder / pointer["generation"]
    original = {p.name: p.read_bytes() for p in generation.iterdir()}
    original_times = {p.name: p.stat().st_mtime_ns for p in generation.iterdir()}
    # A new run may change operational diagnostics, never the data generation.
    manager.run_source("sec_exchange_tickers", force=True)
    second = export_market(ctx)
    assert first["catalogue_entry_count"] == second["catalogue_entry_count"] == 0
    assert {p.name: p.read_bytes() for p in generation.iterdir()} == original
    assert {p.name: p.stat().st_mtime_ns for p in generation.iterdir()} == original_times
    latest = json.loads((folder / "latest_status.json").read_bytes())
    assert latest["sources"]["sec_exchange_tickers"]["last_run"] != "never_run"


def test_search_prioritizes_exact_ticker_over_funds_mentioning_it(tmp_path, monkeypatch):
    settings = replace(get_settings(), project_root=tmp_path)
    monkeypatch.setattr("transparenz.services.market_catalog.get_settings", lambda: settings)
    folder = tmp_path / "data/processed/market"
    generation = folder / "generations/test"
    generation.mkdir(parents=True)
    (folder / "current.json").write_bytes(encoded({"generation": "generations/test"}))
    (generation / "catalogue.json").write_bytes(encoded([
        {"name": "Synthetic TEST leveraged fund", "tickers": ["TEST2"]},
        {"name": "Synthetic issuer", "tickers": ["TEST"]}]))
    assert search_market("TEST", limit=1)[0]["name"] == "Synthetic issuer"
