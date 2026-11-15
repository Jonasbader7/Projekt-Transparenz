"""GLEIF: Namenssuche, LEI-Datensätze, Mutterbeziehungen (API) und die lokale Beziehungsdatei
(Golden Copy, Level 2).
"""
from __future__ import annotations

import csv
import io
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from transparenz.entities.identifiers import is_valid_lei
from transparenz.services.entity_matching import GleifCandidate

RR_KINDS = {"IS_DIRECTLY_CONSOLIDATED_BY": "direct-parent",
            "IS_ULTIMATELY_CONSOLIDATED_BY": "ultimate-parent"}

GLEIF_API = "https://api.gleif.org/api/v1"

JSONAPI = "application/vnd.api+json"

GLEIF_MIN_INTERVAL = 1.1  # Sekunden; GLEIF erlaubt 60 Anfragen pro Minute

PARENT_KINDS = ("direct-parent", "ultimate-parent")


# ------------------------------------------------------------------------------ GLEIF
GLEIF_SEARCH_PAGE = 100


def fetch_gleif_search(queries: list[str], cache: dict[str, Any], user_agent: str,
                       field: str = "entity.names", client: httpx.Client | None = None,
                       sleep: Any = time.sleep) -> dict[str, Any]:
    """GLEIF-Suche (CC0) je Suchtext; Ergebnisse landen im ``cache`` (Suchtext → Treffer).

    ``field`` = «entity.names» (Namenssuche) oder «entity.registeredAs» (Registernummer).
    Mehr Treffer als eine Seite fasst, gilt als «zu viele» (nie stillschweigend gekürzt).
    """
    own = client is None
    client = client or httpx.Client(timeout=30)
    headers = {"User-Agent": user_agent, "Accept": JSONAPI}
    todo = [q for q in dict.fromkeys(queries) if q and f"{field}:{q}" not in cache]
    try:
        for number, query in enumerate(todo):
            if number:
                sleep(GLEIF_MIN_INTERVAL)
            response = client.get(f"{GLEIF_API}/lei-records", headers=headers, params={
                f"filter[{field}]": query, "page[size]": str(GLEIF_SEARCH_PAGE)})
            response.raise_for_status()
            data = response.json()
            total = ((data.get("meta") or {}).get("pagination") or {}).get("total") or 0
            cache[f"{field}:{query}"] = {
                "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "total": total, "truncated": total > GLEIF_SEARCH_PAGE,
                "records": [GleifCandidate.from_record(r).to_dict()
                            for r in data.get("data", [])]}
    finally:
        if own:
            client.close()
    return cache


def gleif_entry(candidate: dict[str, Any]) -> dict[str, Any]:
    """GLEIF-Suchtreffer in derselben Form wie die Rechtsnamen aus ``fetch_gleif``."""
    return {"legal_name": candidate.get("legal_name"),
            "other_names": [{"name": n, "type": None} for n in candidate.get("other_names") or []],
            "entity_status": candidate.get("entity_status"),
            "registration_status": candidate.get("registration_status"),
            "country": candidate.get("legal_country")}


def fetch_gleif(leis_names: list[str], leis_parents: list[str], user_agent: str,
                client: httpx.Client | None = None,
                sleep: Any = time.sleep) -> dict[str, Any]:
    """Lädt Rechtsnamen (``leis_names``) und gemeldete Mütter (``leis_parents``) von GLEIF.

    HTTP 404 bei einer Mutterbeziehung heisst «keine Beziehung gemeldet» und ist kein Fehler.
    Jeder andere Fehlerstatus bricht ab (keine stillschweigend unvollständige Antwort).
    """
    own = client is None
    client = client or httpx.Client(timeout=30)
    headers = {"User-Agent": user_agent, "Accept": JSONAPI}
    result: dict[str, Any] = {
        "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "source": "GLEIF API (CC0 1.0)", "names": {}, "names_checked": sorted(leis_names),
        "parents": [],
    }
    first = True

    def get(url: str, params: dict[str, str] | None = None) -> httpx.Response:
        nonlocal first
        if not first:
            sleep(GLEIF_MIN_INTERVAL)
        first = False
        return client.get(url, params=params, headers=headers)

    try:
        for start in range(0, len(leis_names), 100):
            chunk = leis_names[start:start + 100]
            response = get(f"{GLEIF_API}/lei-records",
                           {"filter[lei]": ",".join(chunk), "page[size]": "100"})
            response.raise_for_status()
            for record in response.json().get("data", []):
                attributes = record.get("attributes", {})
                entity = attributes.get("entity", {})
                result["names"][record.get("id")] = {
                    "legal_name": (entity.get("legalName") or {}).get("name"),
                    "other_names": [
                        {"name": item.get("name"), "type": item.get("type")}
                        for item in [*(entity.get("otherNames") or []),
                                     *(entity.get("transliteratedOtherNames") or [])]
                        if item.get("name")],
                    "entity_status": entity.get("status"),
                    "registration_status": (attributes.get("registration") or {}).get("status"),
                    "country": (entity.get("legalAddress") or {}).get("country"),
                }
        for lei in leis_parents:
            for kind in PARENT_KINDS:
                response = get(f"{GLEIF_API}/lei-records/{lei}/{kind}-relationship")
                if response.status_code == 404:
                    continue
                response.raise_for_status()
                result["parents"].append(parent_link(lei, kind, response.json().get("data") or {}))
    finally:
        if own:
            client.close()
    return result


def parent_link(child_lei: str, kind: str, record: dict[str, Any]) -> dict[str, Any]:
    """Übersetzt einen GLEIF-Beziehungsdatensatz; «verified» nach derselben Regel wie D-026."""
    attributes = record.get("attributes") or {}
    relationship = attributes.get("relationship") or {}
    registration = attributes.get("registration") or {}
    parent = str((relationship.get("endNode") or {}).get("id") or "").upper()
    period = next((p for p in relationship.get("periods") or []
                   if p.get("type") == "RELATIONSHIP_PERIOD"), {})
    return {
        "child_lei": child_lei, "kind": kind,
        "parent_lei": parent if is_valid_lei(parent) else None,
        "relationship_status": relationship.get("status"),
        "registration_status": registration.get("status"),
        "corroboration_level": registration.get("corroborationLevel"),
        "verified": (relationship.get("status") == "ACTIVE"
                     and registration.get("status") == "PUBLISHED"
                     and registration.get("corroborationLevel") == "FULLY_CORROBORATED"),
        "relationship_start": _date(period.get("startDate")),
        "relationship_end": _date(period.get("endDate")),
        "registration_initial_date": _date(registration.get("initialRegistrationDate")),
        "registration_last_update": _date(registration.get("lastUpdateDate")),
    }


def _date(value: str | None) -> str | None:
    """Kalenderdatum aus einem ISO-Zeitstempel, wie GLEIF ihn meldet (ohne Zeitzonen-Umrechnung)."""
    return value[:10] if value and len(value) >= 10 and value[4] == "-" else None


# ------------------------------------------------------------- EU-Emissionshandel


def require_columns(reader: csv.DictReader, required: set[str], label: str) -> None:
    missing = required - set(reader.fieldnames or [])
    if missing:
        raise ValueError(f"{label}: Spalten fehlen: {sorted(missing)}")


def load_group_links(rr_zip: Path, child_leis: set[str],
                     parent_leis: set[str]) -> list[dict[str, Any]]:
    """Mutterbeziehungen aus der GLEIF-Beziehungsdatei (Golden Copy, Level 2).

    Behalten werden nur Beziehungen von einem Rechtsträger mit Beleg zu einem Rechtsträger
    aus dem Fonds. «verified» nach derselben Regel wie bei der API (D-026).
    """
    links: list[dict[str, Any]] = []
    with zipfile.ZipFile(rr_zip) as archive:
        members = [n for n in archive.namelist() if n.lower().endswith(".csv")]
        if len(members) != 1:
            raise ValueError(
                f"{rr_zip.name}: genau eine CSV-Datei erwartet, {len(members)} gefunden.")
        with archive.open(members[0]) as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
            require_columns(reader, {
                "Relationship.StartNode.NodeID", "Relationship.StartNode.NodeIDType",
                "Relationship.EndNode.NodeID", "Relationship.EndNode.NodeIDType",
                "Relationship.RelationshipType", "Relationship.RelationshipStatus",
                "Registration.RegistrationStatus", "Registration.ValidationSources"},
                rr_zip.name)
            for row in reader:
                kind = RR_KINDS.get(row["Relationship.RelationshipType"])
                if (not kind or row["Relationship.StartNode.NodeIDType"] != "LEI"
                        or row["Relationship.EndNode.NodeIDType"] != "LEI"):
                    continue
                child = row["Relationship.StartNode.NodeID"].upper()
                parent = row["Relationship.EndNode.NodeID"].upper()
                if child not in child_leis or parent not in parent_leis or child == parent:
                    continue
                relationship_status = row["Relationship.RelationshipStatus"]
                registration_status = row["Registration.RegistrationStatus"]
                corroboration = row["Registration.ValidationSources"]
                period = next((i for i in range(1, 6) if row.get(
                    f"Relationship.Period.{i}.periodType") == "RELATIONSHIP_PERIOD"), None)
                links.append({
                    "child_lei": child, "kind": kind, "parent_lei": parent,
                    "relationship_status": relationship_status,
                    "registration_status": registration_status,
                    "corroboration_level": corroboration,
                    "verified": (relationship_status == "ACTIVE"
                                 and registration_status == "PUBLISHED"
                                 and corroboration == "FULLY_CORROBORATED"),
                    "relationship_start": _date(row.get(
                        f"Relationship.Period.{period}.startDate")) if period else None,
                    "relationship_end": _date(row.get(
                        f"Relationship.Period.{period}.endDate")) if period else None,
                    "registration_initial_date": _date(
                        row.get("Registration.InitialRegistrationDate")),
                    "registration_last_update": _date(row.get("Registration.LastUpdateDate")),
                })
    return links
