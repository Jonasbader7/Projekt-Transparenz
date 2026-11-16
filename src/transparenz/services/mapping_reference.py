"""Referenzfälle der Zuordnung, Präzisionsmessung je Verfahren und Liste der Abweichungen.

Referenz (D-046, ab D-058): Ein menschlicher Entscheid geht vor. Sonst gilt mit Wertpapierstamm
der N-PORT-Konsens (``security_master``, D-056) als Referenz; die Wikidata-Kennung ist dann
keine Referenz mehr, weil sie an diesem Konsens gemessen selbst nur rund 97 % genau ist
(D-057). Ohne Wertpapierstamm bleibt die frühere Referenz (Wikidata-Kennung oder Entscheid).
Freigabe der Namenssuche je Region (``released_regions``).
"""
from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping
from typing import Any

from transparenz.services.entity_matching import (
    DEVELOPMENT_FUNDS,
    RULE_VERSION,
    evaluate,
    position_region,
)

REFERENCE_FILE = "mapping_reference_cases.json"
# Eigener Speicher für die N-PORT-Referenz: nie mit Fällen der früheren Referenz mischen.
REFERENCE_FILE_NPORT = "mapping_reference_cases_nport.json"

SEARCH_CACHE_FILE = "gleif_search_cache.json"

REFERENCE_LABELS = {"isin_wikidata": "Referenz (Wikidata-Kennung)",
                    "decision": "Referenz (menschlicher Entscheid)",
                    "nport_consensus": "Referenz (N-PORT-Konsens)"}


def reference_cases(rows: list[dict[str, Any]], fund_name: str,
                    nport_reference: Mapping[str, str] | None = None
                    ) -> dict[str, dict[str, Any]]:
    """Referenzfälle für die Messung: Positionen, deren LEI über einen vom Namensverfahren
    unabhängigen Weg feststeht.

    Ohne ``nport_reference``: Wikidata-Kennung widerspruchsfrei oder menschlicher Entscheid.
    Mit ``nport_reference`` (ISIN → bestätigter LEI): menschlicher Entscheid, sonst N-PORT.
    Fälle, die erst durch die Namenssuche entschieden wurden, sind nie Referenz (zirkulär).
    """
    out = {}
    for row in rows:
        company = row.get("company") or {}
        if row["mapping_confidence"] == "confirmed_by_decision":
            source, lei = "decision", company.get("lei")
        elif nport_reference is not None:
            lei = nport_reference.get(row["isin"])
            source = "nport_consensus" if lei else None
        else:
            source = {"consistent": "isin_wikidata",
                      "consistent_lapsed": "isin_wikidata"}.get(row["mapping_confidence"])
            lei = company.get("lei")
        if not source:
            continue
        auto = row.get("auto_match") or {}
        # Je Fonds und Position: Positionsname und Emittentenland sind je Fonds eigene Eingaben.
        out[f"{fund_name}|{row['isin']}"] = {
            "isin": row["isin"], "position_name": row["name"], "fund": fund_name,
            "reference_lei": lei, "reference_source": source,
            "region": position_region(row.get("issuer_country"), row["isin"]),
            "name": auto.get("name"), "register": auto.get("register")}
    return out


def evaluate_methods(store: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Präzision und Abdeckung je automatischem Verfahren, gesamt und je Region.

    Entscheidend für die Freigabe sind nur **unabhängige** Referenzfälle: aus Fonds, die nicht
    zur Entwicklung der Regeln dienten, und ohne ISINs, die in einem Entwicklungsfonds
    vorkommen. Die Entwicklungsfälle werden getrennt gezeigt (``development``); sie sind zu
    optimistisch, weil die Regeln an ihren Fehlern angepasst wurden. Die Namenssuche wirkt nur
    in den Regionen, deren unabhängige Fälle die Freigaberegel erfüllen (``released_regions``).
    """
    dev_isins = {c["isin"] for c in store.values() if c["fund"] in DEVELOPMENT_FUNDS}
    result: dict[str, Any] = {
        "rule_version": RULE_VERSION, "development_funds": sorted(DEVELOPMENT_FUNDS),
        "reference_sources": dict(Counter(c["reference_source"] for c in store.values()))}
    for method in ("name", "register"):
        cases = [{"isin": c["isin"], "position_name": c["position_name"], "fund": c["fund"],
                  "reference_lei": c["reference_lei"],
                  "reference_source": c["reference_source"],
                  "region": c.get("region") or position_region(None, c["isin"]),
                  "predicted_lei": (c.get(method) or {}).get("lei")
                  if (c.get(method) or {}).get("status") == "accepted" else None}
                 for c in store.values() if c.get("reference_lei")
                 and (c.get(method) or {}).get("status") != "not_searched"]
        # Dieselbe ISIN in mehreren Testfonds zählt nur einmal (erster Fonds in Namensfolge):
        # sonst würden gleiche Fälle die Fallzahl künstlich erhöhen.
        independent, counted = [], set()
        for c in sorted(cases, key=lambda item: (item["fund"], item["isin"])):
            if (c["fund"] not in DEVELOPMENT_FUNDS and c["isin"] not in dev_isins
                    and c["isin"] not in counted):
                counted.add(c["isin"])
                independent.append(c)
        by_region: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for c in independent:
            by_region[c["region"]].append(c)
        regions = {region: {k: v for k, v in evaluate(rows).items()
                            if k not in ("release_rule", "wrong_cases")}
                   for region, rows in sorted(by_region.items())}
        funds = sorted({c["fund"] for c in independent})
        development = evaluate([c for c in cases if c["fund"] in DEVELOPMENT_FUNDS])
        result[method] = {**evaluate(independent), "funds": funds,
                          "regions": regions,
                          "released_regions": sorted(r for r, e in regions.items()
                                                     if e["released"]),
                          "development": {k: v for k, v in development.items()
                                          if k != "release_rule"}}
    result["reference_sources"] = dict(Counter(c["reference_source"] for c in store.values()))
    return result


DISPUTES_FILE = "mapping_disputes.json"


def dispute_queue(evaluation: dict[str, Any],
                  entities: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Fragen zu Fällen, in denen Referenz und automatisches Verfahren verschiedene LEIs nennen.

    Gleiches Format wie die offene Frageliste (``review_mapping.py --queue``). Wer hier
    antwortet, korrigiert die Referenz: Der Entscheid wird beim nächsten Lauf zum Referenzfall
    (Quelle «decision»), und die Messung rechnet sich neu. Wir entscheiden diese Fälle nie selbst.
    """
    cases: dict[str, dict[str, Any]] = {}
    for method in ("name", "register"):
        block = evaluation.get(method) or {}
        for wrong in [*block.get("wrong_cases", []),
                      *(block.get("development") or {}).get("wrong_cases", [])]:
            case = cases.setdefault(wrong["isin"], {
                "isin": wrong["isin"], "position_name": wrong["position_name"],
                "fund": wrong["fund"], "weight_percent": None, "signal": "reference_dispute",
                "wikidata_ids": [], "wikidata_names": [], "candidates": []})
            reference = REFERENCE_LABELS.get(wrong.get("reference_source") or "isin_wikidata",
                                             "Referenz")
            for lei, origin in ((wrong["reference_lei"], reference),
                                (wrong["predicted_lei"], f"Verfahren «{method}»")):
                if lei in {c["lei"] for c in case["candidates"]}:
                    continue
                entity = entities.get(lei) or {}
                case["candidates"].append({
                    "lei": lei, "origin": origin, "legal_name": entity.get("legal_name"),
                    "registration_status": entity.get("registration_status"),
                    "other_names": [n if isinstance(n, str) else n.get("name")
                                    for n in entity.get("other_names") or []]})
    return sorted(cases.values(), key=lambda c: (c["fund"], c["position_name"]))
