"""SEC Form N-CEN: Anlageberater je Fonds, als Grundlage für «unabhängige Meldende».

Wofür: Im Wertpapierstamm (``services/security_master.py``) gilt eine ISIN → LEI erst als
bestätigt, wenn mindestens zwei *unabhängige* Fondsgesellschaften denselben LEI melden. Eine
CIK (Registrant, meist ein Trust) ist dafür zu fein: Grosse Anbieter melden über Dutzende
Trusts mit denselben Stammdaten. N-CEN nennt je Fonds den Anlageberater mit Kennungen
(LEI, SEC-Registrierungsnummer «801-…», CRD-Nummer). Daraus bilden wir Berater-Schlüssel;
Fonds mit gemeinsamem Schlüssel gelten als nicht unabhängig.

Gelesen werden nur die lokal vorhandenen Quartalsarchive des SEC-Marktkatalogs
(``raw/external/sec_ncen/objects/*.zip`` mit Begleitdatei, D-052). Nichts wird abgerufen.
Verwendet werden nur Berater vom Typ ``Advisor`` (nicht ``Subadvisor``, nicht
``Terminated …``): Unterberater verwalten oft für viele fremde Fondsfamilien und würden
unabhängige Gesellschaften fälschlich verbinden. Namen werden nie als Schlüssel verwendet.
"""

from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from transparenz.entities.identifiers import is_valid_lei
from transparenz.services.provenance import FileProvenance, ProvenanceError, describe_file

SOURCE_KEY = "sec_ncen"
OBJECT_FOLDER = "raw/external/sec_ncen/objects"
URL_QUARTER = re.compile(r"/form-n-cen-data-sets/(\d{4}q[1-4])_ncen\.zip$")
ADVISER_TYPE = "Advisor"
SERIES_RE = re.compile(r"^S\d{9}$")
SEC_FILE_RE = re.compile(r"^801-\d{1,6}$")

csv.field_size_limit(1 << 30)


@dataclass(frozen=True)
class AdviserRef:
    """Kennungen eines Beraters aus einer N-CEN-Zeile (leer, wenn nicht oder ungültig gemeldet)."""

    lei: str | None
    sec_file: str | None
    crd: str | None


@dataclass
class FundAdvisers:
    """Berater je N-PORT-Fondsschlüssel (Serien-ID oder «CIK» + CIK)."""

    by_fund: dict[str, set[AdviserRef]] = field(default_factory=lambda: defaultdict(set))
    archives: list[FileProvenance] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    def adviser_leis(self) -> set[str]:
        return {a.lei for refs in self.by_fund.values() for a in refs if a.lei}


def local_archives(data_dir: Path) -> list[tuple[str, Path]]:
    """(Quartal, Archiv) je Quartal, jeweils der zuletzt geladene Stand."""
    folder = data_dir / OBJECT_FOLDER
    if not folder.is_dir():
        return []
    best: dict[str, tuple[str, Path]] = {}
    for meta_path in folder.glob("*.zip.metadata.json"):
        meta = json.loads(meta_path.read_bytes())
        match = URL_QUARTER.search(str(meta.get("url") or ""))
        archive = meta_path.with_name(meta_path.name[: -len(".metadata.json")])
        if not match or not archive.is_file():
            continue
        stamp = str(meta.get("downloaded_at") or "")
        quarter = match.group(1)
        if quarter not in best or stamp > best[quarter][0]:
            best[quarter] = (stamp, archive)
    return [(q, best[q][1]) for q in sorted(best)]


def _tsv(archive: zipfile.ZipFile, name: str, required: set[str]):
    # Gleiche Leseweise wie der SEC-Marktkatalog (ingestion/markets.py), der dieselben
    # Archive bereits vollständig liest; falsche Spaltenzahl = Fehler, nichts wird erraten.
    with archive.open(name) as raw:
        reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig"), delimiter="\t")
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"N-CEN {name}: Spalten fehlen: {sorted(missing)}")
        for row in reader:
            if None in row or any(v is None for v in row.values()):
                raise ValueError(f"N-CEN {name}: ungültige Spaltenanzahl")
            yield row


def adviser_ref(row: dict[str, str]) -> AdviserRef | None:
    lei = (row.get("ADVISER_LEI") or "").strip().upper()
    sec_file = (row.get("FILE_NUM") or "").strip()
    crd = (row.get("CRD_NUM") or "").strip().lstrip("0")
    ref = AdviserRef(lei=lei if is_valid_lei(lei) else None,
                     sec_file=sec_file if SEC_FILE_RE.fullmatch(sec_file) else None,
                     crd=crd if crd.isdigit() else None)
    return ref if (ref.lei or ref.sec_file or ref.crd) else None


def read_archive(path: Path, result: FundAdvisers) -> None:
    """Berater eines Quartalsarchivs hinzufügen (Vereinigung über alle Meldungen)."""
    counts = result.stats.setdefault("rows", defaultdict(int))
    with zipfile.ZipFile(path) as archive:
        ciks = {r["ACCESSION_NUMBER"]: r["CIK"].strip().zfill(10)
                for r in _tsv(archive, "SUBMISSION.tsv", {"ACCESSION_NUMBER", "CIK"})
                if r["CIK"].strip().isdigit()}
        funds: dict[str, str] = {}
        for r in _tsv(archive, "FUND_REPORTED_INFO.tsv",
                      {"FUND_ID", "ACCESSION_NUMBER", "SERIES_ID"}):
            series = r["SERIES_ID"].strip()
            if SERIES_RE.fullmatch(series) and series != "S000000000":
                funds[r["FUND_ID"]] = series
            elif r["ACCESSION_NUMBER"] in ciks:
                # Ohne Serie: wie in N-PORT der Registrant als Fonds («CIK» + CIK).
                funds[r["FUND_ID"]] = "CIK" + ciks[r["ACCESSION_NUMBER"]]
        for r in _tsv(archive, "ADVISER.tsv", {"FUND_ID", "ADVISER_TYPE", "ADVISER_LEI",
                                               "FILE_NUM", "CRD_NUM"}):
            if r["ADVISER_TYPE"].strip() != ADVISER_TYPE:
                counts["other_type"] += 1
                continue
            fund = funds.get(r["FUND_ID"])
            ref = adviser_ref(r)
            if fund is None:
                counts["fund_unknown"] += 1
            elif ref is None:
                counts["no_identifier"] += 1
            else:
                counts["used"] += 1
                result.by_fund[fund].add(ref)


def load_fund_advisers(data_dir: Path) -> FundAdvisers:
    """Alle lokalen N-CEN-Quartale lesen; jedes Archiv vorher gegen seine Begleitdatei prüfen."""
    result = FundAdvisers()
    for quarter, path in local_archives(data_dir):
        record = describe_file(path, data_dir, SOURCE_KEY)
        if record.status != "verified":
            raise ProvenanceError(f"{record.path}: keine Begleitdatei mit Prüfsumme.")
        read_archive(path, result)
        result.archives.append(record)
        result.stats.setdefault("quarters", []).append(quarter)
    result.stats["rows"] = dict(result.stats.get("rows", {}))
    result.stats["funds_with_adviser"] = len(result.by_fund)
    return result
