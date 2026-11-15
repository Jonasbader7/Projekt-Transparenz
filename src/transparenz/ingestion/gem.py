"""Global Energy Monitor (CC BY 4.0): Besitzketten und Anlagenlisten aus den XLSX-Dateien."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

from transparenz.entities.identifiers import is_valid_lei
from transparenz.services.ownership import (
    ASSET_MANAGEMENT,
    CUSTODY,
    FINANCIAL_STAKE,
    OWN_ACCOUNT,
    Hop,
    classify_chain,
    parse_path,
    stake_tier,
)

# ------------------------------------------------------------- Global Energy Monitor
XLSX_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

XLSX_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

GEM_OWNERSHIP_GLOB = "Global-Energy-Ownership-Tracker-*.xlsx"

GEM_LICENCE_URL = "https://globalenergymonitor.org/creative-commons-license"

GEM_SHEETS: dict[str, tuple[str, str]] = {
    "Coal Plant Ownership": ("coal", "coal_plant"),
    "Coal Mine Ownership": ("coal", "coal_mine"),
    "Gas Plant Ownership": ("oil_gas", "gas_plant"),
    "LNG Terminal Ownership": ("oil_gas", "lng_terminal"),
    "Gas Pipeline Ownership": ("oil_gas", "gas_pipeline"),
    "Oil & NGL Pipeline Ownership": ("oil_gas", "oil_pipeline"),
}

# Anlagenlisten von GEM (gleiche Lizenz), aus denen Brennstoff, Inbetriebnahme, Betreiber und
# Eigenbedarf je Einheit gelesen werden. Fehlt eine Datei, fehlen nur diese Angaben.
GEM_TRACKERS: dict[str, tuple[str, tuple[str, ...], str]] = {
    "gogpt": ("Global Oil and Gas Plant Tracker*.xlsx",
              ("Gas & Oil Units", "Sub-Threshold Units", "IRP Units"), "GEM unit ID"),
    "gcpt": ("Global-Coal-Plant-Tracker-*.xlsx", ("Units",), "GEM unit/phase ID"),
}

GEM_EXPANSION = frozenset({"announced", "pre-permit", "permitted", "pre-construction",
                           "construction", "proposed"})

GEM_OPERATING = frozenset({"operating", "mothballed", "idle", "idled"})

# Regel bis Profil 1.0 (D-040/D-043), nur noch für den Vorher-nachher-Vergleich im Bericht.
GEM_CUSTODIAL_RE = re.compile(r"nominee|custod|securities clearing|depositor|depositar", re.I)

OWN_TIERS = ("control", "significant", "small", "unknown")

GEM_STAKES = (*OWN_TIERS, FINANCIAL_STAKE, ASSET_MANAGEMENT, CUSTODY)

GEM_STATUSES = ("expansion", "operating", "closed", "unknown")

GEM_DISPLAY_LIMIT = 30

GEM_UNIT_COLUMNS = ("GEM unit ID", "UnitID", "GEM Mine ID", "ProjectID")


def _xlsx_col(ref: str) -> int:
    number = 0
    for ch in re.match(r"[A-Z]+", ref).group(0):
        number = number * 26 + ord(ch) - 64
    return number - 1


class XlsxReader:
    """Streamender XLSX-Leser nur mit der Standardbibliothek (wie D-032, kein openpyxl)."""

    def __init__(self, path: Path):
        self.archive = zipfile.ZipFile(path)
        self.shared: list[str] = []
        if "xl/sharedStrings.xml" in self.archive.namelist():
            with self.archive.open("xl/sharedStrings.xml") as handle:
                for _, element in ET.iterparse(handle):
                    if element.tag == XLSX_NS + "si":
                        self.shared.append("".join(t.text or "" for t in element.iter(
                            XLSX_NS + "t")))
                        element.clear()
        book = ET.fromstring(self.archive.read("xl/workbook.xml"))
        rels = ET.fromstring(self.archive.read("xl/_rels/workbook.xml.rels"))
        target = {r.get("Id"): r.get("Target") for r in rels}
        self.sheets: dict[str, str] = {}
        for sheet in book.iter(XLSX_NS + "sheet"):
            path_in_zip = target[sheet.get(XLSX_REL + "id")].lstrip("/")
            self.sheets[sheet.get("name")] = (path_in_zip if path_in_zip.startswith("xl/")
                                              else "xl/" + path_in_zip)

    def rows(self, sheet: str) -> Any:
        with self.archive.open(self.sheets[sheet]) as handle:
            for _, element in ET.iterparse(handle):
                if element.tag != XLSX_NS + "row":
                    continue
                cells: dict[int, str] = {}
                for cell in element.iter(XLSX_NS + "c"):
                    value = cell.find(XLSX_NS + "v")
                    kind = cell.get("t")
                    if kind == "s" and value is not None:
                        text = self.shared[int(value.text)]
                    elif kind == "inlineStr":
                        text = "".join(t.text or "" for t in cell.iter(XLSX_NS + "t"))
                    else:
                        text = value.text if value is not None else None
                    if text not in (None, ""):
                        cells[_xlsx_col(cell.get("r"))] = text
                element.clear()
                yield [cells.get(i) for i in range(max(cells) + 1 if cells else 0)]

    def table(self, sheet: str) -> Any:
        rows = self.rows(sheet)
        header = next(rows, [])
        for row in rows:
            yield {h: (row[i] if i < len(row) else None) for i, h in enumerate(header) if h}


def gem_stake(share: float | None, path: str | None) -> str:
    """Beteiligungsstufe nach der Regel bis Profil 1.0 (nur Verwahrung wurde ausgenommen).

    Bleibt für den Vergleich «vorher/nachher» im Bericht; die geltende Einordnung macht
    ``classify_gem_assets`` mit den Beziehungstypen.
    """
    if path and GEM_CUSTODIAL_RE.search(path):
        return "custodial"
    return stake_tier(share)


def gem_status(status: str | None) -> str:
    value = (status or "").strip().lower()
    if value in GEM_EXPANSION:
        return "expansion"
    if value in GEM_OPERATING:
        return "operating"
    if value in ("", "-", "–", "unknown"):
        return "unknown"
    return "closed"  # retired, cancelled, shelved, auch «… - inferred»


def _year(value: str | None) -> int | None:
    try:
        return int(float(value)) if value not in (None, "") else None
    except ValueError:
        return None


def load_gem_trackers(gem_dir: Path | None, unit_ids: set[str]) -> dict[str, Any]:
    """Details je Einheit aus den GEM-Anlagenlisten (nur für die übergebenen Einheiten)."""
    details: dict[str, dict[str, Any]] = {}
    files: list[str] = []
    if gem_dir is None:
        return {"units": details, "files": files}
    for pattern, sheets, id_column in GEM_TRACKERS.values():
        found = sorted(gem_dir.glob(pattern))
        if len(found) != 1:
            continue
        book = XlsxReader(found[0])
        files.append(found[0].name)
        for sheet in sheets:
            if sheet not in book.sheets:
                continue
            for row in book.table(sheet):
                unit = row.get(id_column)
                if unit not in unit_ids or unit in details:
                    continue
                unit_name = row.get("Unit name") or ""
                details[unit] = {
                    "plant": row.get("Plant name"), "unit": unit_name or None,
                    "country": row.get("Country/Area"), "fuel": row.get("Fuel"),
                    "start_year": _year(row.get("Start year")),
                    "retired_year": _year(row.get("Retired year")),
                    "operator": row.get("Operator(s)"), "owner": row.get("Owner(s)") or row.get(
                        "Owner"),
                    "captive_use": row.get("Captive industry use") or row.get("Captive"),
                    "captive_type": row.get("Captive industry type"),
                    "captive_non_industry": row.get("Captive non-industry use"),
                    "backup": ((row.get("Backup Power") or "").lower() == "yes"
                               or "backup" in unit_name.lower()),
                    "wiki_url": row.get("Wiki URL"), "list": found[0].name}
    return {"units": details, "files": files}


def load_gem(ownership_xlsx: Path, leis: set[str], gem_dir: Path | None = None) -> dict[str, Any]:
    """Liest den Energy Ownership Tracker für die übergebenen LEIs.

    Zuordnung ausschliesslich über die LEI-Spalte von GEM selbst («Global Legal Entity
    Identifier Index»), nie über Namen. Je Anlage bleiben Anteil, Besitzkette (mit Anteil und
    Quellen-URL je Glied, soweit GEM sie führt) und Status erhalten; kein Anteil wird
    umgedeutet. Zusätzlich: ob eine Gesellschaft der Kette laut GEM börsenkotiert ist.
    """
    book = XlsxReader(ownership_xlsx)
    missing = {"All Entities", *GEM_SHEETS} - set(book.sheets)
    if missing:
        raise ValueError(f"{ownership_xlsx.name}: Blätter fehlen: {sorted(missing)}")
    entities: dict[str, set[str]] = defaultdict(set)
    names: dict[str, str | None] = {}
    listed_votes: dict[str, set[bool]] = defaultdict(set)
    ids_by_name: dict[str, set[str]] = defaultdict(set)
    for row in book.table("All Entities"):
        eid = row.get("Entity ID")
        flag = (row.get("PubliclyListed") or "").strip() == "1"
        for name in {(row.get("Full Name") or "").strip(), (row.get("Name") or "").strip()}:
            if name:
                listed_votes[name].add(flag)
                ids_by_name[name].add(eid)
        lei = (row.get("Global Legal Entity Identifier Index") or "").strip().upper()
        if lei in leis and is_valid_lei(lei):
            entities[lei].add(eid)
            names[eid] = row.get("Name") or row.get("Full Name")
    lei_by_entity = {eid: lei for lei, ids in entities.items() for eid in ids}
    assets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: set[tuple[Any, ...]] = set()
    for sheet, (category, kind) in GEM_SHEETS.items():
        for row in book.table(sheet):
            lei = lei_by_entity.get(row.get("Parent GEM Entity ID"))
            if not lei:
                continue
            try:
                share: float | None = float(row.get("Share"))
            except (TypeError, ValueError):
                share = None
            path = row.get("Ownership Path")
            unit = next((row[c] for c in GEM_UNIT_COLUMNS if row.get(c)), None)
            key = (lei, kind, unit, row.get("Project"), path)
            if key in seen:
                continue
            seen.add(key)
            capacity = next(((h, row[h]) for h in row if h.startswith("Capacity") and row[h]),
                            (None, None))
            assets[lei].append({
                "category": category, "kind": kind, "project": row.get("Project"),
                "unit_id": unit, "status": row.get("Status"),
                "status_group": gem_status(row.get("Status")), "share": share,
                "stake": stake_tier(share), "path": path,
                "hops": [{"holder": h.holder, "name": h.name, "share": h.share}
                         for h in parse_path(path)],
                "immediate_owner": row.get("Immediate Project Owner"),
                "capacity_label": capacity[0], "capacity": capacity[1],
                "tracker": row.get("Tracker"),
            })
    # Quellen je Glied: «Entity Ownership» führt je Beteiligung eine Quellen-URL.
    wanted: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    chain_names: set[str] = set()
    for items in assets.values():
        for asset in items:
            for hop in asset["hops"][:-1]:  # das letzte Glied ist die Anlage selbst
                chain_names.update((hop["holder"], hop["name"]))
                for holder_id in ids_by_name.get(hop["holder"], ()):
                    for subject_id in ids_by_name.get(hop["name"], ()):
                        wanted[(holder_id, subject_id)].append(hop)
            chain_names.add(asset["hops"][0]["holder"] if asset["hops"] else "")
    if wanted and "Entity Ownership" in book.sheets:
        for row in book.table("Entity Ownership"):
            for hop in wanted.get((row.get("Interested Party ID"), row.get("Subject Entity ID")),
                                  []):
                hop["source_url"] = (row.get("Data Source URL") or "").split(",")[0].strip() or None
                hop["imputed"] = (row.get("Share Imputed?") or "").startswith("imputed")
    trackers = load_gem_trackers(gem_dir, {a["unit_id"] for items in assets.values()
                                           for a in items if a["unit_id"]})
    for items in assets.values():
        for asset in items:
            asset["details"] = trackers["units"].get(asset["unit_id"])
    return {"file": ownership_xlsx.name, "release": ownership_xlsx.stem.replace("-", " "),
            "licence": "CC BY 4.0", "licence_url": GEM_LICENCE_URL,
            "entities": {lei: sorted(ids) for lei, ids in entities.items()},
            "names": names, "assets": dict(assets), "tracker_files": trackers["files"],
            "listed": {name: votes == {True} for name, votes in listed_votes.items()
                       if name in chain_names}}


def classify_gem_assets(assets: list[dict[str, Any]], holder_is_financial: bool | None,
                        listed: dict[str, bool]) -> list[dict[str, Any]]:
    """Ordnet jede Besitzkette einem Beziehungstyp zu (services/ownership.py, D-045).

    ``stake`` ist danach die Anteilsstufe bei Eigentum auf eigene Rechnung, sonst der
    Beziehungstyp. ``old_stake`` hält die Einordnung nach Profil 1.0 für den Vergleich fest.
    """
    out = []
    for asset in assets:
        hops = [Hop(h["holder"], h["name"], h["share"]) for h in asset.get("hops") or []]
        result = classify_chain(hops, holder_is_financial=holder_is_financial, listed=listed)
        out.append({**asset, "relationship": result.relationship,
                    "relationship_reason": result.reason, "deciding_hop": result.deciding_hop,
                    "stake": (stake_tier(asset["share"]) if result.relationship == OWN_ACCOUNT
                              else result.relationship),
                    "old_stake": gem_stake(asset["share"], asset.get("path"))})
    return out


def summarise_gem(lei: str, gem: dict[str, Any],
                  assets: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    """Zählt Anlagen je Kategorie, Beziehungstyp bzw. Stufe und Status; zeigt die wichtigsten."""
    if lei not in gem["entities"]:
        return None
    assets = gem["assets"].get(lei, []) if assets is None else assets
    counts: dict[str, dict[str, int]] = {}
    for item in assets:
        bucket = counts.setdefault(item["category"], {})
        key = f"{item['stake']}|{item['status_group']}"
        bucket[key] = bucket.get(key, 0) + 1

    def rank(item: dict[str, Any]) -> tuple[Any, ...]:
        try:
            capacity = -float(item["capacity"])
        except (TypeError, ValueError):
            capacity = 0.0
        return (GEM_STAKES.index(item["stake"]), GEM_STATUSES.index(item["status_group"]),
                capacity)

    shown = {category: sorted((a for a in assets if a["category"] == category), key=rank)
             [:GEM_DISPLAY_LIMIT] for category in ("coal", "oil_gas")}
    return {"entity_ids": gem["entities"][lei],
            "entity_names": sorted({gem["names"].get(e) or e for e in gem["entities"][lei]}),
            "assets_total": len(assets), "counts": counts, "shown": shown,
            "release": gem["release"]}
