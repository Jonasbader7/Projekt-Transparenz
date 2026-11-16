"""GLEIF Golden Copy, Level 1 (alle LEI-Datensätze): lokal lesen, nur gesuchte LEI behalten.

Die Datei (rund 5 GB entpackt, 3.5 Mio. Zeilen, 338 Spalten) wird direkt aus dem ZIP
gelesen; behalten werden nur die übergebenen LEI. Vorher wird das Archiv gegen seine
Begleitdatei geprüft (D-052). Rein lokal, kein Netz.

Bedeutung der Felder laut GLEIF Common Data File 3.1:
- ``Entity.EntityStatus``: ``ACTIVE`` = der Rechtsträger besteht, ``INACTIVE`` = nicht mehr
  (aufgelöst, fusioniert usw.).
- ``Registration.RegistrationStatus``: Zustand des LEI-Datensatzes, z. B. ``ISSUED``
  (gepflegt), ``LAPSED`` (Verlängerung überfällig, Angaben evtl. veraltet), ``RETIRED``,
  ``MERGED``, ``ANNULLED``, ``DUPLICATE``.
"""

from __future__ import annotations

import csv
import io
import re
import zipfile
from collections.abc import Iterable
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from transparenz.services.provenance import FileProvenance, ProvenanceError, describe_file

SOURCE_KEY = "gleif_lei2_golden_copy"
FOLDER = "raw/external/gleif_lei2_golden_copy"
ARCHIVE_NAME = "gleif-goldencopy-lei2.csv.zip"
COLUMNS = ("LEI", "Entity.EntityStatus", "Registration.RegistrationStatus",
           "Entity.LegalAddress.Country", "Registration.LastUpdateDate",
           "Registration.NextRenewalDate", "Entity.SuccessorEntity.1.SuccessorLEI")

csv.field_size_limit(1 << 30)


class LeiRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    lei: str = Field(pattern=r"^[A-Z0-9]{18}[0-9]{2}$")
    entity_status: str = Field(pattern=r"^[A-Z_]*$")
    registration_status: str = Field(pattern=r"^[A-Z_]+$")
    country: str | None = None
    last_update: str | None = None
    next_renewal: str | None = None
    successor_lei: str | None = None


def latest_snapshot(data_dir: Path) -> FileProvenance | None:
    """Jüngster lokal geladener Stand (Ordner JJJJ-MM-TT), gegen die Begleitdatei geprüft."""
    folder = data_dir / FOLDER
    if not folder.is_dir():
        return None
    dated = sorted((p for p in folder.iterdir()
                    if p.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.name)
                    and (p / ARCHIVE_NAME).is_file()), reverse=True)
    if not dated:
        return None
    record = describe_file(dated[0] / ARCHIVE_NAME, data_dir, SOURCE_KEY)
    if record.status != "verified":
        raise ProvenanceError(f"{record.path}: keine Begleitdatei mit Prüfsumme.")
    return record


def _date(value: str) -> str | None:
    return value[:10] if re.match(r"\d{4}-\d{2}-\d{2}", value or "") else None


def load_lei_records(archive_path: Path, wanted: Iterable[str]) -> tuple[dict[str, LeiRecord],
                                                                         int]:
    """(gesuchte LEI → Datensatz, gelesene Zeilen). Doppelte LEI in der Datei = Fehler."""
    wanted = {w.upper() for w in wanted}
    found: dict[str, LeiRecord] = {}
    rows = 0
    with zipfile.ZipFile(archive_path) as archive:
        members = [n for n in archive.namelist() if n.lower().endswith(".csv")]
        if len(members) != 1:
            raise ValueError(f"{archive_path.name}: genau eine CSV erwartet, {len(members)}.")
        with archive.open(members[0]) as raw:
            reader = csv.reader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
            header = next(reader, None) or []
            missing = [c for c in COLUMNS if c not in header]
            if missing:
                raise ValueError(f"{archive_path.name}: Spalten fehlen: {missing}")
            idx = [header.index(c) for c in COLUMNS]
            width = len(header)
            for values in reader:
                rows += 1
                if len(values) != width:
                    raise ValueError(f"{archive_path.name}: Zeile {rows + 1} mit "
                                     f"{len(values)} statt {width} Spalten.")
                lei = values[idx[0]].upper()
                if lei not in wanted:
                    continue
                if lei in found:
                    raise ValueError(f"{archive_path.name}: LEI {lei} doppelt.")
                _, entity, registration, country, updated, renewal, successor = (
                    values[i].strip() for i in idx)
                found[lei] = LeiRecord(
                    lei=lei, entity_status=entity.upper(),
                    registration_status=registration.upper(), country=country or None,
                    last_update=_date(updated), next_renewal=_date(renewal),
                    successor_lei=successor.upper() or None)
    return found, rows
