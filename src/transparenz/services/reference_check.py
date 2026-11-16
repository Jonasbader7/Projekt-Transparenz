"""Gegenprüfung: Zuordnungen des Pilots an der N-PORT-Referenz messen (Phase 2, D-056).

Referenz = ISIN mit Status ``confirmed`` im Wertpapierstamm (``security_master.sqlite``):
zwei unabhängige Fondsgesellschaften melden denselben Emittenten-LEI, niemand widerspricht.
Gemessen werden die Verfahren des Pilots, je ISIN einmal (über alle Pilotfonds):

- ``wikidata``: ISIN → Wikidata → LEI (nur wenn Wikidata genau einen LEI nennt),
- ``register``: Registernummer Wikidata ↔ GLEIF (D-046),
- ``name``: GLEIF-Namenssuche mit Sitzland (D-046, bisher nicht freigegeben).

Unabhängig im Sinne von D-046 sind für ``register`` und ``name`` nur ISIN aus Testfonds, die
in keinem Entwicklungsfonds vorkommen (an deren Fehlern wurden die Regeln angepasst).
Wikidata wurde nie angepasst; dort zählen alle ISIN.

Diese Messung ändert nichts an der Freigabe in ``entity_matching.py``. Ob die N-PORT-Referenz
die Wikidata-Referenz für die Freigabe ersetzt, ist ein eigener Schritt.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from transparenz.services.entity_matching import DEVELOPMENT_FUNDS, RULE_VERSION, evaluate
from transparenz.services.security_master import open_readonly

METHODS = ("wikidata", "register", "name")
# Region nach Sitzland des Referenz-Emittenten laut GLEIF (für die Freigabe je Region, D-046).
_EUROPE = frozenset({
    "AT", "BE", "BG", "CH", "CY", "CZ", "DE", "DK", "EE", "ES", "FI", "FR", "GB", "GG", "GI",
    "GR", "HR", "HU", "IE", "IM", "IS", "IT", "JE", "LI", "LT", "LU", "LV", "MC", "MT", "NL",
    "NO", "PL", "PT", "RO", "SE", "SI", "SK"})
_ASIA_PACIFIC = frozenset({"AU", "CN", "HK", "ID", "IN", "JP", "KR", "MO", "MY", "NZ", "PH",
                           "SG", "TH", "TW", "VN"})
_NORTH_AMERICA = {"US", "CA"}


def region_of(country: str | None) -> str:
    if country in _NORTH_AMERICA:
        return "north_america"
    if country in _EUROPE:
        return "europe"
    if country in _ASIA_PACIFIC:
        return "asia_pacific"
    return "other" if country else "unknown"


def pilot_proposals(pilot_dir: Path) -> list[dict[str, Any]]:
    """Ergebnisse der Pilotverfahren je Fonds und ISIN aus den Pilotberichten (JSON)."""
    found: list[dict[str, Any]] = []
    for report in sorted(pilot_dir.glob("*.json")):
        if any(report.name.endswith(s) for s in ("_gleif.json", "_wikidata_isin.json",
                                                  "_wikidata_profile.json",
                                                  "_review_queue.json")):
            continue
        data = json.loads(report.read_bytes())
        if "positions" not in data or "fund" not in data:
            continue
        fund = data["fund"].get("fund_name")
        wikidata: dict[str, set[str]] = defaultdict(set)
        side = report.with_name(report.stem + "_wikidata_isin.json")
        if side.is_file():
            for row in json.loads(side.read_bytes()).get("rows", []):
                if row.get("isin") and row.get("lei"):
                    wikidata[row["isin"].upper()].add(row["lei"].upper())
        for position in data["positions"]:
            isin = (position.get("isin") or "").upper()
            if not position.get("isin_valid"):
                continue
            match = position.get("auto_match") or {}
            leis = wikidata.get(isin, set())
            found.append({"fund": fund, "isin": isin, "method": "wikidata",
                          "lei": next(iter(leis)) if len(leis) == 1 else None})
            for method in ("register", "name"):
                result = match.get(method) or {}
                found.append({"fund": fund, "isin": isin, "method": method,
                              "lei": result.get("lei") if result.get("status") == "accepted"
                              else None})
    return found


def compare_with_reference(db_path: Path, proposals: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Präzision und Abdeckung je Verfahren gegen die N-PORT-Referenz, gesamt und je Region."""
    proposals = list(proposals)
    dev_isins = {p["isin"] for p in proposals if p["fund"] in DEVELOPMENT_FUNDS}
    isins = sorted({p["isin"] for p in proposals})
    conn = open_readonly(db_path)
    try:
        reference: dict[str, tuple[str | None, str, str | None]] = {}
        for i in range(0, len(isins), 500):
            chunk = isins[i:i + 500]
            marks = ", ".join("?" * len(chunk))
            for isin, lei, status, country in conn.execute(
                    f"SELECT isin, lei, status, gleif_country FROM securities "
                    f"WHERE isin IN ({marks})", chunk):
                reference[isin] = (lei, status, country)
        info = {k: json.loads(v) for k, v in conn.execute("SELECT key, value FROM build_info")}
    finally:
        conn.close()

    status_counts: dict[str, int] = defaultdict(int)
    for isin in isins:
        status_counts[reference.get(isin, (None, "not_held_by_us_funds", None))[1]] += 1

    results: dict[str, Any] = {}
    for method in METHODS:
        # Je ISIN ein Fall; widersprechen sich zwei Fonds im selben Verfahren, gilt der Fall
        # als unbeantwortet (kommt praktisch nicht vor, wird aber gezählt).
        by_isin: dict[str, set[str | None]] = defaultdict(set)
        independent: dict[str, bool] = {}
        for p in (p for p in proposals if p["method"] == method):
            by_isin[p["isin"]].add(p["lei"])
            ok = method == "wikidata" or (p["fund"] not in DEVELOPMENT_FUNDS
                                          and p["isin"] not in dev_isins)
            independent[p["isin"]] = independent.get(p["isin"], False) or ok
        cases: dict[str, list[dict[str, Any]]] = defaultdict(list)
        split = 0
        for isin, answers in by_isin.items():
            ref = reference.get(isin)
            if ref is None or ref[1] != "confirmed" or not independent[isin]:
                continue
            given = {a for a in answers if a}
            split += len(given) > 1
            case = {"isin": isin, "reference_lei": ref[0],
                    "predicted_lei": next(iter(given)) if len(given) == 1 else None}
            cases["all"].append(case)
            cases[region_of(ref[2])].append(case)
        measured = {}
        for scope, rows in sorted(cases.items()):
            result = evaluate(rows)
            result["meets_release_rule"] = result.pop("released")
            measured[scope] = result
        results[method] = {"cases": measured, "split_answers": split}
    return {
        "reference": {"security_master_rule_version": info.get("rule_version"),
                      "built_at": info.get("built_at"),
                      "pilot_isins": len(isins), "status_of_pilot_isins": dict(status_counts)},
        "matching_rule_version": RULE_VERSION,
        "development_funds": len(DEVELOPMENT_FUNDS),
        "methods": results,
        "notes": [
            "Referenz: N-PORT-Konsens (D-056). Für «register» und «name» nur ISIN aus "
            "Testfonds, die in keinem Entwicklungsfonds vorkommen (D-046).",
            "«meets_release_rule» zeigt nur, ob die Messung die Schwelle erreicht; die Freigabe "
            "in entity_matching.py wird dadurch nicht geändert.",
            "Die Referenz enthält nur Papiere, die US-registrierte Fonds halten.",
        ],
    }
