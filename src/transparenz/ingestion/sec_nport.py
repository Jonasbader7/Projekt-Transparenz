"""SEC Form N-PORT Data Sets: Quartalsarchive direkt aus dem ZIP lesen und prüfen (D-054).

Ablauf im Update-System (``DataUpdateManager``):

1. ``NportFetcher`` ruft nichts ab. Er sammelt die lokal geladenen Quartalsarchive
   (``raw/external/sec_nport/<JJJJqN>/<JJJJqN>_nport.zip``), prüft jedes gegen seine
   Begleitdatei (SHA-256, D-052) und liefert ein kleines Manifest. Neues Quartal oder
   veränderte Datei = neues Manifest = neuer Datenstand.
2. ``NportAdapter.parse`` liest alle Archive einmal vollständig, ohne etwas zu speichern:
   jede Zeile wird mit Pydantic geprüft; ungültige Zeilen werden abgelehnt und je Grund
   gezählt. Liegt der Anteil abgelehnter Zeilen einer Tabelle über ``MAX_REJECTED_SHARE``,
   wird der ganze Datenstand abgelehnt.
3. ``write_nport`` liest die Archive ein zweites Mal und schreibt in derselben Transaktion,
   in der der Manager die Version aktiviert. Weichen die Zählungen vom ersten Durchgang ab,
   bricht das Schreiben ab (Rollback).

Gemeldete Kennungen bleiben unverändert (``*_reported``); geprüfte Kennungen stehen nur bei
gültiger Prüfziffer daneben. Auswahl je Fondsserie und Stichtag: siehe ``select_filings``.

Speicher: Positionen werden nie als Ganzes im Speicher gehalten (rund 5.6 Mio. je Quartal).
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import zipfile
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import httpx
from pydantic import ValidationError
from sqlalchemy.orm import Session

from transparenz.config.catalog import Catalog, SourceConfig
from transparenz.config.settings import local_data_dir
from transparenz.entities.enums import DatasetKind
from transparenz.entities.identifiers import is_valid_isin, is_valid_lei
from transparenz.entities.nport import NportHolding, NportIdentifier, NportSubmission
from transparenz.ingestion.adapters import SourceAdapter
from transparenz.ingestion.fetchers import FetchError, FetchResult
from transparenz.ingestion.parsing import ParsedDataset
from transparenz.services.provenance import ProvenanceError, describe_file

FORMAT = "transparenz-nport/1"
# Erhöhen, wenn Lese-, Prüf- oder Auswahlregeln ändern: neues Manifest = neuer Datenstand.
RULE_VERSION = "2026-11-15.2"
SOURCE_KEY = "sec_nport"
SOURCE_FOLDER = "raw/external/sec_nport"
DOWNLOAD_BASE = "https://www.sec.gov/files/dera/data/form-n-port-data-sets/"
LISTING_URL = "https://www.sec.gov/data-research/sec-markets-data/form-n-port-data-sets"
TERMS_URL = "https://www.sec.gov/privacy"
TERMS_CHECKED_ON = "2026-11-07"
QUARTER_RE = re.compile(r"^\d{4}q[1-4]$")

# Unsere Setzung: Bei mehr als 1 % abgelehnter Zeilen einer Tabelle ist nicht mehr von
# Einzelfehlern der Meldenden auszugehen, sondern von einem Lese- oder Formatproblem.
MAX_REJECTED_SHARE = 0.01
MAX_UNCOMPRESSED_BYTES = 8_000_000_000
INSERT_CHUNK = 5000
EXAMPLES_PER_REASON = 3

NOT_APPLICABLE = {"N/A", "NA", "N.A.", "NONE"}
_MONTHS = {m: i for i, m in enumerate(
    ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"), 1)}

TABLES: dict[str, tuple[str, ...]] = {
    "SUBMISSION.tsv": ("ACCESSION_NUMBER", "FILING_DATE", "SUB_TYPE", "REPORT_ENDING_PERIOD",
                       "REPORT_DATE", "IS_LAST_FILING"),
    "REGISTRANT.tsv": ("ACCESSION_NUMBER", "CIK", "REGISTRANT_NAME", "LEI"),
    "FUND_REPORTED_INFO.tsv": ("ACCESSION_NUMBER", "SERIES_NAME", "SERIES_ID", "SERIES_LEI",
                               "TOTAL_ASSETS", "NET_ASSETS"),
    "FUND_REPORTED_HOLDING.tsv": (
        "ACCESSION_NUMBER", "HOLDING_ID", "ISSUER_NAME", "ISSUER_LEI", "ISSUER_TITLE",
        "ISSUER_CUSIP", "BALANCE", "UNIT", "CURRENCY_CODE", "CURRENCY_VALUE", "EXCHANGE_RATE",
        "PERCENTAGE", "PAYOFF_PROFILE", "ASSET_CAT", "ISSUER_TYPE", "INVESTMENT_COUNTRY",
        "IS_RESTRICTED_SECURITY", "FAIR_VALUE_LEVEL", "DERIVATIVE_CAT"),
    "IDENTIFIERS.tsv": ("HOLDING_ID", "IDENTIFIERS_ID", "IDENTIFIER_ISIN", "IDENTIFIER_TICKER",
                        "OTHER_IDENTIFIER", "OTHER_IDENTIFIER_DESC"),
}

csv.field_size_limit(1 << 30)


class RowRejected(ValueError):
    """Eine Zeile verletzt das Format der SEC-Readme; sie wird gezählt und übersprungen."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


# ------------------------------------------------------------------------ Feldprüfung


def _text(value: str) -> str | None:
    value = value.strip()
    return value or None


def _day(value: str, name: str) -> date | None:
    value = value.strip()
    if not value:
        return None
    match = re.fullmatch(r"(\d{2})-([A-Za-z]{3})-(\d{4})", value)
    month = _MONTHS.get(match.group(2).upper()) if match else None
    if not match or month is None:
        raise RowRejected(f"date:{name}")
    try:
        return date(int(match.group(3)), month, int(match.group(1)))
    except ValueError as exc:
        raise RowRejected(f"date:{name}") from exc


def _number(value: str, name: str) -> float | None:
    value = value.strip()
    if not value:
        return None
    try:
        number = float(value)
    except ValueError as exc:
        raise RowRejected(f"number:{name}") from exc
    if number != number or number in (float("inf"), float("-inf")):
        raise RowRejected(f"number:{name}")
    return number


def _integer(value: str, name: str) -> int:
    if not re.fullmatch(r"\d{1,18}", value.strip()):
        raise RowRejected(f"integer:{name}")
    return int(value)


def _flag(value: str, name: str) -> bool | None:
    value = value.strip().upper()
    if not value:
        return None
    if value not in {"Y", "N"}:
        raise RowRejected(f"flag:{name}")
    return value == "Y"


def classify_lei(value: str | None) -> tuple[str | None, str | None, str]:
    """(gemeldet, geprüft, Status). Geprüft nur bei gültiger Prüfziffer nach ISO 17442."""
    reported = _text(value or "")
    if reported is None:
        return None, None, "missing"
    clean = reported.upper()
    if clean in NOT_APPLICABLE:
        return reported, None, "not_applicable"
    if not re.fullmatch(r"[A-Z0-9]{18}[0-9]{2}", clean):
        return reported, None, "invalid_format"
    if not is_valid_lei(clean):
        return reported, None, "invalid_checksum"
    return reported, clean, "valid"


def classify_isin(value: str | None) -> tuple[str | None, str | None, str]:
    """(gemeldet, geprüft, Status). Geprüft nur bei gültiger Prüfziffer nach ISO 6166."""
    reported = _text(value or "")
    if reported is None:
        return None, None, "missing"
    clean = reported.upper()
    if clean in NOT_APPLICABLE:
        return reported, None, "not_applicable"
    if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", clean):
        return reported, None, "invalid_format"
    if not is_valid_isin(clean):
        return reported, None, "invalid_checksum"
    return reported, clean, "valid"


def _accession(value: str) -> str:
    value = value.strip()
    if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", value):
        raise RowRejected("key:ACCESSION_NUMBER")
    return value


# ------------------------------------------------------------------------ Zählung


@dataclass
class TableStats:
    quarter: str
    table: str
    read: int = 0
    accepted: int = 0
    rejected: Counter = field(default_factory=Counter)
    examples: dict[str, list[int]] = field(default_factory=dict)

    def reject(self, reason: str, line: int) -> None:
        self.rejected[reason] += 1
        lines = self.examples.setdefault(reason, [])
        if len(lines) < EXAMPLES_PER_REASON:
            lines.append(line)

    @property
    def rejected_total(self) -> int:
        return sum(self.rejected.values())

    def as_dict(self) -> dict[str, Any]:
        return {"quarter": self.quarter, "table": self.table, "read": self.read,
                "accepted": self.accepted, "rejected": dict(sorted(self.rejected.items())),
                "example_lines": dict(sorted(self.examples.items()))}


# ------------------------------------------------------------------------ Archiv lesen


def _rows(archive: zipfile.ZipFile, name: str) -> Iterator[tuple[int, dict[str, str] | None]]:
    """(Zeilennummer, Feld → Wert). ``None`` bei falscher Spaltenzahl. Pflichtspalten geprüft."""
    with archive.open(name) as stream:
        reader = csv.reader(io.TextIOWrapper(stream, encoding="utf-8", newline=""),
                            delimiter="\t", quoting=csv.QUOTE_NONE)
        header = next(reader, None)
        if header is None:
            raise ValueError(f"{name}: leere Datei")
        header = [h.lstrip("﻿") for h in header]
        missing = [c for c in TABLES[name] if c not in header]
        if missing:
            raise ValueError(f"{name}: Pflichtspalten fehlen: {', '.join(missing)}")
        width = len(header)
        for line, values in enumerate(reader, start=2):
            yield line, (dict(zip(header, values, strict=True)) if len(values) == width
                         else None)


def _validated(stats: TableStats, line: int, build: Callable[[], Any]) -> Any | None:
    stats.read += 1
    try:
        item = build()
    except RowRejected as exc:
        stats.reject(exc.reason, line)
        return None
    except ValidationError as exc:
        fields = sorted({str(e["loc"][0]) for e in exc.errors() if e.get("loc")})
        stats.reject("validation:" + (",".join(fields) or "?"), line)
        return None
    stats.accepted += 1
    return item


def read_submissions(archive: zipfile.ZipFile, quarter: str,
                     stats: dict[str, TableStats]) -> dict[str, NportSubmission]:
    """Meldungen mit Registrant und Fondsangaben (klein, im Speicher)."""
    def side_table(name: str) -> dict[str, dict[str, str]]:
        st = stats.setdefault(name, TableStats(quarter, name))
        rows: dict[str, dict[str, str]] = {}
        for line, row in _rows(archive, name):
            st.read += 1
            if row is None:
                st.reject("column_count", line)
                continue
            key = row["ACCESSION_NUMBER"].strip()
            if key in rows:
                st.reject("duplicate_key", line)
                continue
            rows[key] = row
            st.accepted += 1
        return rows

    registrants = side_table("REGISTRANT.tsv")
    funds = side_table("FUND_REPORTED_INFO.tsv")
    st = stats.setdefault("SUBMISSION.tsv", TableStats(quarter, "SUBMISSION.tsv"))
    result: dict[str, NportSubmission] = {}
    for line, row in _rows(archive, "SUBMISSION.tsv"):
        if row is None:
            st.read += 1
            st.reject("column_count", line)
            continue
        if row["ACCESSION_NUMBER"].strip() in result:
            st.read += 1
            st.reject("duplicate_key", line)
            continue

        def build(row: dict[str, str] = row) -> NportSubmission:
            accession = _accession(row["ACCESSION_NUMBER"])
            reg = registrants.get(accession, {})
            fund = funds.get(accession, {})
            reg_lei, reg_valid, _ = classify_lei(reg.get("LEI"))
            series_lei, series_valid, _ = classify_lei(fund.get("SERIES_LEI"))
            series = _text(fund.get("SERIES_ID", ""))
            cik = _text(reg.get("CIK", ""))
            filing, report = (_day(row["FILING_DATE"], "FILING_DATE"),
                              _day(row["REPORT_DATE"], "REPORT_DATE"))
            if filing is None:
                raise RowRejected("missing:FILING_DATE")
            if report is None:
                raise RowRejected("missing:REPORT_DATE")
            return NportSubmission(
                quarter=quarter, accession=accession, filing_date=filing,
                sub_type=_text(row["SUB_TYPE"]) or "", report_date=report,
                fiscal_year_end=_day(row["REPORT_ENDING_PERIOD"], "REPORT_ENDING_PERIOD"),
                is_last_filing=_flag(row["IS_LAST_FILING"], "IS_LAST_FILING"),
                cik=cik.zfill(10) if cik and cik.isdigit() and len(cik) <= 10 else None,
                registrant_name=_text(reg.get("REGISTRANT_NAME", "")),
                registrant_lei_reported=reg_lei, registrant_lei=reg_valid,
                series_id=series if series and re.fullmatch(r"S\d{9}", series)
                and series != "S000000000" else None,
                series_id_reported=series, series_name=_text(fund.get("SERIES_NAME", "")),
                series_lei_reported=series_lei, series_lei=series_valid,
                total_assets=_number(fund.get("TOTAL_ASSETS", ""), "TOTAL_ASSETS"),
                net_assets=_number(fund.get("NET_ASSETS", ""), "NET_ASSETS"))

        item = _validated(st, line, build)
        if item is not None:
            result[item.accession] = item
    for name, table in (("REGISTRANT.tsv", registrants), ("FUND_REPORTED_INFO.tsv", funds)):
        orphans = sum(1 for key in table if key not in result)
        if orphans:
            stats[name].rejected["unknown_accession"] += orphans
            stats[name].accepted -= orphans
    return result


def iter_holdings(archive: zipfile.ZipFile, quarter: str, accessions: set[str],
                  stats: TableStats) -> Iterator[NportHolding]:
    for line, row in _rows(archive, "FUND_REPORTED_HOLDING.tsv"):
        if row is None:
            stats.read += 1
            stats.reject("column_count", line)
            continue

        def build(row: dict[str, str] = row) -> NportHolding:
            accession = _accession(row["ACCESSION_NUMBER"])
            if accession not in accessions:
                raise RowRejected("unknown_accession")
            lei_reported, lei, lei_status = classify_lei(row["ISSUER_LEI"])
            return NportHolding(
                quarter=quarter, accession=accession,
                holding_id=_integer(row["HOLDING_ID"], "HOLDING_ID"),
                issuer_name=_text(row["ISSUER_NAME"]), issuer_lei_reported=lei_reported,
                issuer_lei=lei, issuer_lei_status=lei_status, title=_text(row["ISSUER_TITLE"]),
                cusip=_text(row["ISSUER_CUSIP"]),
                balance=_number(row["BALANCE"], "BALANCE"), unit=_text(row["UNIT"]),
                currency=_text(row["CURRENCY_CODE"]),
                value=_number(row["CURRENCY_VALUE"], "CURRENCY_VALUE"),
                exchange_rate=_number(row["EXCHANGE_RATE"], "EXCHANGE_RATE"),
                percentage=_number(row["PERCENTAGE"], "PERCENTAGE"),
                payoff_profile=_text(row["PAYOFF_PROFILE"]), asset_cat=_text(row["ASSET_CAT"]),
                issuer_type=_text(row["ISSUER_TYPE"]), country=_text(row["INVESTMENT_COUNTRY"]),
                is_restricted=_flag(row["IS_RESTRICTED_SECURITY"], "IS_RESTRICTED_SECURITY"),
                fair_value_level=_text(row["FAIR_VALUE_LEVEL"]),
                derivative_cat=_text(row["DERIVATIVE_CAT"]))

        item = _validated(stats, line, build)
        if item is not None:
            yield item


def iter_identifiers(archive: zipfile.ZipFile, quarter: str,
                     stats: TableStats) -> Iterator[NportIdentifier]:
    for line, row in _rows(archive, "IDENTIFIERS.tsv"):
        if row is None:
            stats.read += 1
            stats.reject("column_count", line)
            continue

        def build(row: dict[str, str] = row) -> NportIdentifier:
            isin_reported, isin, isin_status = classify_isin(row["IDENTIFIER_ISIN"])
            return NportIdentifier(
                quarter=quarter, holding_id=_integer(row["HOLDING_ID"], "HOLDING_ID"),
                identifier_id=_integer(row["IDENTIFIERS_ID"], "IDENTIFIERS_ID"),
                isin_reported=isin_reported, isin=isin, isin_status=isin_status,
                ticker=_text(row["IDENTIFIER_TICKER"]),
                other_identifier=_text(row["OTHER_IDENTIFIER"]),
                other_identifier_desc=_text(row["OTHER_IDENTIFIER_DESC"]))

        item = _validated(stats, line, build)
        if item is not None:
            yield item


# ------------------------------------------------------------------------ Auswahl


def fund_keys(submissions: Iterable[NportSubmission]) -> dict[tuple[str, str], str | None]:
    """Fondsschlüssel je Meldung: Serien-ID, sonst «CIK» + CIK des Registranten.

    Ohne Serie (z. B. geschlossene Fonds ohne Serienstruktur) ist der Registrant selbst der
    Fonds – aber nur, wenn derselbe Registrant nirgends mit Serie meldet. Sonst bleibt offen,
    zu welcher Serie die Meldung gehört (``None``).
    """
    subs = list(submissions)
    with_series = {s.cik for s in subs if s.series_id and s.cik}
    keys: dict[tuple[str, str], str | None] = {}
    for s in subs:
        if s.series_id:
            key: str | None = s.series_id
        elif s.cik and s.cik not in with_series:
            key = "CIK" + s.cik
        else:
            key = None
        keys[(s.quarter, s.accession)] = key
    return keys


def select_filings(submissions: Iterable[NportSubmission]) -> dict[tuple[str, str], str]:
    """Welche Meldung gilt je Fonds und Stichtag? Schlüssel (Quartal, Accession).

    Unsere Regel (nicht aus der SEC-Readme, dort nur «includes any amendments»):
    - Fonds = Serie, ohne Serie der Registrant (``fund_keys``).
    - ``no_series``: kein Fondsschlüssel bestimmbar (Registrant meldet auch mit Serie).
    - ``notice``: Mitteilungen über verspätete Meldung (``NT …``) enthalten keine Positionen.
    - Je Serie und Stichtag gilt die zuletzt eingereichte Meldung; frühere werden
      ``superseded``. Haben mehrere Meldungen dasselbe späteste Einreichdatum, entscheidet
      nichts zwischen ihnen: alle ``tie`` (keine Wahl nach Nummernfolge).
    - Je Serie ist der jüngste Stichtag ``current``, ältere Stichtage ``earlier_period``.
      Ist der jüngste Stichtag unentschieden, hat die Serie keinen ``current``-Stand.
    """
    subs = list(submissions)
    funds = fund_keys(subs)
    result: dict[tuple[str, str], str] = {}
    by_series: dict[str, dict[date, list[NportSubmission]]] = defaultdict(lambda:
                                                                          defaultdict(list))
    for sub in subs:
        key = (sub.quarter, sub.accession)
        fund = funds[key]
        if sub.sub_type.upper().startswith("NT"):
            result[key] = "notice"
        elif fund is None:
            result[key] = "no_series"
        else:
            by_series[fund][sub.report_date].append(sub)
    for periods in by_series.values():
        latest_period = max(periods)
        for period, subs in periods.items():
            last = max(s.filing_date for s in subs)
            winners = [s for s in subs if s.filing_date == last]
            for sub in subs:
                key = (sub.quarter, sub.accession)
                if sub.filing_date != last:
                    result[key] = "superseded"
                elif len(winners) > 1:
                    result[key] = "tie"
                else:
                    result[key] = "current" if period == latest_period else "earlier_period"
    return result


# ------------------------------------------------------------------------ Manifest


def snapshot_folder(data_dir: Path) -> Path:
    return data_dir / SOURCE_FOLDER


def local_archives(data_dir: Path) -> list[dict[str, Any]]:
    """Alle lokal geladenen Quartalsarchive mit geprüfter Herkunft, ältestes zuerst."""
    folder = snapshot_folder(data_dir)
    archives = []
    if not folder.is_dir():
        return archives
    for sub in sorted(p for p in folder.iterdir() if p.is_dir() and QUARTER_RE.match(p.name)):
        path = sub / f"{sub.name}_nport.zip"
        if not path.is_file():
            continue
        record = describe_file(path, data_dir, SOURCE_KEY)  # ProvenanceError bei Abweichung
        if record.status != "verified":
            raise ProvenanceError(f"{path}: keine Begleitdatei mit Prüfsumme – nicht verwendet.")
        meta = json.loads((sub / "source.metadata.json").read_bytes())
        archives.append({"quarter": sub.name, "path": record.path, "sha256": record.sha256,
                         "bytes": record.bytes, "url": meta.get("url"),
                         "retrieved": record.retrieved})
    return archives


def encoded(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=1).encode("utf-8")


class NportFetcher:
    """Kein Netzabruf: liefert das Manifest der lokal geladenen, geprüften Archive."""

    def __init__(self, config: SourceConfig, root: Path):
        self.config, self.root = config, root

    def fetch(self, etag: str | None = None, last_modified: str | None = None) -> FetchResult:
        data_dir = local_data_dir(self.root)
        try:
            archives = local_archives(data_dir)
        except ProvenanceError as exc:
            raise FetchError(str(exc), transient=False) from exc
        if not archives:
            raise FetchError("Kein lokales N-PORT-Archiv. Zuerst «nport-download <Quartal> "
                             "--confirm» ausführen.", transient=False)
        return FetchResult(origin=str(snapshot_folder(data_dir)), content=encoded({
            "format": FORMAT, "rule_version": RULE_VERSION, "source_key": self.config.key,
            "archives": archives}))


# ------------------------------------------------------------------------ Parser


@dataclass
class NportDataset(ParsedDataset):
    archives: list[dict[str, Any]] = field(default_factory=list)
    stats: list[TableStats] = field(default_factory=list)
    data_dir: Path | None = None

    @property
    def record_count(self) -> int:
        wanted = {"SUBMISSION.tsv", "FUND_REPORTED_HOLDING.tsv", "IDENTIFIERS.tsv"}
        return sum(s.accepted for s in self.stats if s.table in wanted)

    def counts(self) -> dict[tuple[str, str], tuple[int, int]]:
        return {(s.quarter, s.table): (s.read, s.accepted) for s in self.stats}


def _open_archive(entry: dict[str, Any], data_dir: Path) -> zipfile.ZipFile:
    folder = snapshot_folder(data_dir).resolve()
    path = (data_dir / entry["path"]).resolve()
    if not path.is_relative_to(folder):
        raise ValueError("Archivpfad ausserhalb des N-PORT-Ordners")
    record = describe_file(path, data_dir, SOURCE_KEY)
    if record.status != "verified" or record.sha256 != entry["sha256"]:
        raise ProvenanceError(f"{path}: Prüfsumme weicht vom Manifest ab.")
    archive = zipfile.ZipFile(path)
    names = {i.filename for i in archive.infolist()}
    missing = sorted(set(TABLES) - names)
    if missing:
        archive.close()
        raise ValueError(f"{path.name}: Tabellen fehlen: {', '.join(missing)}")
    if sum(i.file_size for i in archive.infolist()) > MAX_UNCOMPRESSED_BYTES:
        archive.close()
        raise ValueError(f"{path.name}: Archiv überschreitet Grössenlimit")
    return archive


def _read_all(ds: NportDataset, data_dir: Path,
              sink: Callable[[str, str, Any], None] | None = None) -> list[NportSubmission]:
    """Ein vollständiger Durchgang über alle Archive; ``sink`` erhält jede gültige Zeile."""
    submissions: list[NportSubmission] = []
    for entry in ds.archives:
        quarter = entry["quarter"]
        with _open_archive(entry, data_dir) as archive:
            stats: dict[str, TableStats] = {}
            subs = read_submissions(archive, quarter, stats)
            submissions.extend(subs.values())
            holdings = TableStats(quarter, "FUND_REPORTED_HOLDING.tsv")
            for item in iter_holdings(archive, quarter, set(subs), holdings):
                if sink:
                    sink(quarter, "holding", item)
            identifiers = TableStats(quarter, "IDENTIFIERS.tsv")
            for item in iter_identifiers(archive, quarter, identifiers):
                if sink:
                    sink(quarter, "identifier", item)
            ds.stats.extend([*stats.values(), holdings, identifiers])
    return submissions


def parse_manifest(content: bytes, root: Path, config_key: str = SOURCE_KEY) -> NportDataset:
    ds = NportDataset(kind=DatasetKind.NPORT)
    data_dir = local_data_dir(root)
    ds.data_dir = data_dir
    try:
        bundle = json.loads(content)
        if bundle.get("format") != FORMAT or bundle.get("source_key") != config_key:
            raise ValueError("Ungültiges N-PORT-Manifest")
        ds.archives = list(bundle["archives"])
        if not ds.archives:
            raise ValueError("Manifest ohne Archiv")
        if len({a["quarter"] for a in ds.archives}) != len(ds.archives):
            raise ValueError("Quartal doppelt im Manifest")
        submissions = _read_all(ds, data_dir)
    except (KeyError, ValueError, TypeError, OSError, zipfile.BadZipFile, ProvenanceError,
            UnicodeDecodeError, csv.Error) as exc:
        ds.error(f"N-PORT nicht lesbar: {exc}")
        return ds
    for st in ds.stats:
        if st.read and st.rejected_total / st.read > MAX_REJECTED_SHARE:
            ds.error(f"{st.quarter} {st.table}: {st.rejected_total} von {st.read} Zeilen "
                     f"abgelehnt (mehr als {MAX_REJECTED_SHARE:.0%}); Datenstand abgelehnt.")
        if st.rejected_total:
            reasons = ", ".join(f"{k} {v}" for k, v in st.rejected.most_common())
            ds.warn(f"{st.quarter} {st.table}: {st.rejected_total} Zeilen abgelehnt ({reasons}).")
    if not any(s.table == "FUND_REPORTED_HOLDING.tsv" and s.accepted for s in ds.stats):
        ds.error("Keine gültige Position gelesen.")
    selection = Counter(select_filings(submissions).values())
    if selection.get("tie"):
        ds.warn(f"{selection['tie']} Meldungen mit gleichem Einreichdatum für dieselbe Serie "
                "und denselben Stichtag: keine gewählt.")
    ds.warn("Daten «as filed» der Fonds; die SEC garantiert die Richtigkeit nicht.")
    ds.data_as_of = max((s.report_date for s in submissions), default=None)
    return ds


class NportAdapter(SourceAdapter):
    root: Path

    def parse(self, content: bytes) -> ParsedDataset:
        return parse_manifest(content, self.root, self.config.key)


def build_nport_adapter(config: SourceConfig, catalog: Catalog, root: Path) -> NportAdapter:
    adapter = NportAdapter(config, NportFetcher(config, root), catalog.criterion_keys)
    adapter.root = root
    return adapter


# ------------------------------------------------------------------------ Schreiben

_SUBMISSION_COLS = (*NportSubmission.model_fields, "fund_key", "selection")
_HOLDING_COLS = tuple(NportHolding.model_fields)
_IDENTIFIER_COLS = tuple(NportIdentifier.model_fields)


def _db_value(value: Any) -> Any:
    """Werte so ablegen, wie SQLAlchemy sie für SQLite schreibt (Datum als ISO-Text)."""
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bool):
        return int(value)
    return value


def _insert_sql(table: str, columns: tuple[str, ...]) -> str:
    names = ", ".join(("dataset_version_id", *columns))
    marks = ", ".join("?" * (len(columns) + 1))
    return f"INSERT INTO {table} ({names}) VALUES ({marks})"


def write_nport(session: Session, version_id: int, parsed: ParsedDataset) -> int:
    """Zweiter Durchgang: schreibt alles in die offene Transaktion des Managers (kein Commit)."""
    if not isinstance(parsed, NportDataset) or parsed.data_dir is None:
        raise TypeError("write_nport braucht ein NportDataset")
    expected = parsed.counts()
    again = NportDataset(kind=DatasetKind.NPORT, archives=parsed.archives,
                         data_dir=parsed.data_dir)
    conn = session.connection()
    buffers: dict[str, list[tuple]] = {"holding": [], "identifier": []}
    sql = {"holding": _insert_sql("nport_holdings", _HOLDING_COLS),
           "identifier": _insert_sql("nport_identifiers", _IDENTIFIER_COLS)}
    columns = {"holding": _HOLDING_COLS, "identifier": _IDENTIFIER_COLS}

    def flush(kind: str) -> None:
        if buffers[kind]:
            conn.exec_driver_sql(sql[kind], buffers[kind])
            buffers[kind] = []

    def sink(_quarter: str, kind: str, item: Any) -> None:
        data = item.model_dump()
        buffers[kind].append((version_id, *(_db_value(data[c]) for c in columns[kind])))
        if len(buffers[kind]) >= INSERT_CHUNK:
            flush(kind)

    submissions = _read_all(again, parsed.data_dir, sink)
    flush("holding")
    flush("identifier")
    if again.counts() != expected:
        raise RuntimeError("Zweiter Lesedurchgang weicht vom geprüften ersten ab – Abbruch.")
    selection = select_filings(submissions)
    funds = fund_keys(submissions)
    rows = []
    for s in submissions:
        data = s.model_dump()
        key = (s.quarter, s.accession)
        rows.append((version_id, *(_db_value(data[c]) for c in _SUBMISSION_COLS[:-2]),
                     funds[key], selection[key]))
    if rows:
        conn.exec_driver_sql(_insert_sql("nport_submissions", _SUBMISSION_COLS), rows)
    # Je Position die gemeldete(n) ISIN zusammenfassen: genau eine gültige → übernommen.
    conn.exec_driver_sql("DROP TABLE IF EXISTS temp.nport_isin_agg")
    conn.exec_driver_sql(
        "CREATE TEMP TABLE nport_isin_agg AS SELECT quarter, holding_id, MIN(isin) AS isin, "
        "COUNT(DISTINCT isin) AS n_valid, SUM(isin_status NOT IN ('valid', 'missing')) AS n_bad "
        "FROM nport_identifiers WHERE dataset_version_id = ? GROUP BY quarter, holding_id",
        (version_id,))
    conn.exec_driver_sql("CREATE INDEX temp.ix_nport_isin_agg ON nport_isin_agg "
                         "(quarter, holding_id)")
    conn.exec_driver_sql(
        "UPDATE nport_holdings SET "
        "isin = CASE WHEN a.n_valid = 1 THEN a.isin END, "
        "isin_status = CASE WHEN a.n_valid = 1 THEN 'valid' WHEN a.n_valid > 1 THEN 'multiple' "
        "WHEN a.n_bad > 0 THEN 'invalid' ELSE 'missing' END "
        "FROM nport_isin_agg AS a WHERE nport_holdings.dataset_version_id = ? "
        "AND a.quarter = nport_holdings.quarter AND a.holding_id = nport_holdings.holding_id",
        (version_id,))
    conn.exec_driver_sql("UPDATE nport_holdings SET isin_status = 'missing' "
                         "WHERE dataset_version_id = ? AND isin_status IS NULL", (version_id,))
    conn.exec_driver_sql("DROP TABLE temp.nport_isin_agg")
    conn.exec_driver_sql(
        "INSERT INTO nport_load_stats (dataset_version_id, quarter, table_name, rows_read, "
        "rows_accepted, rejected_json) VALUES (?, ?, ?, ?, ?, ?)",
        [(version_id, s.quarter, s.table, s.read, s.accepted,
          json.dumps({"rejected": dict(s.rejected), "example_lines": s.examples},
                     ensure_ascii=False, sort_keys=True)) for s in again.stats])
    session.flush()
    return again.record_count


# ------------------------------------------------------------------------ Herunterladen


def download_quarter(quarter: str, data_dir: Path, contact: str, *, confirm: bool,
                     client: httpx.Client | None = None,
                     now: Callable[[], datetime] = lambda: datetime.now(UTC)) -> dict[str, Any]:
    """Lädt ein Quartalsarchiv der SEC. Ohne ``confirm`` nur Name, Quelle und Grösse.

    Der Kontakt (E-Mail) steht nur im User-Agent, den die SEC verlangt; nie in Dateien.
    """
    if not QUARTER_RE.match(quarter):
        raise ValueError("Quartal im Format JJJJqN angeben, z. B. 2026q3.")
    if not re.fullmatch(r"[^\s@()]+@[^\s@()]+\.[^\s@()]+", contact or ""):
        raise ValueError("TRANSPARENZ_SEC_CONTACT lokal in .env setzen (Kontakt-E-Mail).")
    name = f"{quarter}_nport.zip"
    url = DOWNLOAD_BASE + name
    folder = snapshot_folder(data_dir) / quarter
    target = folder / name
    if target.exists():
        raise FileExistsError(f"{target} existiert bereits; nichts heruntergeladen.")
    own = client is None
    client = client or httpx.Client(timeout=120, follow_redirects=False,
                                    headers={"User-Agent": f"ProjektTransparenz/0.1 ({contact})"})
    try:
        head = client.head(url)
        if head.status_code != 200:
            raise FetchError(f"HTTP {head.status_code} bei {url}", transient=False)
        size = int(head.headers.get("Content-Length", "0"))
        info = {"file": name, "url": url, "size_bytes": size,
                "size_mb": round(size / 1024 / 1024, 2), "target": str(target),
                "downloaded": False}
        if not confirm:
            return info
        folder.mkdir(parents=True, exist_ok=True)
        part = target.with_name(name + ".part")
        digest = hashlib.sha256()
        started = now()
        with client.stream("GET", url) as response:
            if response.status_code != 200:
                raise FetchError(f"HTTP {response.status_code} bei {url}", transient=False)
            last_modified = response.headers.get("Last-Modified")
            with part.open("wb") as handle:
                for block in response.iter_bytes(1 << 20):
                    digest.update(block)
                    handle.write(block)
        written = part.stat().st_size
        if size and written != size:
            part.unlink()
            raise FetchError(f"{name}: {written} statt {size} Bytes erhalten.", transient=True)
        with zipfile.ZipFile(part) as archive:
            broken = archive.testzip()
        if broken is not None:
            part.unlink()
            raise FetchError(f"{name}: Archiveintrag {broken} beschädigt.", transient=True)
        part.replace(target)
        meta = {"source_key": SOURCE_KEY,
                "publisher": "U.S. Securities and Exchange Commission (DERA) - Form N-PORT "
                             "Data Sets",
                "file": name, "url": url, "listing_url": LISTING_URL, "terms_url": TERMS_URL,
                "license": "SEC public-information dissemination permission "
                           "(keine benannte Lizenz)",
                "terms_checked_on": TERMS_CHECKED_ON,
                "retrieved_at_utc": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "http_last_modified": last_modified, "size_bytes": written,
                "sha256": digest.hexdigest(),
                "approved_by": "Befehl nport-download --confirm", "status": "raw_snapshot"}
        (folder / "source.metadata.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {**info, "size_bytes": written, "sha256": meta["sha256"], "downloaded": True}
    finally:
        if own:
            client.close()
