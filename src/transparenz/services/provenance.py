"""Herkunft der Eingabedateien: Prüfsumme, Begleitdatei, Lizenzangaben.

Jede Rohdatei liegt mit einer Begleitdatei (``<datei>.metadata.json`` oder
``source.metadata.json``) im Datenordner, die beim Herunterladen die SHA-256-Prüfsumme
festhielt. Vor jeder Verwendung wird die Datei neu gehasht und mit diesem Wert verglichen:

- ``verified``    Prüfsumme stimmt mit der Begleitdatei überein
- ``derived``     aus einem geprüften Archiv entpackt; CRC-32 stimmt mit dem Archiveintrag
- ``generated``   von uns erzeugt (Export, Abfrage-Zwischenspeicher); Prüfsumme festgehalten,
                  ``derived_from`` nennt, woraus bzw. wann
- ``unrecorded``  keine Begleitdatei mit Prüfsumme – ehrlich als «nicht erfasst» ausgewiesen

Für das Update-System (D-061) gilt derselbe Weg: Das gespeicherte Manifest eines Datenstands
muss die Prüfsumme aus ``dataset_versions.content_hash`` tragen, jede darin genannte
Originaldatei die Prüfsumme aus Manifest und eigener Begleitdatei (``verified_manifest``).

Weicht eine Prüfsumme ab, bricht die Verarbeitung ab (``ProvenanceError``): Veränderte
Rohdaten dürfen nie still in ein Ergebnis einfliessen. Rein lokal, keine Uhr, kein Netz.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SIDECAR_NAMES = ("source.metadata.json",)
_LICENCE_KEYS = ("license", "licence", "license_name")
_TERMS_KEYS = ("terms_url", "licence_url", "license_url")
_DATE_KEYS = ("retrieved_at_utc", "retrieved_on", "retrieved_at", "downloaded_at",
              "publish_date", "terms_checked_on")


class ProvenanceError(RuntimeError):
    """Eine Rohdatei stimmt nicht mehr mit der beim Download festgehaltenen Prüfsumme überein."""


@dataclass(frozen=True)
class FileProvenance:
    source_key: str | None
    path: str  # relativ zum Datenordner, mit «/»
    bytes: int
    sha256: str
    status: str  # verified | derived | unrecorded
    recorded_in: str | None  # Begleitdatei, relativ zum Datenordner
    derived_from: str | None  # Archiv, aus dem die Datei entpackt wurde
    licence: str | None
    terms_url: str | None
    retrieved: str | None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def sha256_of(path: Path, chunk: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(chunk):
            digest.update(block)
    return digest.hexdigest()


def _crc32_of(path: Path, chunk: int = 1 << 20) -> int:
    value = 0
    with path.open("rb") as handle:
        while block := handle.read(chunk):
            value = zlib.crc32(block, value)
    return value & 0xFFFFFFFF


def _first(meta: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = meta.get(key)
        if value and not isinstance(value, dict):
            return str(value)
    # Begleitdateien des Update-Systems tragen die ganze Quellenkonfiguration unter
    # «license»; dort stehen Bezeichnung und Bedingungen als eigene Felder.
    nested = meta.get("license")
    return _first(nested, keys) if isinstance(nested, dict) else None


def _relative(path: Path, data_dir: Path) -> str:
    try:
        return path.resolve().relative_to(data_dir.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _sidecar(path: Path) -> tuple[Path, dict[str, Any], str | None] | None:
    """Begleitdatei und die dort für diese Datei festgehaltene Prüfsumme (falls vorhanden)."""
    own = path.with_name(path.name + ".metadata.json")
    if own.is_file():
        meta = json.loads(own.read_bytes())
        return own, meta, meta.get("sha256")
    for name in SIDECAR_NAMES:
        shared = path.parent / name
        if not shared.is_file():
            continue
        meta = json.loads(shared.read_bytes())
        files = meta.get("files") or {}
        if path.name in files:
            return shared, meta, files[path.name].get("sha256")
        if meta.get("sha256") and not files:
            # Eine einzelne Prüfsumme im Ordner gilt für die Datei mit der festgehaltenen
            # Grösse; andere Dateien im selben Ordner gelten als nicht erfasst.
            if meta.get("size_bytes") in (None, path.stat().st_size):
                return shared, meta, meta["sha256"]
            return shared, meta, None
        return shared, meta, None
    return None


def _archive_parent(path: Path) -> tuple[Path, Path, dict[str, Any], zipfile.ZipInfo] | None:
    """Für entpackte Dateien (``…/extracted/<name>``): das geprüfte Archiv mit diesem Eintrag."""
    if path.parent.name != "extracted":
        return None
    folder = path.parent.parent
    for archive in sorted(folder.glob("*.zip")):
        found = _sidecar(archive)
        if not found:
            continue
        with zipfile.ZipFile(archive) as zf:
            for info in zf.infolist():
                if Path(info.filename).name == path.name and not info.is_dir():
                    return archive, found[0], found[1], info
    return None


def describe_file(path: Path, data_dir: Path, source_key: str | None = None) -> FileProvenance:
    """Prüft eine Eingabedatei gegen ihre Begleitdatei und beschreibt ihre Herkunft."""
    path = Path(path)
    digest = sha256_of(path)
    size = path.stat().st_size
    found = _sidecar(path)
    if found:
        sidecar, meta, recorded = found
        if recorded and recorded != digest:
            raise ProvenanceError(
                f"{path}: SHA-256 {digest} weicht von der Begleitdatei {sidecar.name} ab "
                f"({recorded}). Rohdaten verändert oder ersetzt – Verarbeitung abgebrochen.")
        return FileProvenance(
            source_key=source_key or meta.get("source_key"), path=_relative(path, data_dir),
            bytes=size, sha256=digest, status="verified" if recorded else "unrecorded",
            recorded_in=_relative(sidecar, data_dir), derived_from=None,
            licence=_first(meta, _LICENCE_KEYS), terms_url=_first(meta, _TERMS_KEYS),
            retrieved=_first(meta, _DATE_KEYS))
    parent = _archive_parent(path)
    if parent:
        archive, sidecar, meta, info = parent
        if _crc32_of(path) != info.CRC or info.file_size != size:
            raise ProvenanceError(
                f"{path}: stimmt nicht mit dem Eintrag in {archive.name} überein (CRC-32/Grösse). "
                "Entpackte Datei verändert – Verarbeitung abgebrochen.")
        archive_record = describe_file(archive, data_dir, source_key)
        return FileProvenance(
            source_key=source_key or meta.get("source_key"), path=_relative(path, data_dir),
            bytes=size, sha256=digest,
            status="derived" if archive_record.status == "verified" else "unrecorded",
            recorded_in=_relative(sidecar, data_dir), derived_from=archive_record.path,
            licence=_first(meta, _LICENCE_KEYS), terms_url=_first(meta, _TERMS_KEYS),
            retrieved=_first(meta, _DATE_KEYS))
    return FileProvenance(
        source_key=source_key, path=_relative(path, data_dir), bytes=size, sha256=digest,
        status="unrecorded", recorded_in=None, derived_from=None, licence=None,
        terms_url=None, retrieved=None)


def describe_generated(path: Path, data_dir: Path, source_key: str,
                       derived_from: str) -> FileProvenance:
    """Von uns erzeugte Datei (Export, gespeicherte Abfrage): Prüfsumme und Ursprung festhalten.

    ``derived_from`` nennt die Erzeugung, z. B. die Exportgeneration mit ihrem Qualitätsbericht
    oder Quelle und Abrufzeit einer gespeicherten Abfrage. Lizenzangaben stehen bei der Quelle.
    """
    path = Path(path)
    return FileProvenance(
        source_key=source_key, path=_relative(path, data_dir), bytes=path.stat().st_size,
        sha256=sha256_of(path), status="generated", recorded_in=None,
        derived_from=derived_from, licence=None, terms_url=None, retrieved=None)


def verified_manifest(path: Path, data_dir: Path, source_key: str, expected_sha256: str,
                      recorded_in: str, folder: Path) -> tuple[bytes, list[FileProvenance]]:
    """Manifest eines aktiven Datenstands und alle darin genannten Originaldateien prüfen.

    ``expected_sha256`` ist die beim Aktivieren gespeicherte Prüfsumme des Manifests
    (``dataset_versions.content_hash``), ``recorded_in`` nennt diese Stelle. Jede Originaldatei
    muss unter ``folder`` liegen und mit Manifest und eigener Begleitdatei übereinstimmen.
    Rückgabe: Manifestinhalt (genau die geprüften Bytes) und Herkunft, Manifest zuerst.
    """
    path = Path(path)
    content = path.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    if digest != expected_sha256:
        raise ProvenanceError(
            f"{path}: SHA-256 {digest} weicht vom aktiven Datenstand ab ({expected_sha256}). "
            "Manifest verändert oder ersetzt – Verarbeitung abgebrochen.")
    records = [FileProvenance(
        source_key=source_key, path=_relative(path, data_dir), bytes=len(content),
        sha256=digest, status="verified", recorded_in=recorded_in, derived_from=None,
        licence=None, terms_url=None, retrieved=None)]
    root = Path(folder).resolve()
    for entry in json.loads(content).get("pages", []):
        page = (root / entry["path"]).resolve()
        if not page.is_relative_to(root):
            raise ProvenanceError(f"{page}: Originaldatei ausserhalb des Quellenordners.")
        if not page.is_file():
            raise ProvenanceError(f"{page}: im Manifest genannte Originaldatei fehlt.")
        record = describe_file(page, data_dir, source_key)
        if record.sha256 != entry["sha256"] or entry.get("bytes") not in (None, record.bytes):
            raise ProvenanceError(
                f"{page}: stimmt nicht mit dem Manifest {path.name} überein (SHA-256/Grösse). "
                "Rohdaten verändert – Verarbeitung abgebrochen.")
        records.append(record)
    return content, records


def verify_recorded(path: Path, data_dir: Path, source_key: str, expected_sha256: str,
                    recorded_in: Path, meta: dict[str, Any]) -> tuple[bytes, FileProvenance]:
    """Eine Datei gegen eine Prüfsumme in einem Zeiger (z. B. ``current.json``) prüfen."""
    path = Path(path)
    content = path.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    if digest != str(expected_sha256).lower():
        raise ProvenanceError(
            f"{path}: SHA-256 {digest} weicht von {Path(recorded_in).name} ab "
            f"({expected_sha256}). Rohdaten verändert – Verarbeitung abgebrochen.")
    return content, FileProvenance(
        source_key=source_key, path=_relative(path, data_dir), bytes=len(content),
        sha256=digest, status="verified", recorded_in=_relative(Path(recorded_in), data_dir),
        derived_from=None, licence=_first(meta, _LICENCE_KEYS),
        terms_url=_first(meta, _TERMS_KEYS), retrieved=_first(meta, _DATE_KEYS))
