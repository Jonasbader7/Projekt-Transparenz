"""SwissPRTR emissions workbook normalisation: synthetic fixtures only.

Linking to a company must use only the row's own validated facility UID, never
the facility/company name; diffuse (non-point) sources have no facility and must
stay explicitly unlinked.
"""
from __future__ import annotations

import hashlib
import sqlite3
import zipfile
from io import BytesIO
from pathlib import Path
from string import ascii_uppercase

from test_swiss_foundation import config, gleif_records, original
from transparenz.entities.identifiers import make_lei
from transparenz.ingestion.external import FORMAT, encoded, parse_external
from transparenz.services import swiss_foundation as swiss

# Compact header set matching the EMISSION_HEADERS the parser requires; any column
# letters work, the parser matches by header text, not position.
EMISSION_COLUMNS = ("Facility ID", "UID of facility", "UID holder", "Year", "Source type",
                    "Pollutant_name", "CAS", "Pollutant_group", "Medium", "Value", "Unit",
                    "Diffuse_sources")


def build_emissions_xlsx(rows: list[dict], columns: tuple[str, ...] = EMISSION_COLUMNS) -> bytes:
    """Minimal OOXML workbook with one 'Daten…' sheet, built without any Excel library.

    Rows are dicts keyed by header name (not position), so a test can drop a column
    by leaving it out of `columns` without having to realign every row by hand.
    """
    strings: list[str] = []

    def sidx(text: str) -> int:
        if text not in strings:
            strings.append(text)
        return strings.index(text)

    def cell_xml(col: str, row_num: int, value) -> str:
        ref = f"{col}{row_num}"
        if value is None:
            return ""
        if isinstance(value, str):
            return f'<c r="{ref}" t="s"><v>{sidx(value)}</v></c>'
        return f'<c r="{ref}"><v>{value}</v></c>'

    letters = list(ascii_uppercase[:len(columns)])
    all_rows = [dict(zip(columns, columns, strict=True)), *rows]
    sheet_rows = []
    for i, row in enumerate(all_rows, start=1):
        cells = "".join(cell_xml(col, i, row.get(name)) for col, name in zip(letters, columns,
                                                                              strict=True))
        sheet_rows.append(f'<row r="{i}">{cells}</row>')
    sheet_xml = ('<?xml version="1.0" encoding="UTF-8"?>'
                 '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                 f'<sheetData>{"".join(sheet_rows)}</sheetData></worksheet>')
    shared_xml = ('<?xml version="1.0" encoding="UTF-8"?>'
                  '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                  f'count="{len(strings)}" uniqueCount="{len(strings)}">'
                  + "".join(f"<si><t>{s}</t></si>" for s in strings) + "</sst>")
    workbook_xml = ('<?xml version="1.0" encoding="UTF-8"?>'
                    '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                    '<sheets><sheet name="Daten 2007-2024 v02 (fiktiv)" sheetId="1" r:id="rId1"/>'
                    '</sheets></workbook>')
    rels_xml = ('<?xml version="1.0" encoding="UTF-8"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
                'relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
                'officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
                '</Relationships>')
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", rels_xml)
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)
        archive.writestr("xl/sharedStrings.xml", shared_xml)
    return buffer.getvalue()


def build_facility_gpkg_zip(facilities: list[tuple[int, str, str, int]]) -> bytes:
    """Minimal GeoPackage (plain SQLite) with one facility register table."""
    import tempfile
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "source.gpkg"
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE gpkg_contents (table_name TEXT)")
        conn.execute("INSERT INTO gpkg_contents VALUES ('swissprtr')")
        conn.execute("CREATE TABLE swissprtr (fid INTEGER, geom BLOB, Betriebs_I INTEGER, "
                     "Betrieb TEXT, Ort TEXT, Jahr INTEGER)")
        for fid, (betriebs_i, betrieb, ort, jahr) in enumerate(facilities, start=1):
            conn.execute("INSERT INTO swissprtr VALUES (?, NULL, ?, ?, ?, ?)",
                        (fid, betriebs_i, betrieb, ort, jahr))
        conn.commit()
        conn.close()
        content = path.read_bytes()
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("swissPRTR.gpkg", content)
    return buffer.getvalue()


def swissprtr_manifest(tmp_path, cfg, *, gpkg: bytes, xlsx: bytes | None,
                       data_as_of="2026-11-08") -> bytes:
    folder = tmp_path / "data/raw/external" / cfg.key / "objects"
    folder.mkdir(parents=True, exist_ok=True)
    entries = [(gpkg, "zip", "geopackage")]
    if xlsx is not None:
        entries.append((xlsx, "xlsx", "original_emissions_workbook"))
    pages = []
    for content, suffix, role in entries:
        digest = hashlib.sha256(content).hexdigest()
        (folder / f"{digest}.{suffix}").write_bytes(content)
        pages.append({"path": f"objects/{digest}.{suffix}", "sha256": digest,
                      "bytes": len(content), "url": "https://example.org/fiktiv",
                      "format": suffix, "role": role})
    return encoded({"format": FORMAT, "source_key": cfg.key, "mode": cfg.external_mode,
                    "data_as_of": data_as_of, "coverage": {"complete_swiss_market": False},
                    "pages": pages})


def emission_row(facility_id="4", uid="CHE105904234", year="2024", source_type="Punktquelle",
                 pollutant="Kohlendioxid (CO2) (fiktiv)", cas=None, group="Treibhausgase",
                 medium="Luft", value=1000, unit="kg/a", diffuse=None, uid_holder=None):
    return {"Facility ID": facility_id, "UID of facility": uid, "UID holder": uid_holder,
            "Year": year, "Source type": source_type, "Pollutant_name": pollutant, "CAS": cas,
            "Pollutant_group": group, "Medium": medium, "Value": value, "Unit": unit,
            "Diffuse_sources": diffuse}


def test_point_and_diffuse_emissions_are_normalised(tmp_path):
    cfg = config("swissprtr")
    gpkg = build_facility_gpkg_zip([(4, "Beispiel AG (fiktiv)", "Beispielort", 2024)])
    xlsx = build_emissions_xlsx([
        emission_row(),
        emission_row(facility_id=None, uid=None, source_type="Nicht-Punktquelle",
                     pollutant="Methan (CH4) (fiktiv)", group="Treibhausgase",
                     diffuse="Diffuse Quellen Luft: Verkehr (fiktiv)", value=500),
    ])
    parsed = parse_external(swissprtr_manifest(tmp_path, cfg, gpkg=gpkg, xlsx=xlsx), cfg, tmp_path)
    assert parsed.is_valid, parsed.errors
    emissions = parsed.extra["emissions"]
    assert len(emissions) == 2
    point = next(e for e in emissions if e["source_type"] == "Punktquelle")
    assert point["facility_id"] == "4"
    assert point["uid_facility"] == "CHE105904234"
    assert point["year"] == 2024
    assert point["pollutant_name"] == "Kohlendioxid (CO2) (fiktiv)"
    assert point["medium"] == "Luft"
    assert point["value"] == 1000.0
    assert point["unit"] == "kg/a"
    assert point["mapping_status"] == "unresolved"  # company linking happens in export
    assert point["evidence_category"] == "emission_register_not_violation"
    diffuse = next(e for e in emissions if e["source_type"] == "Nicht-Punktquelle")
    assert diffuse["facility_id"] is None
    assert diffuse["mapping_status"] == "diffuse_source_no_facility"
    assert diffuse["diffuse_source_description"] == "Diffuse Quellen Luft: Verkehr (fiktiv)"


def test_missing_required_column_invalidates_dataset(tmp_path):
    cfg = config("swissprtr")
    gpkg = build_facility_gpkg_zip([(4, "Beispiel AG (fiktiv)", "Beispielort", 2024)])
    incomplete_columns = tuple(c for c in EMISSION_COLUMNS if c != "Medium")
    xlsx = build_emissions_xlsx([emission_row()], columns=incomplete_columns)
    parsed = parse_external(swissprtr_manifest(tmp_path, cfg, gpkg=gpkg, xlsx=xlsx), cfg, tmp_path)
    assert not parsed.is_valid
    assert any("Medium" in str(error) for error in parsed.errors)


def test_invalid_facility_uid_is_kept_unlinked_with_warning(tmp_path):
    cfg = config("swissprtr")
    gpkg = build_facility_gpkg_zip([(4, "Beispiel AG (fiktiv)", "Beispielort", 2024)])
    xlsx = build_emissions_xlsx([emission_row(uid="CHE105904235")])  # bad checksum
    parsed = parse_external(swissprtr_manifest(tmp_path, cfg, gpkg=gpkg, xlsx=xlsx), cfg, tmp_path)
    assert parsed.is_valid, parsed.errors
    emission = parsed.extra["emissions"][0]
    assert emission["uid_facility"] is None
    assert emission["uid_facility_raw"] == "CHE105904235"
    assert any("ungültige" in str(w) for w in parsed.warnings)


def test_export_links_emission_to_company_only_by_validated_uid(tmp_path, monkeypatch):
    from dataclasses import replace

    from transparenz.config.settings import get_settings
    from transparenz.ingestion.adapters import build_adapter
    from transparenz.ingestion.fetchers import FetchResult

    ctx = swiss.create_swiss_context(replace(get_settings(), project_root=tmp_path))
    try:
        lei = make_lei("FIKT00COMPANY".ljust(17, "0") + "1")
        gleif_cfg = ctx.catalog.source("gleif_ch")
        body = gleif_records()
        body["data"][0]["attributes"]["lei"] = lei
        body["data"][0]["id"] = lei
        body["data"][0]["attributes"]["entity"]["registeredAs"] = "CHE-105.904.234"
        body["data"] = [body["data"][0]]  # drop the synthetic fund record
        gleif_adapter = build_adapter(gleif_cfg, ctx.catalog, tmp_path, "test")

        class GleifFetcher:
            content = original(tmp_path, gleif_cfg, body, 1)

            def fetch(self, **kwargs):
                return FetchResult(origin="https://example.org/fiktiv", content=self.content)

        gleif_adapter.fetcher = GleifFetcher()
        ctx.updates._adapters[gleif_cfg.key] = gleif_adapter
        ctx.updates.run_source(gleif_cfg.key, force=True)

        swissprtr_cfg = ctx.catalog.source("swissprtr")
        gpkg = build_facility_gpkg_zip([(4, "Beispiel AG (fiktiv)", "Beispielort", 2024)])
        xlsx = build_emissions_xlsx([
            emission_row(uid="CHE105904234"),  # matches the company above
            emission_row(facility_id="99", uid="CHE999999996"),  # no matching company
            emission_row(facility_id=None, uid=None, source_type="Nicht-Punktquelle",
                        diffuse="Diffuse Quellen Luft: Verkehr (fiktiv)"),
        ])
        manifest = swissprtr_manifest(tmp_path, swissprtr_cfg, gpkg=gpkg, xlsx=xlsx)
        swissprtr_adapter = build_adapter(swissprtr_cfg, ctx.catalog, tmp_path, "test")

        class SwissprtrFetcher:
            def fetch(self, **kwargs):
                return FetchResult(origin="https://example.org/fiktiv", content=manifest)

        swissprtr_adapter.fetcher = SwissprtrFetcher()
        ctx.updates._adapters[swissprtr_cfg.key] = swissprtr_adapter
        ctx.updates.run_source(swissprtr_cfg.key, force=True)

        report = swiss.export_foundation(ctx)
        assert report["counts"]["emissions"] == 3
        assert report["counts"]["emissions_company_matched"] == 1
        assert report["counts"]["emissions_diffuse_source"] == 1
        output = ctx.settings.processed_dir / "swiss"
        import json
        pointer = json.loads((output / "current.json").read_bytes())
        generation = output / pointer["generation"]
        emissions = json.loads((generation / "emissions.json").read_bytes())
        matched = next(e for e in emissions if e["uid_facility"] == "CHE105904234")
        unresolved = next(e for e in emissions if e["uid_facility"] == "CHE999999996")
        diffuse = next(e for e in emissions if e["source_type"] == "Nicht-Punktquelle")
        assert matched["company_key"] == f"lei:{lei}"
        assert matched["mapping_status"] == "exact_uid_match"
        assert unresolved["company_key"] is None
        assert unresolved["mapping_status"] == "unresolved"
        assert diffuse["company_key"] is None
        assert diffuse["mapping_status"] == "diffuse_source_no_facility"
    finally:
        ctx.engine.dispose()
