"""Official SEC snapshots and annual N-CEN reports, with original-file provenance."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import zipfile
from collections.abc import Iterator
from datetime import date, datetime
from pathlib import Path

from pydantic import ValidationError

from transparenz.config.catalog import Catalog, SourceConfig
from transparenz.entities.enums import DatasetKind
from transparenz.entities.markets import MarketObservation
from transparenz.ingestion.adapters import SourceAdapter
from transparenz.ingestion.external import RawClient, encoded
from transparenz.ingestion.fetchers import FetchError, FetchResult
from transparenz.ingestion.parsing import ParsedDataset

FORMAT = "transparenz-market/1"
QUARTER_LINK = r"/files/dera/data/form-n-cen-data-sets/\d{4}q[1-4]_ncen\.zip"


class MarketFetcher:
    def __init__(self, config: SourceConfig, root: Path):
        self.config, self.root = config, root

    def fetch(self, etag=None, last_modified=None) -> FetchResult:
        contact = os.environ.get("TRANSPARENZ_SEC_CONTACT", "").strip()
        if not re.fullmatch(r"[^\s@()]+@[^\s@()]+\.[^\s@()]+", contact):
            raise FetchError("TRANSPARENZ_SEC_CONTACT lokal in .env setzen (Kontakt-E-Mail).",
                             transient=False)
        # Contact only travels in the HTTP header, never in manifests or versioned settings.
        c = RawClient(self.config, self.root, f"ProjektTransparenz/0.1 ({contact})")
        try:
            mode = self.config.external_mode
            first = c.get(self.config.location, suffix="html" if mode == "sec_ncen" else "json")
            pages = [first]
            if mode == "sec_ncen":
                html = (c.folder / first["path"]).read_text(encoding="utf-8")
                links = sorted(set(re.findall(QUARTER_LINK, html)), reverse=True)[:4]
                if len(links) != 4:
                    raise FetchError("N-CEN: nicht vier Quartalsarchive gefunden.", transient=False)
                pages = [c.get("https://www.sec.gov" + link, suffix="zip") for link in links]
            compact = [{k: p[k] for k in ("path", "sha256", "bytes", "url", "format")}
                       for p in pages]
            return FetchResult(origin=self.config.location, content=encoded({
                "format": FORMAT, "source_key": self.config.key, "mode": mode,
                "pages": compact, "complete_world": False,
                "ncen_schema_3_1_gap": mode == "sec_ncen"}))
        finally:
            c.close()


def _tsv(archive: zipfile.ZipFile, name: str, required: set[str]) -> Iterator[dict]:
    with archive.open(name) as stream:
        reader = csv.DictReader(io.TextIOWrapper(stream, encoding="utf-8-sig"), delimiter="\t")
        if not required <= set(reader.fieldnames or []):
            raise ValueError(f"{name}: Pflichtspalten fehlen")
        for row in reader:
            if None in row or any(v is None for v in row.values()):
                raise ValueError(f"{name}: ungültige Spaltenanzahl")
            yield row


def _day(value: str) -> date:
    return datetime.strptime(value, "%d-%b-%Y").date()


def _flag(value: str) -> bool | None:
    if not value:
        return None
    if value.upper() not in {"Y", "N"}:
        raise ValueError("Unbekannter N-CEN Wahrheitswert")
    return value.upper() == "Y"


def parse_ncen(content: bytes, page: dict) -> list[MarketObservation]:
    result = []
    provenance = {"source_url": page["url"], "original_sha256": page["sha256"]}
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        # No extraction; bounded selected tables only.
        if sum(i.file_size for i in archive.infolist()) > 2_000_000_000:
            raise ValueError("N-CEN: Archiv überschreitet Grössenlimit")
        submissions = {}
        for row in _tsv(archive, "SUBMISSION.tsv", {"ACCESSION_NUMBER", "CIK", "FILING_DATE",
                                                "REPORT_ENDING_PERIOD"}):
            accession = row["ACCESSION_NUMBER"]
            if accession in submissions:
                raise ValueError("Doppelte N-CEN Submission")
            submissions[accession] = {
                "cik": str(int(row["CIK"])).zfill(10), "accession": accession,
                "report_date": _day(row["REPORT_ENDING_PERIOD"]),
                "filing_date": _day(row["FILING_DATE"])}
        funds = {}
        for row in _tsv(archive, "FUND_REPORTED_INFO.tsv", {
                "FUND_ID", "ACCESSION_NUMBER", "FUND_NAME", "SERIES_ID", "IS_ETF", "IS_ETMF"}):
            key = row["FUND_ID"]
            if key in funds:
                raise ValueError("Doppelte N-CEN FUND_ID")
            fields = {**submissions[row["ACCESSION_NUMBER"]], **provenance,
                      "fund_id": key,
                      "series_id": (row["SERIES_ID"] if re.fullmatch(r"S\d{9}", row["SERIES_ID"])
                                    and row["SERIES_ID"] != "S000000000" else None),
                      "reported_series_id": row["SERIES_ID"] or None,
                      "name": row["FUND_NAME"] or None,
                      "series_is_etf": _flag(row["IS_ETF"]),
                      "series_is_etmf": _flag(row["IS_ETMF"])}
            funds[key] = fields
            result.append(MarketObservation(record_type="ncen_fund", record_key=key, **fields))
        for row in _tsv(archive, "SHARES_OUTSTANDING.tsv", {
                "FUND_ID", "CLASS_NAME", "CLASS_ID", "TICKER"}):
            fields = funds[row["FUND_ID"]]
            # A missing class ID is retained as an unresolved source observation.
            suffix = hashlib.sha256(encoded(row)).hexdigest()[:24]
            key = row["FUND_ID"] + ":" + (row["CLASS_ID"] or "unresolved") + ":" + suffix
            result.append(MarketObservation(
                record_type="ncen_class", record_key=key, **fields,
                class_id=(row["CLASS_ID"] or None) if row["CLASS_ID"] != "C000000000" else None,
                reported_class_id=row["CLASS_ID"] or None,
                class_name=row["CLASS_NAME"] or None,
                ticker=row["TICKER"] or None))
    return result


def parse_tickers(body: dict, mode: str, page: dict) -> list[MarketObservation]:
    expected = (["cik", "name", "ticker", "exchange"] if mode == "sec_exchange"
                else ["cik", "seriesId", "classId", "symbol"])
    if body["fields"] != expected or not body["data"]:
        raise ValueError("SEC-Ticker: Spalten verändert oder leerer Datenstand")
    result = []
    for values in body["data"]:
        if len(values) != len(expected):
            raise ValueError("SEC-Ticker: ungültige Spaltenanzahl")
        row = dict(zip(expected, values, strict=True))
        cik = str(int(row["cik"])).zfill(10)
        if mode == "sec_exchange":
            record = MarketObservation(
                record_type="listed_ticker", record_key=f'{cik}:{row["ticker"]}:{row["exchange"]}',
                cik=cik, ticker=row["ticker"], exchange=row["exchange"], name=row["name"],
                source_url=page["url"], original_sha256=page["sha256"])
        else:
            record = MarketObservation(
                record_type="fund_class", record_key=f'{row["classId"]}:{row["symbol"]}',
                cik=cik, series_id=row["seriesId"], class_id=row["classId"], ticker=row["symbol"],
                source_url=page["url"], original_sha256=page["sha256"])
        result.append(record)
    return result


class MarketAdapter(SourceAdapter):
    root: Path

    def parse(self, content: bytes) -> ParsedDataset:
        ds = ParsedDataset(kind=DatasetKind.MARKET, records={"market": []})
        try:
            bundle = json.loads(content)
            if (bundle["format"] != FORMAT or bundle["source_key"] != self.config.key
                    or bundle["mode"] != self.config.external_mode or not bundle["pages"]):
                raise ValueError("Ungültiges Marktmanifest")
            folder = (self.root / "data/raw/external" / self.config.key).resolve()
            seen = {}
            for page in bundle["pages"]:
                path = (folder / page["path"]).resolve()
                if not path.is_relative_to(folder / "objects"):
                    raise ValueError("Originalpfad ausserhalb des Quellenarchivs")
                raw = path.read_bytes()
                if hashlib.sha256(raw).hexdigest() != page["sha256"]:
                    raise ValueError("Originalprüfsumme stimmt nicht")
                rows = (parse_ncen(raw, page) if bundle["mode"] == "sec_ncen" else
                        parse_tickers(json.loads(raw), bundle["mode"], page))
                for row in rows:
                    key = (row.record_type, row.record_key)
                    if key in seen:
                        # Exact duplicate quarterly disclosures are harmless; contradictions fail.
                        old = seen[key].model_dump(exclude={"source_url", "original_sha256"})
                        new = row.model_dump(exclude={"source_url", "original_sha256"})
                        if old != new:
                            raise ValueError(f"Widersprüchlicher Quellenschlüssel: {key}")
                    else:
                        seen[key] = row
            ds.records["market"] = list(seen.values())
            if not seen:
                raise ValueError("Leerer Marktbestand")
            if bundle["mode"] == "sec_ncen":
                ds.warn("Jährliche Meldungen; Schema 3.1 laut SEC nicht vollständig "
                        "enthalten. Serien-ETF-Status ist kein allgemeiner Anteilsklassennachweis.")
                ds.data_as_of = max(r.report_date for r in seen.values() if r.report_date)
            else:
                ds.warn("SEC-Suchzuordnungen: kein vollständiges Weltuniversum, "
                        "kein gesicherter Instrumenttyp oder heutiger Handelsstatus.")
        except (KeyError, ValueError, TypeError, OSError, zipfile.BadZipFile,
                ValidationError) as exc:
            ds.error(str(exc))
        return ds


def build_market_adapter(config: SourceConfig, catalog: Catalog, root: Path,
                         user_agent: str) -> MarketAdapter:
    adapter = MarketAdapter(config, MarketFetcher(config, root), catalog.criterion_keys)
    adapter.root = root
    return adapter
