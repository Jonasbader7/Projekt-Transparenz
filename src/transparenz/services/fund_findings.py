"""Befunde je Unternehmen aus GEM-Anlagen (Kohle, fossile Expansion) und Schwellenwert-
Empfindlichkeit. Wendet nur übergebene Regeln an.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from transparenz.ingestion.gem import GEM_STAKES
from transparenz.services.ownership import CUSTODY, OWN_ACCOUNT, RELATIONSHIP_TYPES

SENSITIVITY_THRESHOLDS = (0.0, 5.0, 10.0, 20.0, 50.0)

# Kategorie je Anlagenart: dieselben Schlüssel wie die Kategorien in criteria.toml.
COAL_CATEGORIES = {"coal_mine": "kohlefoerderung", "coal_plant": "kohleverstromung"}

GEM_PHASES = {"announced": "ankuendigung", "proposed": "ankuendigung",
              "pre-permit": "genehmigung", "permitted": "genehmigung",
              "pre-construction": "bau", "construction": "bau"}

GEM_CAPACITY_TYPES = {"coal_mine": "foerderung", "coal_plant": "kraftwerke",
                      "gas_plant": "kraftwerke", "lng_terminal": "lng",
                      "gas_pipeline": "transport", "oil_pipeline": "transport"}


def _unit_key(asset: dict[str, Any]) -> tuple[Any, ...]:
    return (asset["kind"], asset.get("unit_id") or asset.get("project"))


def own_share_by_unit(assets: list[dict[str, Any]]) -> dict[tuple[Any, ...], float | None]:
    """Durchgerechneter Eigenanteil je Einheit: Summe der bekannten Anteile über alle Ketten
    auf eigene Rechnung (höchstens 100 %); ``None``, wenn nur unbekannte Anteile vorliegen."""
    shares: dict[tuple[Any, ...], float | None] = {}
    for asset in assets:
        if asset.get("relationship", OWN_ACCOUNT) != OWN_ACCOUNT:
            continue
        key = _unit_key(asset)
        if asset["share"] is None:
            shares.setdefault(key, None)
        else:
            shares[key] = min(100.0, (shares.get(key) or 0.0) + asset["share"])
    return shares


def _finding(assets: list[dict[str, Any]], min_share: float,
             effects: dict[str, str] | None, category_of: Any) -> dict[str, Any]:
    """Gemeinsamer Kern von Kohle und Expansion: Konflikt nur bei Eigentum auf eigene Rechnung
    mit belegtem Anteil ab ``min_share`` in einer Kategorie mit Wirkung «conflict»."""
    effects = effects or {}
    by_stake: dict[str, int] = {}
    conflict_assets = []
    categories: Counter[str] = Counter()
    for asset in assets:
        by_stake[asset["stake"]] = by_stake.get(asset["stake"], 0) + 1
        category = category_of(asset)
        categories[category] += 1
        if effects.get(category, "conflict") == "conflict":
            conflict_assets.append(asset)
    own = own_share_by_unit(conflict_assets)
    known = [s for s in own.values() if s is not None]
    max_own = max(known) if known else None
    involved = [s for s in by_stake if s != CUSTODY]
    return {
        "strongest": min(involved, key=GEM_STAKES.index) if involved else None,
        "by_stake": by_stake, "categories": dict(categories),
        "relationships": sorted({a.get("relationship", OWN_ACCOUNT) for a in assets},
                                key=RELATIONSHIP_TYPES.index),
        "own_units": len(own), "own_units_unknown_share": sum(1 for s in own.values()
                                                               if s is None),
        "max_own_share": max_own,
        "conflict": max_own is not None and max_own > 0 and max_own >= min_share,
        "old_conflict": any(a.get("old_stake", a["stake"]) in ("control", "significant", "small")
                            for a in conflict_assets),
    }


def coal_finding(assets: list[dict[str, Any]] | None, min_share: float = 0.0,
                 effects: dict[str, str] | None = None) -> dict[str, Any] | None:
    """Aktive Kohleanlagen (in Betrieb oder im Ausbau) je Beziehungstyp; Konfliktregel D-045."""
    if assets is None:
        return None
    active = [a for a in assets if a["category"] == "coal"
              and a["status_group"] in ("operating", "expansion")]
    if not [a for a in active if a["stake"] != CUSTODY]:
        return {"has_active_coal": False, "custody_only": bool(active)}
    core = _finding(active, min_share, effects, lambda a: COAL_CATEGORIES[a["kind"]])
    by_status: dict[str, dict[str, int]] = {}
    for a in active:
        by_status.setdefault(a["stake"], {"operating": 0, "expansion": 0})[a["status_group"]] += 1
    return {"has_active_coal": True, **core, "by_stake": by_status,
            "expansion": any(a["status_group"] == "expansion" and a["stake"] != CUSTODY
                             for a in active)}


def expansion_finding(assets: list[dict[str, Any]], min_share: float = 0.0,
                      effects: dict[str, str] | None = None) -> dict[str, Any]:
    """Neue fossile Kapazität laut GEM (angekündigt, in Genehmigung oder im Bau).

    Phase, Art der Kapazität und Beziehungstyp bleiben getrennt. Bestehende Anlagen in Betrieb
    zählen hier nicht. Neue Öl- und Gasfelder fehlen: GEM nennt deren Eigentümer nur mit Namen.
    Eigenbedarf und Notstrom (z. B. Generatoren von Rechenzentren) werden mitgezählt, aber
    ausgewiesen (offene Frage im Kriterienmodell).
    """
    new = [a for a in assets if a["status_group"] == "expansion" and a["stake"] != CUSTODY]
    if not new:
        return {"has_expansion": False}
    phases: Counter[str] = Counter()
    types: Counter[str] = Counter()
    for asset in new:
        phases[GEM_PHASES.get((asset.get("status") or "").strip().lower(), "ankuendigung")] += 1
        types[GEM_CAPACITY_TYPES[asset["kind"]]] += 1
    core = _finding(new, min_share, effects, lambda a: GEM_CAPACITY_TYPES[a["kind"]])
    own_new = [a for a in new if a.get("relationship", OWN_ACCOUNT) == OWN_ACCOUNT]
    captive = [a for a in own_new if (a.get("details") or {}).get("backup")
               or (a.get("details") or {}).get("captive_use")]
    return {"has_expansion": True, **core, "phases": dict(phases),
            "capacity_types": dict(types), "own_captive_or_backup": len(captive),
            "own_units_total": len({_unit_key(a) for a in own_new})}


def sensitivity(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    """Wie viele Positionen wären bei einer Beteiligungsschwelle von x % ein Konflikt?"""
    out = []
    for threshold in SENSITIVITY_THRESHOLDS:
        hits = [r for r in rows if (r.get(key) or {}).get("max_own_share") is not None
                and r[key]["max_own_share"] > 0 and r[key]["max_own_share"] >= threshold]
        out.append({"threshold": threshold, "positions": len(hits),
                    "weight_percent": round(sum(r["weight_percent"] or 0 for r in hits), 2)})
    return out
