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
import json
import re
import zipfile
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

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


RR_SOURCE_KEY = "gleif_rr_golden_copy"
RR_FOLDER = "raw/external/gleif_rr_golden_copy"
RR_ARCHIVE_NAME = "gleif-goldencopy-rr.csv.zip"


def latest_snapshot(data_dir: Path, folder_name: str = FOLDER, archive_name: str = ARCHIVE_NAME,
                    source_key: str = SOURCE_KEY) -> FileProvenance | None:
    """Jüngster lokal geladener Stand (Ordner JJJJ-MM-TT), gegen die Begleitdatei geprüft.

    Standard: Liste Level 1; mit ``RR_FOLDER``/``RR_ARCHIVE_NAME`` die Beziehungsdatei.
    """
    folder = data_dir / folder_name
    if not folder.is_dir():
        return None
    dated = sorted((p for p in folder.iterdir()
                    if p.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.name)
                    and (p / archive_name).is_file()), reverse=True)
    if not dated:
        return None
    record = describe_file(dated[0] / archive_name, data_dir, source_key)
    if record.status != "verified":
        raise ProvenanceError(f"{record.path}: keine Begleitdatei mit Prüfsumme.")
    return record


def _date(value: str) -> str | None:
    return value[:10] if re.match(r"\d{4}-\d{2}-\d{2}", value or "") else None


def _scan(archive_path: Path, wanted: set[str], columns: tuple[str, ...]
          ) -> Iterator[tuple[str, list[str]]]:
    """Liefert (LEI, Werte der Spalten) für die gesuchten LEI.

    Prüft Spalten und Zeilenbreite; doppelte LEI in der Datei = Fehler. Rückgabewert des
    Generators (``StopIteration.value``) ist die Zahl der gelesenen Zeilen.
    """
    seen: set[str] = set()
    rows = 0
    with zipfile.ZipFile(archive_path) as archive:
        members = [n for n in archive.namelist() if n.lower().endswith(".csv")]
        if len(members) != 1:
            raise ValueError(f"{archive_path.name}: genau eine CSV erwartet, {len(members)}.")
        with archive.open(members[0]) as raw:
            reader = csv.reader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
            header = next(reader, None) or []
            missing = [c for c in ("LEI", *columns) if c not in header]
            if missing:
                raise ValueError(f"{archive_path.name}: Spalten fehlen: {missing}")
            lei_index = header.index("LEI")
            idx = [header.index(c) for c in columns]
            width = len(header)
            for values in reader:
                rows += 1
                if len(values) != width:
                    raise ValueError(f"{archive_path.name}: Zeile {rows + 1} mit "
                                     f"{len(values)} statt {width} Spalten.")
                lei = values[lei_index].upper()
                if lei not in wanted:
                    continue
                if lei in seen:
                    raise ValueError(f"{archive_path.name}: LEI {lei} doppelt.")
                seen.add(lei)
                yield lei, [values[i].strip() for i in idx]
    return rows


def _collect(scan: Iterator[tuple[str, list[str]]]) -> tuple[list[tuple[str, list[str]]], int]:
    items = []
    while True:
        try:
            items.append(next(scan))
        except StopIteration as done:
            return items, done.value


def load_lei_records(archive_path: Path, wanted: Iterable[str]) -> tuple[dict[str, LeiRecord],
                                                                         int]:
    """(gesuchte LEI → Datensatz, gelesene Zeilen). Doppelte LEI in der Datei = Fehler."""
    items, rows = _collect(_scan(archive_path, {w.upper() for w in wanted}, COLUMNS[1:]))
    found: dict[str, LeiRecord] = {}
    for lei, (entity, registration, country, updated, renewal, successor) in items:
        found[lei] = LeiRecord(
            lei=lei, entity_status=entity.upper(), registration_status=registration.upper(),
            country=country or None, last_update=_date(updated), next_renewal=_date(renewal),
            successor_lei=successor.upper() or None)
    return found, rows


# Namen laut Common Data File 3.1: Rechtsname, bis zu fünf weitere und fünf transliterierte
# Namen, je mit Typ (z. B. PREVIOUS_LEGAL_NAME, TRADING_OR_OPERATING_NAME).
_OTHER = "Entity.OtherEntityNames.OtherEntityName"
_TRANSLIT = "Entity.TransliteratedOtherEntityNames.TransliteratedOtherEntityName"
NAME_COLUMNS = ("Entity.LegalName", "Entity.EntityStatus", "Registration.RegistrationStatus",
                "Entity.LegalAddress.Country",
                *(f"{base}.{i}{suffix}" for base in (_OTHER, _TRANSLIT) for i in range(1, 6)
                  for suffix in ("", ".type")))


def load_lei_names(archive_path: Path, wanted: Iterable[str]) -> tuple[dict[str, dict], int]:
    """(gesuchte LEI → Namen und Status, gelesene Zeilen), in der Form der GLEIF-Abfrage.

    Gleiche Felder wie ``gleif_lookup.fetch_gleif`` (``legal_name``, ``other_names`` mit
    ``name``/``type``, ``entity_status``, ``registration_status``, ``country``), dazu
    ``source = "gleif_level1"``. Fehlt ein gesuchter LEI in der Datei, fehlt er im Ergebnis.
    """
    items, rows = _collect(_scan(archive_path, {w.upper() for w in wanted}, NAME_COLUMNS))
    found: dict[str, dict] = {}
    for lei, values in items:
        legal, entity, registration, country, *others = values
        found[lei] = {
            "legal_name": legal or None,
            "other_names": [{"name": others[i], "type": others[i + 1] or None}
                            for i in range(0, len(others), 2) if others[i]],
            "entity_status": entity.upper() or None,
            "registration_status": registration.upper() or None,
            "country": country or None, "source": SOURCE_KEY}
    return found, rows


NAMES_CACHE_SCHEMA = 1


def cached_lei_names(archive_path: Path, archive_sha256: str, wanted: Iterable[str],
                     cache_path: Path) -> tuple[dict[str, dict], dict[str, Any]]:
    """Namen aus der Liste Level 1, zwischengespeichert je Archiv-Prüfsumme und LEI-Menge.

    Der Zwischenspeicher gilt nur, wenn Prüfsumme und Schema gleich sind und er alle gesuchten
    LEI abfragte; sonst wird die Liste neu gelesen (rund eine bis zwei Minuten) und der
    Speicher ersetzt. Zurück: (LEI → Eintrag für die gesuchten LEI, Angaben zum Stand).
    """
    wanted = sorted({w.upper() for w in wanted})
    cache: dict[str, Any] = {}
    if cache_path.exists():
        cache = json.loads(cache_path.read_text("utf-8"))
    valid = (cache.get("schema") == NAMES_CACHE_SCHEMA
             and cache.get("archive_sha256") == archive_sha256
             and set(wanted) <= set(cache.get("requested") or []))
    if not valid:
        names, rows = load_lei_names(archive_path, wanted)
        cache = {"schema": NAMES_CACHE_SCHEMA, "archive": archive_path.name,
                 "archive_sha256": archive_sha256, "rows_read": rows,
                 "requested": wanted, "names": names}
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cache, ensure_ascii=False), "utf-8")
    names = {lei: cache["names"][lei] for lei in wanted if lei in cache["names"]}
    return names, {"archive": cache["archive"], "archive_sha256": archive_sha256,
                   "rows_read": cache["rows_read"], "requested": len(wanted),
                   "found": len(names), "rebuilt": not valid}
