"""SEC N-PORT: Lesen aus dem ZIP, Zeilenprüfung, Auswahl, Update-System, Download (fiktiv).

Alle Daten sind erfunden: Fondsnamen «Fiktiv …», ISIN mit Präfix ZZ, LEI mit Präfix FIKT00,
Accession-Nummern mit Präfix 9999999999.
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import select, text

from transparenz.config.catalog import load_catalog
from transparenz.config.licensing import license_block_reasons
from transparenz.config.settings import CONFIG_DIR
from transparenz.database.models import DatasetVersion, NportHoldingRow, UpdateRun
from transparenz.entities.enums import UpdateStatus
from transparenz.entities.identifiers import make_isin, make_lei
from transparenz.entities.nport import NportSubmission
from transparenz.ingestion.fetchers import FetchError
from transparenz.ingestion.sec_nport import (
    TABLES,
    classify_isin,
    classify_lei,
    download_quarter,
    fund_keys,
    select_filings,
)
from transparenz.services.nport_catalog import quality_report
from transparenz.services.update_manager import DataUpdateManager

A1, A2, A3 = "9999999999-26-000001", "9999999999-26-000002", "9999999999-26-000003"
LEI_ISSUER = make_lei("FIKT00NPORTISSUER1")
LEI_SERIES = make_lei("FIKT00NPORTSERIES1")
ISIN_A = make_isin("ZZNPORT0001")
ISIN_B = make_isin("ZZNPORT0002")
BAD_ISIN = ISIN_A[:-1] + str((int(ISIN_A[-1]) + 1) % 10)
BAD_LEI = LEI_ISSUER[:-1] + str((int(LEI_ISSUER[-1]) + 1) % 10)


def holding(accession: str, holding_id: int, **over: str) -> dict[str, str]:
    row = {c: "" for c in TABLES["FUND_REPORTED_HOLDING.tsv"]}
    row.update({"ACCESSION_NUMBER": accession, "HOLDING_ID": str(holding_id),
                "ISSUER_NAME": "Fiktiv Emittent AG", "ISSUER_LEI": LEI_ISSUER,
                "ISSUER_TITLE": "Fiktiv Aktie", "BALANCE": "10", "UNIT": "NS",
                "CURRENCY_CODE": "USD", "CURRENCY_VALUE": "100.5", "PERCENTAGE": "25",
                "PAYOFF_PROFILE": "Long", "ASSET_CAT": "EC", "ISSUER_TYPE": "CORP",
                "INVESTMENT_COUNTRY": "ZZ", "IS_RESTRICTED_SECURITY": "N",
                "FAIR_VALUE_LEVEL": "1"})
    row.update(over)
    return row


def identifier(holding_id: int, identifier_id: int, isin: str = "", ticker: str = "") -> dict:
    return {"HOLDING_ID": str(holding_id), "IDENTIFIERS_ID": str(identifier_id),
            "IDENTIFIER_ISIN": isin, "IDENTIFIER_TICKER": ticker, "OTHER_IDENTIFIER": "",
            "OTHER_IDENTIFIER_DESC": ""}


def default_tables() -> dict[str, list[dict[str, str]]]:
    subs = [
        # A1: Original, A2: Berichtigung derselben Serie und desselben Stichtags (später)
        {"ACCESSION_NUMBER": A1, "FILING_DATE": "20-JUL-2026", "SUB_TYPE": "NPORT-P",
         "REPORT_ENDING_PERIOD": "31-DEC-2026", "REPORT_DATE": "30-JUN-2026",
         "IS_LAST_FILING": "N"},
        {"ACCESSION_NUMBER": A2, "FILING_DATE": "25-AUG-2026", "SUB_TYPE": "NPORT-P/A",
         "REPORT_ENDING_PERIOD": "31-DEC-2026", "REPORT_DATE": "30-JUN-2026",
         "IS_LAST_FILING": "N"},
        # A3: zweite Serie, Stichtag ausserhalb eines Quartalsendmonats
        {"ACCESSION_NUMBER": A3, "FILING_DATE": "28-SEP-2026", "SUB_TYPE": "NPORT-P",
         "REPORT_ENDING_PERIOD": "31-DEC-2026", "REPORT_DATE": "31-JUL-2026",
         "IS_LAST_FILING": ""},
    ]
    registrants = [{"ACCESSION_NUMBER": a, "CIK": "9999999", "REGISTRANT_NAME": "Fiktiv Trust",
                    "LEI": "N/A"} for a in (A1, A2, A3)]
    funds = [
        {"ACCESSION_NUMBER": A1, "SERIES_NAME": "Fiktiv Fonds Eins", "SERIES_ID": "S999999901",
         "SERIES_LEI": LEI_SERIES, "TOTAL_ASSETS": "410", "NET_ASSETS": "400"},
        {"ACCESSION_NUMBER": A2, "SERIES_NAME": "Fiktiv Fonds Eins", "SERIES_ID": "S999999901",
         "SERIES_LEI": LEI_SERIES, "TOTAL_ASSETS": "410", "NET_ASSETS": "400"},
        {"ACCESSION_NUMBER": A3, "SERIES_NAME": "Fiktiv Fonds Zwei", "SERIES_ID": "S999999902",
         "SERIES_LEI": "", "TOTAL_ASSETS": "100", "NET_ASSETS": "100"},
    ]
    holdings = [
        holding(A1, 1),
        holding(A2, 11),                                     # eine gültige ISIN
        holding(A2, 12, ISSUER_LEI="N/A"),                   # zwei verschiedene gültige ISIN
        holding(A2, 13, ISSUER_LEI=BAD_LEI),                 # nur ungültige ISIN
        holding(A2, 14, ISSUER_LEI="ABC"),                   # ohne ISIN, nur Ticker
        holding(A3, 21, ASSET_CAT="DBT", ISSUER_LEI=""),
    ]
    identifiers = [
        identifier(1, 101, ISIN_A),
        identifier(11, 111, ISIN_A), identifier(11, 112, ISIN_A.lower()),
        identifier(12, 121, ISIN_A), identifier(12, 122, ISIN_B),
        identifier(13, 131, BAD_ISIN),
        identifier(14, 141, ticker="FIKT"),
        identifier(21, 211, ISIN_B),
    ]
    return {"SUBMISSION.tsv": subs, "REGISTRANT.tsv": registrants,
            "FUND_REPORTED_INFO.tsv": funds, "FUND_REPORTED_HOLDING.tsv": holdings,
            "IDENTIFIERS.tsv": identifiers}


def zip_bytes(tables: dict[str, list[dict[str, str]]], drop_column: str | None = None) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, rows in tables.items():
            columns = list(rows[0]) if rows else list(TABLES[name])
            if drop_column in columns:
                columns.remove(drop_column)
            lines = ["\t".join(columns)] + ["\t".join(r.get(c, "") for c in columns)
                                            for r in rows]
            archive.writestr(name, "\n".join(lines) + "\n")
        archive.writestr("nport_readme.htm", "<p>fiktiv</p>")
    return out.getvalue()


def place(root: Path, content: bytes, quarter: str = "2026q3",
          recorded_sha: str | None = None) -> Path:
    folder = root / "data/raw/external/sec_nport" / quarter
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{quarter}_nport.zip"
    path.write_bytes(content)
    (folder / "source.metadata.json").write_text(json.dumps({
        "source_key": "sec_nport", "url": "https://example.org/fiktiv/nport.zip",
        "license": "fiktiv", "terms_url": "https://example.org/fiktiv/terms",
        "retrieved_at_utc": "2026-11-15T00:00:00Z", "size_bytes": len(content),
        "sha256": recorded_sha or hashlib.sha256(content).hexdigest()}), encoding="utf-8")
    return path


@pytest.fixture
def nport_catalog():
    return load_catalog(CONFIG_DIR / "nport_sources.toml", CONFIG_DIR / "criteria.toml")


@pytest.fixture
def manager(tmp_path, session_factory, nport_catalog):
    return DataUpdateManager(session_factory, nport_catalog, project_root=tmp_path,
                             raw_dir=tmp_path / "data/raw/external/manifests")


def active(session_factory) -> DatasetVersion | None:
    with session_factory() as session:
        return session.scalars(select(DatasetVersion).where(
            DatasetVersion.source_key == "sec_nport", DatasetVersion.status == "active")).first()


# --------------------------------------------------------------------------- Kennungen


def test_classify_identifiers_keeps_reported_value_and_status():
    assert classify_lei(LEI_ISSUER.lower()) == (LEI_ISSUER.lower(), LEI_ISSUER, "valid")
    assert classify_lei(" ") == (None, None, "missing")
    assert classify_lei("N/A") == ("N/A", None, "not_applicable")
    assert classify_lei("ABC") == ("ABC", None, "invalid_format")
    assert classify_lei(BAD_LEI)[2] == "invalid_checksum"
    assert classify_isin(ISIN_A) == (ISIN_A, ISIN_A, "valid")
    assert classify_isin(BAD_ISIN) == (BAD_ISIN, None, "invalid_checksum")
    assert classify_isin("123") == ("123", None, "invalid_format")


def test_licence_gate_passes_for_reviewed_nport_source(nport_catalog):
    cfg = nport_catalog.source("sec_nport")
    assert license_block_reasons(cfg, date(2026, 11, 15)) == []


# --------------------------------------------------------------------------- Auswahl


def sub(accession: str, series: str | None, report: str, filed: str,
        sub_type: str = "NPORT-P", cik: str | None = None) -> NportSubmission:
    return NportSubmission(quarter="2026q3", accession=accession, sub_type=sub_type, cik=cik,
                           series_id=series, report_date=date.fromisoformat(report),
                           filing_date=date.fromisoformat(filed))


def test_selection_amendment_tie_earlier_period_and_no_series():
    picks = select_filings([
        sub("9999999999-26-000010", "S999999901", "2026-06-30", "2026-07-20"),
        sub("9999999999-26-000011", "S999999901", "2026-06-30", "2026-08-25", "NPORT-P/A"),
        sub("9999999999-26-000012", "S999999901", "2026-03-31", "2026-04-20"),
        sub("9999999999-26-000020", "S999999902", "2026-07-31", "2026-09-01"),
        sub("9999999999-26-000021", "S999999902", "2026-07-31", "2026-09-01"),
        sub("9999999999-26-000022", "S999999902", "2026-04-30", "2026-06-01"),
        sub("9999999999-26-000030", None, "2026-07-31", "2026-09-01", cik="0009999901"),
        sub("9999999999-26-000032", None, "2026-07-31", "2026-09-01", cik="0009999902"),
        sub("9999999999-26-000033", "S999999904", "2026-07-31", "2026-09-01",
            cik="0009999902"),
        sub("9999999999-26-000031", "S999999903", "2026-07-31", "2026-09-02", "NT NPORT-P"),
    ])
    get = {acc[-2:]: value for (_, acc), value in picks.items()}
    assert get == {"10": "superseded", "11": "current", "12": "earlier_period",
                   "20": "tie", "21": "tie", "22": "earlier_period",
                   "30": "current", "31": "notice", "32": "no_series", "33": "current"}


def test_fund_key_uses_registrant_only_without_any_series():
    keys = fund_keys([
        sub("9999999999-26-000040", None, "2026-07-31", "2026-09-01", cik="0009999901"),
        sub("9999999999-26-000041", None, "2026-07-31", "2026-09-01", cik="0009999902"),
        sub("9999999999-26-000042", "S999999905", "2026-07-31", "2026-09-01",
            cik="0009999902"),
        sub("9999999999-26-000043", None, "2026-07-31", "2026-09-01"),
    ])
    assert [keys[("2026q3", f"9999999999-26-0000{i}")] for i in (40, 41, 42, 43)] == [
        "CIK0009999901", None, "S999999905", None]


# --------------------------------------------------------------------------- Update-System


def test_update_reads_zip_validates_and_records_run(tmp_path, manager, session_factory):
    place(tmp_path, zip_bytes(default_tables()))
    outcome = manager.run_source("sec_nport", force=True)
    assert outcome.status == UpdateStatus.ERFOLGREICH, outcome
    # 3 Meldungen + 6 Positionen + 8 Kennungen
    assert "17 Datensätzen" in outcome.message
    version = active(session_factory)
    assert version is not None and version.data_as_of == date(2026, 7, 31)
    with session_factory() as session:
        rows = {r.holding_id: r for r in session.scalars(select(NportHoldingRow))}
        assert (rows[11].isin, rows[11].isin_status) == (ISIN_A, "valid")
        assert (rows[12].isin, rows[12].isin_status) == (None, "multiple")
        assert (rows[13].isin, rows[13].isin_status) == (None, "invalid")
        assert (rows[14].isin, rows[14].isin_status) == (None, "missing")
        assert rows[12].issuer_lei_status == "not_applicable"
        assert rows[13].issuer_lei is None and rows[13].issuer_lei_reported == BAD_LEI
        selection = dict(session.execute(text(
            "SELECT accession, selection FROM nport_submissions")).all())
        assert selection == {A1: "superseded", A2: "current", A3: "current"}
        runs = session.scalars(select(UpdateRun)).all()
        assert [r.status for r in runs] == [UpdateStatus.ERFOLGREICH.value]
        stats = session.execute(text("SELECT table_name, rows_read, rows_accepted "
                                     "FROM nport_load_stats")).all()
        assert ("FUND_REPORTED_HOLDING.tsv", 6, 6) in stats
    again = manager.run_source("sec_nport", force=True)
    assert again.status == UpdateStatus.UNVERAENDERT


def test_quality_report_counts_current_filings_only(tmp_path, manager, session_factory):
    place(tmp_path, zip_bytes(default_tables()))
    assert manager.run_source("sec_nport", force=True).status == UpdateStatus.ERFOLGREICH
    report = quality_report(SimpleNamespace(session_factory=session_factory))
    h = report["holdings"]
    assert h["all_filings"] == 6 and h["current_filings"] == 5
    assert h["isin_status"]["valid"] == {"count": 2, "of": 5, "percent": 40.0}
    assert h["issuer_lei_status"]["valid"]["count"] == 1
    assert h["isin_and_issuer_lei_valid"]["count"] == 1
    assert h["distinct_valid_isin"] == 2
    assert h["identifiers_without_holding"] == 0
    f = report["filings"]
    assert f["selection"] == {"superseded": 1, "current": 2}
    # Juni ist Quartalsendmonat bei Geschäftsjahresende Dezember, Juli nicht.
    assert f["report_date_in_fiscal_quarter_end_month"]["count"] == 2
    assert report["funds"]["series_distinct"] == 2
    assert report["funds"]["funds_distinct"] == 2
    assert "issuer_lei_active_at_gleif" in report["not_measured"]


def test_invalid_rows_are_rejected_and_counted(tmp_path, manager, session_factory):
    tables = default_tables()
    tables["FUND_REPORTED_HOLDING.tsv"] += [holding(A3, 22 + i) for i in range(300)]
    tables["FUND_REPORTED_HOLDING.tsv"] += [
        holding(A3, 900, PERCENTAGE="viel"), holding("9999999999-26-999999", 901),
        holding("kaputt", 902)]
    place(tmp_path, zip_bytes(tables))
    outcome = manager.run_source("sec_nport", force=True)
    assert outcome.status == UpdateStatus.ERFOLGREICH, outcome
    warning = next(w for w in outcome.warnings if "FUND_REPORTED_HOLDING" in w)
    assert "3 Zeilen abgelehnt" in warning
    assert "number:PERCENTAGE 1" in warning and "unknown_accession 1" in warning
    with session_factory() as session:
        stat = session.execute(text(
            "SELECT rows_read, rows_accepted, rejected_json FROM nport_load_stats "
            "WHERE table_name = 'FUND_REPORTED_HOLDING.tsv'")).one()
    assert stat[0] == 309 and stat[1] == 306
    assert json.loads(stat[2])["rejected"]["key:ACCESSION_NUMBER"] == 1


def test_too_many_rejected_rows_reject_whole_dataset(tmp_path, manager, session_factory):
    tables = default_tables()
    tables["FUND_REPORTED_HOLDING.tsv"].append(holding(A3, 99, BALANCE="x"))
    place(tmp_path, zip_bytes(tables))
    outcome = manager.run_source("sec_nport", force=True)
    assert outcome.status == UpdateStatus.FEHLGESCHLAGEN
    assert any("mehr als 1%" in e for e in outcome.errors)
    assert active(session_factory) is None


def test_missing_required_column_fails(tmp_path, manager, session_factory):
    place(tmp_path, zip_bytes(default_tables(), drop_column="ISSUER_LEI"))
    outcome = manager.run_source("sec_nport", force=True)
    assert outcome.status == UpdateStatus.FEHLGESCHLAGEN
    assert any("Pflichtspalten fehlen: ISSUER_LEI" in e for e in outcome.errors)


def test_changed_archive_is_refused_before_parsing(tmp_path, manager, session_factory):
    place(tmp_path, zip_bytes(default_tables()), recorded_sha="0" * 64)
    outcome = manager.run_source("sec_nport", force=True)
    assert outcome.status == UpdateStatus.FEHLGESCHLAGEN
    assert "weicht von der Begleitdatei" in outcome.errors[0]
    assert active(session_factory) is None


def test_no_local_archive_is_explicit_failure(manager):
    outcome = manager.run_source("sec_nport", force=True)
    assert outcome.status == UpdateStatus.FEHLGESCHLAGEN
    assert "nport-download" in outcome.errors[0]


def test_duplicate_holding_key_rolls_back(tmp_path, manager, session_factory):
    tables = default_tables()
    tables["FUND_REPORTED_HOLDING.tsv"].append(holding(A3, 21))
    tables["FUND_REPORTED_HOLDING.tsv"] += [holding(A3, 500 + i) for i in range(200)]
    place(tmp_path, zip_bytes(tables))
    outcome = manager.run_source("sec_nport", force=True)
    assert outcome.status == UpdateStatus.FEHLGESCHLAGEN
    assert "Rollback" in outcome.message
    assert active(session_factory) is None
    with session_factory() as session:
        assert session.execute(text("SELECT COUNT(*) FROM nport_holdings")).scalar() == 0


def test_new_quarter_creates_new_version_with_both_archives(tmp_path, manager, session_factory):
    place(tmp_path, zip_bytes(default_tables()))
    assert manager.run_source("sec_nport", force=True).status == UpdateStatus.ERFOLGREICH
    tables = default_tables()
    for rows in tables.values():
        for row in rows:
            if "ACCESSION_NUMBER" in row:
                row["ACCESSION_NUMBER"] = row["ACCESSION_NUMBER"].replace("-26-", "-27-")
    tables["SUBMISSION.tsv"][2]["REPORT_DATE"] = "31-OCT-2026"
    place(tmp_path, zip_bytes(tables), quarter="2026q4")
    assert manager.run_source("sec_nport", force=True).status == UpdateStatus.ERFOLGREICH
    version = active(session_factory)
    with session_factory() as session:
        quarters = session.execute(text(
            "SELECT quarter, COUNT(*) FROM nport_holdings WHERE dataset_version_id = :v "
            "GROUP BY quarter"), {"v": version.id}).all()
        current = session.execute(text(
            "SELECT accession FROM nport_submissions WHERE dataset_version_id = :v AND "
            "selection = 'current' AND series_id = 'S999999902'"), {"v": version.id}).all()
    assert dict(quarters) == {"2026q3": 6, "2026q4": 6}
    # Gleiche Holding-ID in zwei Quartalen ist erlaubt; jüngster Stichtag gewinnt je Serie.
    assert current == [("9999999999-27-000003",)]


# --------------------------------------------------------------------------- Download


def mock_client(body: bytes, length: int | None = None, status: int = 200) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "www.sec.gov"
        headers = {"Content-Length": str(len(body) if length is None else length),
                   "Last-Modified": "Wed, 07 Oct 2026 16:13:21 GMT"}
        if request.method == "HEAD":
            return httpx.Response(status, headers=headers)
        return httpx.Response(status, headers=headers, content=body)
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_download_without_confirm_only_reports_size(tmp_path):
    body = zip_bytes(default_tables())
    info = download_quarter("2026q3", tmp_path, "test@example.org", confirm=False,
                            client=mock_client(body))
    assert info["downloaded"] is False and info["size_bytes"] == len(body)
    assert info["file"] == "2026q3_nport.zip"
    assert not (tmp_path / "raw/external/sec_nport/2026q3").exists()


def test_download_with_confirm_writes_archive_and_sidecar(tmp_path):
    body = zip_bytes(default_tables())
    info = download_quarter("2026q3", tmp_path, "test@example.org", confirm=True,
                            client=mock_client(body),
                            now=lambda: datetime(2026, 11, 15, 12, 0, 0))
    folder = tmp_path / "raw/external/sec_nport/2026q3"
    meta = json.loads((folder / "source.metadata.json").read_text(encoding="utf-8"))
    assert info["downloaded"] and meta["sha256"] == hashlib.sha256(body).hexdigest()
    assert meta["retrieved_at_utc"] == "2026-11-15T12:00:00Z"
    assert "example.org" not in json.dumps(meta)  # Kontakt nie in Dateien
    assert (folder / "2026q3_nport.zip").read_bytes() == body
    with pytest.raises(FileExistsError):
        download_quarter("2026q3", tmp_path, "test@example.org", confirm=True,
                         client=mock_client(body))


def test_download_refuses_short_body_bad_quarter_and_missing_contact(tmp_path):
    body = zip_bytes(default_tables())
    with pytest.raises(FetchError, match="Bytes erhalten"):
        download_quarter("2026q3", tmp_path, "test@example.org", confirm=True,
                         client=mock_client(body, length=len(body) + 5))
    assert not list((tmp_path / "raw/external/sec_nport/2026q3").glob("*.zip*"))
    with pytest.raises(ValueError, match="JJJJqN"):
        download_quarter("2026-3", tmp_path, "test@example.org", confirm=False)
    with pytest.raises(ValueError, match="TRANSPARENZ_SEC_CONTACT"):
        download_quarter("2026q3", tmp_path, "", confirm=False)
