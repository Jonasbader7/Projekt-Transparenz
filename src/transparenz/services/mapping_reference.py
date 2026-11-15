"""Referenzfälle der Zuordnung, Präzisionsmessung je Verfahren und Liste der Abweichungen (D-046).
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from transparenz.services.entity_matching import DEVELOPMENT_FUNDS, RULE_VERSION, evaluate

REFERENCE_FILE = "mapping_reference_cases.json"

SEARCH_CACHE_FILE = "gleif_search_cache.json"


def reference_cases(rows: list[dict[str, Any]], fund_name: str) -> dict[str, dict[str, Any]]:
    """Referenzfälle für die Messung: Positionen, deren LEI über einen vom Namensverfahren
    unabhängigen Weg feststeht (Wikidata-Kennung widerspruchsfrei oder menschlicher Entscheid).

    Fälle, die erst durch die Namenssuche entschieden wurden, sind nie Referenz (zirkulär).
    """
    out = {}
    for row in rows:
        source = {"consistent": "isin_wikidata", "consistent_lapsed": "isin_wikidata",
                  "confirmed_by_decision": "decision"}.get(row["mapping_confidence"])
        if not source:
            continue
        company = row.get("company") or {}
        auto = row.get("auto_match") or {}
        # Je Fonds und Position: Positionsname und Emittentenland sind je Fonds eigene Eingaben.
        out[f"{fund_name}|{row['isin']}"] = {
            "isin": row["isin"], "position_name": row["name"], "fund": fund_name,
            "reference_lei": company.get("lei"), "reference_source": source,
            "name": auto.get("name"), "register": auto.get("register")}
    return out


def evaluate_methods(store: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Präzision und Abdeckung je automatischem Verfahren.

    Entscheidend für die Freigabe sind nur **unabhängige** Referenzfälle: aus Fonds, die nicht
    zur Entwicklung der Regeln dienten, und ohne ISINs, die in einem Entwicklungsfonds
    vorkommen. Die Entwicklungsfälle werden getrennt gezeigt (``development``); sie sind zu
    optimistisch, weil die Regeln an ihren Fehlern angepasst wurden.
    """
    dev_isins = {c["isin"] for c in store.values() if c["fund"] in DEVELOPMENT_FUNDS}
    result: dict[str, Any] = {
        "rule_version": RULE_VERSION, "development_funds": sorted(DEVELOPMENT_FUNDS),
        "reference_sources": dict(Counter(c["reference_source"] for c in store.values()))}
    for method in ("name", "register"):
        cases = [{"isin": c["isin"], "position_name": c["position_name"], "fund": c["fund"],
                  "reference_lei": c["reference_lei"],
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
        funds = sorted({c["fund"] for c in independent})
        development = evaluate([c for c in cases if c["fund"] in DEVELOPMENT_FUNDS])
        result[method] = {**evaluate(independent), "funds": funds,
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
            for lei, origin in ((wrong["reference_lei"], "Referenz (Wikidata-Kennung)"),
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
