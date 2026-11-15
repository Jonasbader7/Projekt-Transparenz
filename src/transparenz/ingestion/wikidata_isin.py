"""Wikidata: exakter ISIN-Abgleich und Unternehmensprofile (CC0). Ergebnisse bleiben unbestätigte
Hinweise.
"""
from __future__ import annotations

import re
import time
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

import httpx

from transparenz.entities.identifiers import is_valid_isin

WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"

WIKIDATA_CHUNK = 200  # ISINs je Abfrage; hält die Antwortzeit im Sekundenbereich

WIKIDATA_MIN_INTERVAL = 2.0


# --------------------------------------------------------------------------- Wikidata


def fetch_wikidata_isins(isins: list[str], user_agent: str, client: httpx.Client | None = None,
                         sleep: Any = time.sleep) -> dict[str, Any]:
    """Fragt Wikidata nach Einträgen, die exakt eine dieser ISINs tragen (P946), samt LEI (P1278).

    Nur gültige ISINs gehen in die Abfrage. Ein Fehlerstatus bricht ab; es gibt keine
    stillschweigend unvollständige Antwort.
    """
    wanted = sorted({i.upper() for i in isins if is_valid_isin(i)})
    own = client is None
    client = client or httpx.Client(timeout=90)
    headers = {"User-Agent": user_agent, "Accept": "application/sparql-results+json"}
    result: dict[str, Any] = {
        "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "source": "Wikidata Query Service (strukturierte Daten, CC0 1.0)",
        "isins_queried": wanted, "rows": [],
    }
    try:
        for start in range(0, len(wanted), WIKIDATA_CHUNK):
            if start:
                sleep(WIKIDATA_MIN_INTERVAL)
            values = " ".join(f'"{isin}"' for isin in wanted[start:start + WIKIDATA_CHUNK])
            query = (
                f"SELECT ?isin ?item ?itemLabel ?lei WHERE {{ VALUES ?isin {{ {values} }} "
                "?item wdt:P946 ?isin . OPTIONAL { ?item wdt:P1278 ?lei } "
                'SERVICE wikibase:label { bd:serviceParam wikibase:language "en,de". } }')
            response = client.post(WIKIDATA_SPARQL, data={"query": query}, headers=headers)
            response.raise_for_status()
            for binding in response.json()["results"]["bindings"]:
                result["rows"].append({
                    "isin": binding["isin"]["value"].upper(),
                    "wikidata_id": binding["item"]["value"].rsplit("/", 1)[-1],
                    "name": (binding.get("itemLabel") or {}).get("value"),
                    "lei": (binding.get("lei") or {}).get("value"),
                })
    finally:
        if own:
            client.close()
    return result


def wikidata_candidates(lookup: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Bringt die Abfrageantwort in dieselbe Form wie die lokalen Wertpapierkandidaten."""
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for row in (lookup or {}).get("rows", []):
        entry = grouped.setdefault((row["isin"], row["wikidata_id"]), {
            "isin": row["isin"], "wikidata_id": row["wikidata_id"],
            "name": row.get("name") or row["wikidata_id"], "claims": {"P1278": []},
            "source_key": "wikidata_isin_lookup",
            "mapping_status": "unverified_company_level_claim"})
        if row.get("lei") and row["lei"] not in entry["claims"]["P1278"]:
            entry["claims"]["P1278"].append(row["lei"])
    return list(grouped.values())


PROFILE_PROPERTIES = ("P452", "P31")  # Branche, «ist ein(e)»


def fetch_wikidata_profiles(items: list[str], user_agent: str,
                            client: httpx.Client | None = None,
                            sleep: Any = time.sleep) -> dict[str, Any]:
    """Branche (P452), Art (P31) und Registernummern je Wikidata-Eintrag (CC0).

    Die Branche dient nur der Einordnung von Besitzketten (Finanzinstitut ja/nein), die
    Registernummern nur dem Abgleich mit GLEIF über dieselbe Nummer (Verfahren «register»).
    """
    wanted = sorted({i for i in items if re.fullmatch(r"Q\d+", i or "")})
    own = client is None
    client = client or httpx.Client(timeout=90)
    headers = {"User-Agent": user_agent, "Accept": "application/sparql-results+json"}
    props = " ".join(f"wdt:{p}" for p in (*PROFILE_PROPERTIES, *REGISTER_PROPS))
    result: dict[str, Any] = {
        "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "source": "Wikidata Query Service (strukturierte Daten, CC0 1.0)",
        "items_queried": wanted, "rows": []}
    try:
        for start in range(0, len(wanted), WIKIDATA_CHUNK):
            if start:
                sleep(WIKIDATA_MIN_INTERVAL)
            values = " ".join(f"wd:{q}" for q in wanted[start:start + WIKIDATA_CHUNK])
            query = (f"SELECT ?item ?prop ?value ?valueLabel WHERE {{ VALUES ?item {{ {values} }} "
                     f"VALUES ?prop {{ {props} }} ?item ?prop ?value . "
                     'SERVICE wikibase:label { bd:serviceParam wikibase:language "en". } }')
            response = client.post(WIKIDATA_SPARQL, data={"query": query}, headers=headers)
            response.raise_for_status()
            for binding in response.json()["results"]["bindings"]:
                value = binding["value"]["value"]
                result["rows"].append({
                    "item": binding["item"]["value"].rsplit("/", 1)[-1],
                    "prop": binding["prop"]["value"].rsplit("/", 1)[-1],
                    "value": value.rsplit("/", 1)[-1] if value.startswith("http") else value,
                    "label": (binding.get("valueLabel") or {}).get("value")})
    finally:
        if own:
            client.close()
    return result


REGISTER_PROPS = ("P1320", "P3549", "P3548", "P3225", "P5687")


def index_profiles(profiles: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    """Wikidata-Eintrag → {"industries": [...], "register": {Eigenschaft: [Werte]}}."""
    out: dict[str, dict[str, Any]] = defaultdict(lambda: {"industries": [], "register": {}})
    for row in (profiles or {}).get("rows", []):
        entry = out[row["item"]]
        if row["prop"] in PROFILE_PROPERTIES:
            label = row.get("label") or row["value"]
            if label not in entry["industries"]:
                entry["industries"].append(label)
        elif row["prop"] in REGISTER_PROPS:
            values = entry["register"].setdefault(row["prop"], [])
            if row["value"] not in values:
                values.append(row["value"])
    return dict(out)
