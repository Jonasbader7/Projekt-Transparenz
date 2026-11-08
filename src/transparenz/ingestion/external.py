"""Official Swiss raw sources using the existing DataUpdateManager contract.

Original HTTP bodies are content-addressed and never rewritten. The manager activates
only a fully validated manifest. Supplementary attributes remain in these manifests
and local exports; the existing screening schema is deliberately unchanged.
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import re
import sqlite3
import tempfile
import time
import zipfile
from collections import defaultdict
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import httpx
from pydantic import ValidationError

from transparenz.config.catalog import Catalog, SourceConfig
from transparenz.entities.enums import DatasetKind
from transparenz.entities.identifiers import is_valid_isin, is_valid_lei
from transparenz.entities.models import CompanyRecord
from transparenz.ingestion.fetchers import FetchError, FetchResult
from transparenz.ingestion.gleif import REGISTRATION_EXCLUDED, GleifLeiRecord
from transparenz.ingestion.parsing import ParsedDataset, check_entities

log = logging.getLogger(__name__)
FORMAT = "transparenz-external/1"
ZEFIX_PREFIX = '''PREFIX schema: <http://schema.org/>
PREFIX admin: <https://schema.ld.admin.ch/>
'''


def encoded(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(content)
    temporary.replace(path)


def atomic_json(path: Path, value: Any) -> None:
    """Stream large exports, avoiding a second full JSON copy in memory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, mode="w", encoding="utf-8",
                                     delete=False) as handle:
        temporary = Path(handle.name)
        json.dump(value, handle, ensure_ascii=False, sort_keys=True)
    temporary.replace(path)


def normalize_uid(value: str | None) -> str | None:
    clean = re.sub(r"[^A-Z0-9]", "", (value or "").upper())
    if not re.fullmatch(r"CHE\d{9}", clean):
        return None
    digits = [int(c) for c in clean[3:]]
    check = (11 - sum(a * b for a, b in zip(digits[:8], (5, 4, 3, 2, 7, 6, 5, 4),
                                          strict=True)) % 11) % 11
    return clean if check < 10 and check == digits[8] else None


@dataclass
class ExternalDataset(ParsedDataset):
    extra: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    coverage: dict[str, Any] = field(default_factory=dict)

    @property
    def record_count(self) -> int:
        return super().record_count + sum(len(self.extra.get(k, [])) for k in
                                          ("funds", "facilities", "emissions"))


class RawClient:
    """Bounded retries, Retry-After, conditional requests and a 24h disk cache."""

    def __init__(self, cfg: SourceConfig, root: Path, user_agent: str,
                 client: httpx.Client | None = None, sleep: Callable = time.sleep):
        self.cfg = cfg
        self.folder = root / "data/raw/external" / cfg.key
        self.client = client or httpx.Client(timeout=90, follow_redirects=False,
                                             headers={"User-Agent": user_agent})
        self.owns_client = client is None
        self.sleep = sleep
        self.last_request = 0.0

    def get(self, url: str, *, params: dict | None = None, suffix: str = "json") -> dict:
        request = self.client.build_request("GET", url, params=params)
        # All navigational links are restricted to this source's official hosts.
        hosts = {"gleif_ch": {"api.gleif.org"}, "zefix": {"lindas.admin.ch"},
                 "wikidata": {"query.wikidata.org"},
                 "swissprtr": {"data.geo.admin.ch", "www.bafu.admin.ch"}}
        hosts.update({mode: {"www.sec.gov"} for mode in
                      ("sec_exchange", "sec_fund_classes", "sec_ncen")})
        if request.url.host not in hosts[self.cfg.external_mode]:
            raise FetchError("Unerwarteter Host in Quellenlink", transient=False)
        cache_key = hashlib.sha256(str(request.url).encode()).hexdigest()
        cache_path = self.folder / "cache" / f"{cache_key}.json"
        cached = json.loads(cache_path.read_bytes()) if cache_path.exists() else None
        if cached:
            downloaded = datetime.fromisoformat(cached["checked_at"])
            object_path = self.folder / cached["path"]
            if (object_path.exists()
                    and (datetime.now(UTC) - downloaded).total_seconds() < 86400
                    and hashlib.sha256(object_path.read_bytes()).hexdigest() == cached["sha256"]):
                return cached
            if cached.get("etag"):
                request.headers["If-None-Match"] = cached["etag"]
            if cached.get("last_modified"):
                request.headers["If-Modified-Since"] = cached["last_modified"]
        request.headers["Accept"] = "application/sparql-results+json, application/json, */*"
        response = None
        for attempt in range(3):
            self.sleep(max(0.0, 1.1 - (time.monotonic() - self.last_request)))
            self.last_request = time.monotonic()
            try:
                response = self.client.send(request)
            except httpx.TransportError as exc:
                if attempt == 2:
                    raise FetchError(str(exc), transient=False) from exc
                self.sleep(3 * 2 ** attempt)
                continue
            if response.status_code == 304 and cached:
                cached["checked_at"] = datetime.now(UTC).isoformat()
                atomic_write(cache_path, encoded(cached))
                return cached
            if response.status_code == 429 or response.status_code >= 500:
                wait = response.headers.get("Retry-After", "")
                if wait.isdigit() and int(wait) > 60:
                    raise FetchError(f"HTTP {response.status_code}; Retry-After {wait}s; "
                                     "später erneut ausführen", transient=False)
                if attempt < 2:
                    self.sleep(max(float(wait) if wait.isdigit() else 0, 3 * 2 ** attempt))
                    continue
            if response.is_error or response.is_redirect:
                raise FetchError(f"HTTP {response.status_code} bei {request.url}", transient=False)
            break
        if response is None:
            raise FetchError("Keine HTTP-Antwort", transient=False)
        content = response.content
        digest = hashlib.sha256(content).hexdigest()
        path = Path("objects") / f"{digest}.{suffix}"
        absolute = self.folder / path
        if not absolute.exists():
            atomic_write(absolute, content)
        now = datetime.now(UTC).isoformat()
        entry = {"path": path.as_posix(), "sha256": digest, "bytes": len(content),
                 "url": str(request.url), "downloaded_at": now, "checked_at": now,
                 "format": suffix, "source_key": self.cfg.key,
                 "data_as_of": None, "data_as_of_note": "Siehe Datensatzmanifest",
                 "license": self.cfg.model_dump(mode="json"),
                 "etag": response.headers.get("ETag"),
                 "last_modified": response.headers.get("Last-Modified"),
                 "quality_notes": ["Unveränderte Originalantwort; keine Vollständigkeitszusage."]}
        metadata = absolute.with_suffix(absolute.suffix + ".metadata.json")
        if not metadata.exists():
            atomic_write(metadata, encoded(entry))
        atomic_write(cache_path, encoded(entry))
        log.info("%s: Originaldatei %s (%s Bytes)", self.cfg.key, path.name, len(content))
        return entry

    def body(self, entry: dict) -> Any:
        return json.loads((self.folder / entry["path"]).read_bytes())

    def close(self) -> None:
        if self.owns_client:
            self.client.close()


class ExternalFetcher:
    def __init__(self, config: SourceConfig, root: Path, user_agent: str):
        self.config, self.root, self.user_agent = config, root, user_agent

    def fetch(self, etag=None, last_modified=None) -> FetchResult:
        c = RawClient(self.config, self.root, self.user_agent)
        try:
            mode = self.config.external_mode
            pages: list[dict] = []
            coverage: dict = {"complete_swiss_market": False}
            data_as_of = None
            if mode == "gleif_ch":
                expected, publish, seen = None, None, set()
                url = self.config.location
                params = {"filter[entity.legalAddress.country]": "CH", "page[size]": 200,
                          "page[cursor]": "*"}
                for _ in range(20000):
                    entry = c.get(url, params=params)
                    body = c.body(entry)
                    pagination = body["meta"]["pagination"]
                    current_publish = body["meta"]["goldenCopy"]["publishDate"]
                    if expected is None:
                        expected, publish = int(pagination["total"]), current_publish
                    if int(pagination["total"]) != expected or current_publish != publish:
                        raise FetchError("GLEIF-Snapshot während Abruf geändert", transient=False)
                    for record in body["data"]:
                        if record["id"] in seen:
                            raise FetchError("GLEIF-Pagination enthält doppelte LEIs",
                                             transient=False)
                        seen.add(record["id"])
                    pages.append(entry)
                    if not body.get("links", {}).get("next"):
                        break
                    url, params = body["links"]["next"], None
                else:
                    raise FetchError("GLEIF-Seitenlimit erreicht", transient=False)
                if len(seen) != expected:
                    raise FetchError("GLEIF-Seiten unvollständig", transient=False)
                coverage.update(api_total=expected, downloaded_unique=len(seen),
                                complete_api_filter=True, filter="entity.legalAddress.country=CH")
                data_as_of = publish[:10]
            elif mode == "zefix":
                cursor = ""
                seen = set()
                for _ in range(2000):
                    query = ZEFIX_PREFIX + '''SELECT ?company ?name ?uid ?legalForm ?municipality
                    WHERE {
                      { SELECT DISTINCT ?company WHERE {
                        ?company a admin:ZefixOrganisation .
                        FILTER(STR(?company) > ''' + json.dumps(cursor) + ''')
                      } ORDER BY ?company LIMIT 100000 }
                      ?company a admin:ZefixOrganisation; schema:name ?name;
                        schema:identifier ?identifier; schema:additionalType ?legalForm.
                      ?identifier schema:value ?uid.
                      FILTER(STRSTARTS(STR(?uid), "CHE"))
                      OPTIONAL {?company admin:municipality ?municipality}
                    } ORDER BY ?company'''
                    entry = c.get(self.config.location, params={"query": query})
                    rows = c.body(entry)["results"]["bindings"]
                    seen.update(r["company"]["value"] for r in rows)
                    pages.append(entry)
                    if not rows:
                        break
                    next_cursor = rows[-1]["company"]["value"]
                    if next_cursor <= cursor:
                        raise FetchError("Zefix-Cursor ohne Fortschritt", transient=False)
                    cursor = next_cursor
                    if len({r["company"]["value"] for r in rows}) < 100000:
                        break
                else:
                    raise FetchError("Zefix-Seitenlimit erreicht", transient=False)
                count_query = ZEFIX_PREFIX + '''SELECT (COUNT(DISTINCT ?company) AS ?count)
                WHERE {
                  ?company a admin:ZefixOrganisation; schema:name ?name;
                    schema:identifier ?identifier; schema:additionalType ?legalForm.
                  ?identifier schema:value ?uid.
                  FILTER(STRSTARTS(STR(?uid), "CHE"))
                }'''
                count_entry = c.get(self.config.location, params={"query": count_query})
                count_body = c.body(count_entry)["results"]["bindings"]
                expected = int(count_body[0]["count"]["value"])
                pages.append(dict(count_entry, role="count"))
                if len(seen) != expected:
                    raise FetchError(f"Zefix unvollständig: {len(seen)} von {expected}",
                                     transient=False)
                coverage.update(exhausted_query=True, atomic_snapshot=False,
                                query_total=expected, downloaded_unique=len(seen),
                                scope="Aktive ZefixOrganisation mit CHE-UID und Rechtsform")
            elif mode == "wikidata":
                query_files = [self.config.query_file, "data/queries/wikidata_funds.sparql"]
                for query_file in query_files:
                    query = (self.root / query_file).read_text(encoding="utf-8")
                    entry = c.get(self.config.location, params={"query": query, "format": "json"})
                    entry = dict(entry, role="funds" if "funds" in query_file else "companies")
                    pages.append(entry)
                coverage.update(scope="Wikidata company/fund candidates, CH or SIX; incomplete")
            elif mode == "swissprtr":
                entry = c.get(self.config.location)
                body = c.body(entry)
                pages.append(dict(entry, role="stac"))
                asset = body["assets"]["swissprtr_2056.gpkg.zip"]
                download = c.get(asset["href"], suffix="zip")
                expected_hash = asset.get("checksum:multihash", "")
                if not expected_hash.startswith("1220") or download["sha256"] != expected_hash[4:]:
                    raise FetchError("SwissPRTR STAC-Prüfsumme stimmt nicht", transient=False)
                pages.append(dict(download, role="geopackage"))
                if self.config.supplementary_url:
                    workbook = c.get(self.config.supplementary_url, suffix="xlsx")
                    with zipfile.ZipFile(io.BytesIO(
                            (c.folder / workbook["path"]).read_bytes())) as archive:
                        if "xl/workbook.xml" not in archive.namelist():
                            raise FetchError("SwissPRTR-Download ist keine XLSX-Datei",
                                             transient=False)
                    pages.append(dict(workbook, role="original_emissions_workbook"))
                data_as_of = body["properties"]["datetime"][:10]
                coverage.update(
                    scope="Standorte; Emissionen 2007–2024 aus Original-XLSX normalisiert",
                    emissions_normalized=bool(self.config.supplementary_url))
            else:
                raise FetchError(f"Unbekannter Modus: {mode}", transient=False)
            # Download times are sidecars. Manifest hash changes only with data/coverage.
            compact = [{k: v for k, v in p.items() if k in
                        {"path", "sha256", "bytes", "url", "format", "role"}} for p in pages]
            bundle = {"format": FORMAT, "source_key": self.config.key, "mode": mode,
                      "pages": compact, "data_as_of": data_as_of, "coverage": coverage}
            return FetchResult(origin=self.config.location, content=encoded(bundle))
        except (KeyError, ValueError, TypeError) as exc:
            raise FetchError(f"Ungültige Quellenstruktur: {exc}", transient=False) from exc
        finally:
            c.close()


def _value(row: dict, field_name: str) -> str | None:
    return row.get(field_name, {}).get("value")


def _gleif(body: dict, ds: ExternalDataset) -> None:
    for raw in body["data"]:
        raw_lei = raw.get("attributes", {}).get("lei")
        if not is_valid_lei(raw_lei) or raw.get("id") != raw_lei:
            ds.extra.setdefault("quarantined_identifiers", []).append({
                "source_key": "gleif_ch", "lei": raw_lei, "id": raw.get("id"),
                "reason": "invalid_lei_checksum_or_inconsistent_id"})
            ds.warn(f"GLEIF LEI {raw_lei}: ungültige Kennung, in Quarantäne.")
            continue
        record = GleifLeiRecord.model_validate(raw)
        a = record.attributes
        entity = raw["attributes"]["entity"]
        if a.entity.legalAddress.country != "CH":
            raise ValueError("GLEIF lieferte Rechtsadresse ausserhalb CH")
        item = {"company_key": f"lei:{a.lei}", "lei": a.lei,
                "name": a.entity.legalName.name, "country": "CH",
                "uid": normalize_uid(entity.get("registeredAs")),
                "registered_as": entity.get("registeredAs"),
                "category": entity.get("category"), "entity_status": a.entity.status,
                "registration_status": a.registration.status,
                "legal_form": entity.get("legalForm", {}).get("id"),
                "seat": entity.get("legalAddress", {}).get("city"),
                "source_key": "gleif_ch", "data_as_of": ds.data_as_of.isoformat()
                if ds.data_as_of else None}
        if a.registration.status in REGISTRATION_EXCLUDED:
            ds.extra.setdefault("excluded", []).append(item)
            continue
        if entity.get("category") == "FUND":
            ds.extra.setdefault("funds", []).append(dict(
                item, isin=None, provider=None, domicile="CH", exchange=None,
                reference_index=None, sustainability_label=None, fund_type="GLEIF FUND"))
            continue
        ds.extra.setdefault("company_attributes", []).append(item)
        ds.records["companies"].append(CompanyRecord.model_validate(item))
        for kind in ("direct-parent", "ultimate-parent"):
            links = raw.get("relationships", {}).get(kind, {}).get("links", {})
            ds.extra.setdefault("unresolved_relationships", []).append({
                "child_key": item["company_key"], "kind": kind,
                "relationship_url": links.get("relationship-record"),
                "exception_url": links.get("reporting-exception"),
                "status": "not_fetched" if "relationship-record" in links
                else "reporting_exception_or_unavailable", "verified": False})


def _zefix(body: dict, ds: ExternalDataset) -> None:
    groups: dict[str, list[dict]] = {}
    for row in body["results"]["bindings"]:
        groups.setdefault(_value(row, "company"), []).append(row)
    priority = {"": 0, "de": 1, "en": 2, "fr": 3, "it": 4}
    for uri, variants in groups.items():
        variants.sort(key=lambda r: (priority.get(r["name"].get("xml:lang", ""), 5),
                                     _value(r, "name")))
        row = variants[0]
        if len({_value(r, "uid") for r in variants}) != 1:
            ds.extra.setdefault("quarantined_identifiers", []).append({
                "source_key": "zefix_lindas", "source_uri": uri,
                "reason": "multiple_uids_for_register_entity"})
            continue
        uid = normalize_uid(_value(row, "uid"))
        if not uid:
            ds.extra.setdefault("quarantined_identifiers", []).append({
                "source_key": "zefix_lindas", "uid": _value(row, "uid"),
                "source_uri": _value(row, "company"), "reason": "invalid_uid_checksum"})
            continue
        item = {"company_key": f"uid:{uid}", "name": _value(row, "name"),
                "uid": uid, "lei": None, "country": "CH",
                "legal_form": _value(row, "legalForm"),
                "municipality": _value(row, "municipality"),
                "source_uri": _value(row, "company"), "source_key": "zefix_lindas",
                "data_as_of": None,
                "name_variants": [{"name": _value(r, "name"),
                                   "language": r["name"].get("xml:lang")} for r in variants]}
        ds.extra.setdefault("company_attributes", []).append(item)
        ds.records["companies"].append(CompanyRecord.model_validate(item))


_WIKIDATA_COLUMNS = (("lei", "P1278"), ("isin", "P946"), ("exchange", "P414"),
                     ("ticker", "P249"), ("tickerQ", "P249"), ("country", "P17"),
                     ("parent", "P749"), ("instanceOf", "P31"))


def _wikidata(body: dict, ds: ExternalDataset, role: str) -> None:
    # Wide columns, not melted property/value rows: the live query service times out
    # on an unbound-predicate join even for a handful of pre-filtered items (see
    # data/queries/wikidata_ch.sparql).
    grouped: dict[str, dict] = {}
    for row in body["results"]["bindings"]:
        qid = _value(row, "item").rsplit("/", 1)[-1]
        item = grouped.setdefault(qid, {"wikidata_id": qid, "label_de": None, "label_en": None,
                                       "claims": {prop: set() for _, prop in _WIKIDATA_COLUMNS},
                                       "source_key": "wikidata_ch"})
        item["label_de"] = item["label_de"] or _value(row, "labelDe")
        item["label_en"] = item["label_en"] or _value(row, "labelEn")
        for field_name, prop in _WIKIDATA_COLUMNS:
            value = _value(row, field_name)
            if value:
                item["claims"][prop].add(value)
    candidates: dict[str, dict] = {}
    for qid, item in grouped.items():
        item["claims"] = {k: sorted(v) for k, v in item["claims"].items() if v}
        label_de, label_en = item.pop("label_de"), item.pop("label_en")
        item["name"] = label_de or label_en or item["wikidata_id"]
        leis = item["claims"].get("P1278", [])
        isins = item["claims"].get("P946", [])
        if any(not is_valid_lei(x) for x in leis) or any(not is_valid_isin(x) for x in isins):
            ds.extra.setdefault("identifier_conflicts", []).append(item)
            continue
        item["lei"] = leis[0] if len(leis) == 1 else None
        candidates[qid] = item
    # Two different Wikidata items can carry the same LEI (seen live: a holding and an
    # older/merged item both claim one LEI). Quarantine the shared LEI instead of
    # rejecting the whole source or merging by name.
    lei_items: dict[str, list[dict]] = defaultdict(list)
    for item in candidates.values():
        if item["lei"]:
            lei_items[item["lei"]].append(item)
    shared_leis = {lei for lei, items in lei_items.items() if len(items) > 1}
    for item in candidates.values():
        isins = item["claims"].get("P946", [])
        if item["lei"] in shared_leis:
            ds.extra.setdefault("identifier_conflicts", []).append(
                dict(item, reason="lei_shared_by_multiple_wikidata_items"))
            continue
        item["company_key"] = f"wikidata:{item['wikidata_id']}"
        item["country"] = "CH" if "http://www.wikidata.org/entity/Q39" in (
            item["claims"].get("P17", [])) else None
        ds.extra.setdefault("funds" if role == "funds" else "company_attributes", []).append(item)
        if role != "funds":
            ds.records["companies"].append(CompanyRecord.model_validate(item))
        for isin in isins:
            ds.extra.setdefault("security_candidates", []).append({
                "isin": isin, "wikidata_id": item["wikidata_id"],
                "name": item["name"], "issuer_company_key": None,
                "mapping_status": "unverified_company_level_claim", "claims": item["claims"],
                "source_key": "wikidata_ch", "data_as_of": None})


def _swissprtr(content: bytes, ds: ExternalDataset, folder: Path) -> None:
    # GeoPackage is SQLite; stdlib suffices, no GIS framework or Excel dependency.
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        members = [n for n in archive.namelist() if n.endswith(".gpkg")]
        if len(members) != 1:
            raise ValueError("SwissPRTR ZIP muss ein GeoPackage enthalten")
        with tempfile.TemporaryDirectory(dir=folder) as temporary:
            path = Path(temporary) / "source.gpkg"
            path.write_bytes(archive.read(members[0]))
            with closing(sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)) as conn:
                conn.row_factory = sqlite3.Row
                tables = conn.execute("SELECT table_name FROM gpkg_contents").fetchall()
                for table_row in tables:
                    table = table_row[0].replace('"', '""')
                    for row in conn.execute(f'SELECT * FROM "{table}"'):
                        attrs = {k: v for k, v in dict(row).items()
                                 if not isinstance(v, bytes)}
                        ds.extra.setdefault("facilities", []).append({
                            "attributes": attrs, "source_table": table_row[0],
                            "source_key": "swissprtr", "data_as_of": str(ds.data_as_of),
                            "company_key": None, "mapping_status": "unresolved",
                            "evidence_category": "facility_register_not_violation"})


_XLSX_NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
            "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
            "rel": "http://schemas.openxmlformats.org/package/2006/relationships"}
EMISSION_HEADERS = {"Facility ID", "UID of facility", "UID holder", "Year", "Source type",
                    "Pollutant_name", "CAS", "Pollutant_group", "Medium", "Value", "Unit",
                    "Diffuse_sources"}


def _xlsx_header_and_rows(content: bytes) -> tuple[dict[str, str], list[dict[str, str]]]:
    """Minimal OOXML reader: shared strings + the 'Daten…' sheet's rows.

    Stdlib only (zipfile + ElementTree), matching the no-Excel-dependency approach
    already used for the SwissPRTR GeoPackage.
    """
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {rel.get("Id"): rel.get("Target")
                   for rel in rels.findall(f"{{{_XLSX_NS['rel']}}}Relationship")}
        sheet = next((s for s in workbook.findall(".//s:sheets/s:sheet", _XLSX_NS)
                      if (s.get("name") or "").startswith("Daten")), None)
        if sheet is None:
            raise ValueError("Kein Datenblatt 'Daten…' in der Arbeitsmappe gefunden")
        target = targets.get(sheet.get(f"{{{_XLSX_NS['r']}}}id"))
        if not target:
            raise ValueError("Datenblatt-Verweis in der Arbeitsmappe fehlt")
        sheet_xml = ET.fromstring(archive.read(f"xl/{target}"))
        strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            strings = ["".join(t.text or "" for t in si.findall(".//s:t", _XLSX_NS))
                       for si in shared.findall("s:si", _XLSX_NS)]

        def cell_value(cell) -> str | None:
            value = cell.find("s:v", _XLSX_NS)
            text = value.text if value is not None else None
            if cell.get("t") == "s" and text is not None:
                return strings[int(text)]
            if cell.get("t") == "inlineStr":
                inline = cell.find("s:is/s:t", _XLSX_NS)
                return inline.text if inline is not None else None
            return text

        rows = []
        for row in sheet_xml.findall(".//s:sheetData/s:row", _XLSX_NS):
            cells = {}
            for cell in row.findall("s:c", _XLSX_NS):
                match = re.match(r"[A-Z]+", cell.get("r", ""))
                if match:
                    cells[match.group()] = cell_value(cell)
            rows.append(cells)
        if not rows:
            raise ValueError("Datenblatt der Arbeitsmappe ist leer")
        header = {col: name for col, name in rows[0].items() if name}
        return header, rows[1:]


def _swissprtr_emissions(content: bytes, ds: ExternalDataset) -> None:
    """Normalise the archived original SwissPRTR emissions workbook (2007–2024).

    Linking to a company uses only the row's own validated facility UID, the same
    exact-match rule as everywhere else; it never uses the facility name. Diffuse
    (non-point) sources report no facility and stay explicitly unlinked. Emissions
    are an official report, not evidence of a legal violation (evidence_category).
    """
    header, data_rows = _xlsx_header_and_rows(content)
    by_name = {name: col for col, name in header.items()}
    missing = EMISSION_HEADERS - set(by_name)
    if missing:
        raise ValueError(f"SwissPRTR-Arbeitsmappe: Spalten fehlen: {sorted(missing)}")
    invalid_uid = 0
    for row in data_rows:
        year_raw = row.get(by_name["Year"])
        if (not year_raw or not re.fullmatch(r"\d{4}", year_raw)
                or not 2000 <= int(year_raw) <= 2100):
            continue
        raw_uid = row.get(by_name["UID of facility"])
        uid = normalize_uid(raw_uid)
        if raw_uid and not uid:
            invalid_uid += 1
        value_raw = row.get(by_name["Value"])
        try:
            value = float(value_raw) if value_raw is not None else None
        except ValueError:
            value = None
        source_type = row.get(by_name["Source type"])
        ds.extra.setdefault("emissions", []).append({
            "source_key": "swissprtr",
            "data_as_of": str(ds.data_as_of) if ds.data_as_of else None,
            "facility_id": row.get(by_name["Facility ID"]),
            "uid_facility": uid, "uid_facility_raw": None if uid else raw_uid,
            "uid_holder": normalize_uid(row.get(by_name["UID holder"])),
            "year": int(year_raw), "source_type": source_type,
            "pollutant_name": row.get(by_name["Pollutant_name"]),
            "cas": row.get(by_name["CAS"]), "pollutant_group": row.get(by_name["Pollutant_group"]),
            "medium": row.get(by_name["Medium"]), "value": value,
            "unit": row.get(by_name["Unit"]),
            "diffuse_source_description": row.get(by_name["Diffuse_sources"]),
            "company_key": None,
            "mapping_status": "diffuse_source_no_facility" if source_type == "Nicht-Punktquelle"
            else "unresolved",
            "evidence_category": "emission_register_not_violation"})
    if invalid_uid:
        ds.warn(f"SwissPRTR-Emissionen: {invalid_uid} Betriebs-UID(s) mit ungültiger Prüfziffer, "
                "ohne Unternehmenszuordnung übernommen.")


def parse_external(content: bytes, cfg: SourceConfig, root: Path) -> ExternalDataset:
    ds = ExternalDataset(DatasetKind.ENTITIES)
    ds.records = {"companies": [], "securities": [], "relationships": []}
    folder = (root / "data/raw/external" / cfg.key).resolve()
    try:
        bundle = json.loads(content)
        if bundle["format"] != FORMAT or bundle["source_key"] != cfg.key:
            raise ValueError("Falsches Manifestformat/Quelle")
        ds.coverage = bundle["coverage"]
        ds.data_as_of = date.fromisoformat(bundle["data_as_of"]) if bundle["data_as_of"] else None
        for entry in bundle["pages"]:
            path = (folder / entry["path"]).resolve()
            if not path.is_relative_to(folder):
                raise ValueError("Rohdatenpfad ausserhalb Quellenordner")
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != entry["sha256"] or len(raw) != entry["bytes"]:
                raise ValueError("Rohdaten verändert/Prüfsumme ungültig")
            if cfg.external_mode == "swissprtr":
                if entry.get("role") == "geopackage":
                    _swissprtr(raw, ds, folder)
                elif entry.get("role") == "original_emissions_workbook":
                    _swissprtr_emissions(raw, ds)
                continue
            body = json.loads(raw)
            if entry.get("role") == "count":
                continue
            if cfg.external_mode == "gleif_ch":
                _gleif(body, ds)
            elif cfg.external_mode == "zefix":
                _zefix(body, ds)
            elif cfg.external_mode == "wikidata":
                _wikidata(body, ds, entry.get("role", "companies"))
        if cfg.external_mode == "zefix":
            by_key: dict[str, list[dict]] = {}
            for item in ds.extra.get("company_attributes", []):
                by_key.setdefault(item["company_key"], []).append(item)
            collisions = {k for k, values in by_key.items()
                          if len({v["source_uri"] for v in values}) > 1}
            for key in sorted(collisions):
                ds.extra.setdefault("identifier_conflicts", []).append({
                    "company_key": key, "reason": "multiple_register_entities_for_uid",
                    "source_records": by_key[key]})
                for item in by_key[key]:
                    ds.extra.setdefault("quarantined_identifiers", []).append(dict(
                        item, reason="multiple_register_entities_for_uid"))
            ds.records["companies"] = [r for r in ds.records["companies"]
                                       if r.company_key not in collisions]
            ds.extra["company_attributes"] = [r for r in ds.extra.get("company_attributes", [])
                                               if r["company_key"] not in collisions]
        if cfg.external_mode != "swissprtr":
            check_entities(ds, ds.records["companies"], [], [])
        elif not ds.extra.get("facilities"):
            ds.error("SwissPRTR ohne Standorte")
        if (cfg.external_mode == "swissprtr"
                and any(p.get("role") == "original_emissions_workbook" for p in bundle["pages"])
                and not ds.extra.get("emissions")):
            ds.error("SwissPRTR-Emissionsarbeitsmappe ohne auswertbare Zeilen")
        if cfg.external_mode == "gleif_ch":
            count = (len(ds.records["companies"]) + len(ds.extra.get("funds", []))
                     + len(ds.extra.get("excluded", []))
                     + len(ds.extra.get("quarantined_identifiers", [])))
            if count != ds.coverage["api_total"]:
                ds.error("GLEIF-Zählung stimmt nicht mit API-Gesamtzahl überein")
        quarantined = len(ds.extra.get("quarantined_identifiers", []))
        if quarantined > max(1, ds.record_count * 0.01):
            ds.error("Mehr als 1% ungültige Kennungen: Gesamtdatenstand abgelehnt")
        if cfg.external_mode == "zefix":
            ds.warn("Zefix: zeitlich gestaffelte Extraktion, kein atomarer Registerstand.")
    except (ValueError, KeyError, TypeError, OSError, ValidationError,
            sqlite3.Error, zipfile.BadZipFile, ET.ParseError) as exc:
        ds.error(f"Externe Rohdaten ungültig: {exc}")
    return ds


def build_external_adapter(config: SourceConfig, catalog: Catalog,
                           project_root: Path, user_agent: str):
    from transparenz.ingestion.adapters import SourceAdapter

    class ExternalAdapter(SourceAdapter):
        def parse(self, content: bytes) -> ExternalDataset:
            return parse_external(content, self.config, project_root)

    return ExternalAdapter(config, ExternalFetcher(config, project_root, user_agent),
                           catalog.criterion_keys)
