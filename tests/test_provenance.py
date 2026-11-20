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


def _manifest(tmp_path: Path, content: bytes, sidecar: dict | None = None) -> tuple[Path, Path]:
    """Fiktiver Datenstand wie im Update-System: Originaldatei, Begleitdatei, Manifest."""
    folder = tmp_path / "raw/external/fiktiv"
    page = folder / "objects" / f"{_sha(content)}.json"
    page.parent.mkdir(parents=True)
    page.write_bytes(content)
    if sidecar is not None:
        page.with_name(page.name + ".metadata.json").write_text(json.dumps(sidecar))
    manifest = tmp_path / "raw/external/manifests/fiktiv/20990101T000000_x.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_bytes(json.dumps({"pages": [
        {"path": f"objects/{page.name}", "sha256": _sha(content), "bytes": len(content)}]})
        .encode())
    return manifest, page


def test_manifest_and_pages_verified_with_licence_from_source_config(tmp_path: Path) -> None:
    from transparenz.services.provenance import verified_manifest

    content = b'{"fiktiv": true}'
    manifest, _ = _manifest(tmp_path, content, {
        "sha256": _sha(content), "downloaded_at": "2099-01-02T00:00:00+00:00",
        "license": {"license": "CC0 1.0 (fiktiv)", "terms_url": "https://example.org/agb"}})
    raw, records = verified_manifest(manifest, tmp_path, "fiktiv", _sha(manifest.read_bytes()),
                                     "fiktiv.sqlite: Datenstand 1",
                                     tmp_path / "raw/external/fiktiv")
    assert raw == manifest.read_bytes()
    assert [r.status for r in records] == ["verified", "verified"]
    assert records[0].recorded_in == "fiktiv.sqlite: Datenstand 1"
    assert records[1].licence == "CC0 1.0 (fiktiv)"
    assert records[1].terms_url == "https://example.org/agb"
    assert records[1].retrieved == "2099-01-02T00:00:00+00:00"


def test_page_without_sidecar_is_unrecorded_but_still_checked(tmp_path: Path) -> None:
    from transparenz.services.provenance import verified_manifest

    manifest, page = _manifest(tmp_path, b"{}")
    expected = _sha(manifest.read_bytes())
    folder = tmp_path / "raw/external/fiktiv"
    _, records = verified_manifest(manifest, tmp_path, "fiktiv", expected, "x", folder)
    assert records[1].status == "unrecorded"
    page.write_bytes(b"[]")
    with pytest.raises(ProvenanceError, match="Manifest"):
        verified_manifest(manifest, tmp_path, "fiktiv", expected, "x", folder)


@pytest.mark.parametrize("change", ["manifest", "sidecar", "missing", "outside"])
def test_changed_data_version_stops_processing(tmp_path: Path, change: str) -> None:
    from transparenz.services.provenance import verified_manifest

    content = b'{"fiktiv": 1}'
    manifest, page = _manifest(tmp_path, content, {"sha256": _sha(content)})
    expected = _sha(manifest.read_bytes())
    if change == "manifest":
        manifest.write_bytes(manifest.read_bytes() + b" ")
    elif change == "sidecar":
        page.with_name(page.name + ".metadata.json").write_text(json.dumps({"sha256": "0" * 64}))
    elif change == "missing":
        page.unlink()
    else:
        bundle = {"pages": [{"path": "../../ausserhalb.json", "sha256": _sha(content),
                             "bytes": len(content)}]}
        manifest.write_bytes(json.dumps(bundle).encode())
        expected = _sha(manifest.read_bytes())
    with pytest.raises(ProvenanceError):
        verified_manifest(manifest, tmp_path, "fiktiv", expected, "x",
                          tmp_path / "raw/external/fiktiv")
