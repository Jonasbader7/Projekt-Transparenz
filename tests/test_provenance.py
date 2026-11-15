"""Herkunft der Eingabedateien: Prüfsumme gegen Begleitdatei, entpackte Dateien, Abbruch."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from transparenz.services.provenance import ProvenanceError, describe_file


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_own_sidecar_verified(tmp_path: Path) -> None:
    raw = tmp_path / "raw/external/fiktiv/2099/datei.zip"
    raw.parent.mkdir(parents=True)
    raw.write_bytes(b"fiktive Rohdaten")
    raw.with_name("datei.zip.metadata.json").write_text(json.dumps({
        "source_key": "fiktiv", "sha256": _sha(b"fiktive Rohdaten"),
        "terms_url": "https://example.org/bedingungen", "retrieved_at_utc": "2099-01-02"}))
    record = describe_file(raw, tmp_path)
    assert record.status == "verified"
    assert record.path == "raw/external/fiktiv/2099/datei.zip"
    assert record.source_key == "fiktiv" and record.retrieved == "2099-01-02"


def test_changed_file_stops_processing(tmp_path: Path) -> None:
    raw = tmp_path / "datei.csv"
    raw.write_bytes(b"neu")
    (tmp_path / "source.metadata.json").write_text(json.dumps(
        {"files": {"datei.csv": {"sha256": _sha(b"alt")}}}))
    with pytest.raises(ProvenanceError, match="weicht"):
        describe_file(raw, tmp_path)


def test_extracted_member_checked_against_archive(tmp_path: Path) -> None:
    folder = tmp_path / "raw/external/fiktiv/2099"
    (folder / "extracted").mkdir(parents=True)
    archive = folder / "paket.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("innen/tabelle.xlsx", b"inhalt")
    (folder / "source.metadata.json").write_text(json.dumps(
        {"source_key": "fiktiv", "licence": "CC BY 4.0",
         "files": {"paket.zip": {"sha256": _sha(archive.read_bytes())}}}))
    member = folder / "extracted/tabelle.xlsx"
    member.write_bytes(b"inhalt")
    record = describe_file(member, tmp_path)
    assert record.status == "derived"
    assert record.derived_from == "raw/external/fiktiv/2099/paket.zip"
    assert record.licence == "CC BY 4.0"
    member.write_bytes(b"veraendert")
    with pytest.raises(ProvenanceError, match="CRC"):
        describe_file(member, tmp_path)


def test_without_sidecar_is_unrecorded_not_invented(tmp_path: Path) -> None:
    raw = tmp_path / "lose.json"
    raw.write_text("{}")
    record = describe_file(raw, tmp_path, source_key="wikidata_isin")
    assert record.status == "unrecorded"
    assert record.recorded_in is None and record.licence is None


def test_generated_file_keeps_origin(tmp_path: Path) -> None:
    from transparenz.services.provenance import describe_generated

    out = tmp_path / "processed/export.json"
    out.parent.mkdir(parents=True)
    out.write_text("[]")
    record = describe_generated(out, tmp_path, "swiss_export", "Generation 2099")
    assert record.status == "generated" and record.sha256 == _sha(b"[]")
    assert record.path == "processed/export.json"
