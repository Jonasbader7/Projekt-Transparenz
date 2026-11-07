"""GLEIF-Adapter: LEI-Stammdaten (Level 1) und gemeldete Muttergesellschaften (Level 2).

Quelle: GLEIF-API ``https://api.gleif.org/api/v1`` (JSON:API, ohne Konto).
Lizenz: CC0 1.0 laut «LEI Data Terms of Use» (geprüft 07.11.2026, docs/DATA_SOURCES.md).
API-Limit laut GLEIF-Dokumentation: 60 Anfragen pro Minute und Nutzer.

Ablauf
------
1. ``GleifApiFetcher`` liest die Abfrageliste (ein LEI pro Zeile) und ruft ab:
   * ``/lei-records?filter[lei]=…`` (bis 100 LEIs pro Anfrage),
   * ``/lei-records/{lei}/direct-parent-relationship`` bzw. ``…/ultimate-parent-relationship``
     nur, wenn der LEI-Datensatz einen Link ``relationship-record`` enthält,
   * die LEI-Datensätze der so gefundenen Muttergesellschaften.
   Zwischen Anfragen wird gewartet (Standard 1.1 s → unter 60/Min.). Das Ergebnis ist ein
   **Bündel** mit den unveränderten API-Antworten (``data``-Objekte) – so bleibt jeder
   Datenstand als Rohdaten-Schnappschuss nachvollziehbar.
2. ``parse_gleif_bundle`` validiert das Bündel mit Pydantic und übersetzt es ins interne
   Stammdatenformat (``CompanyRecord``, ``RelationshipRecord``). Danach laufen dieselben
   Prüfungen wie für jede Stammdatenquelle (``check_entities``).

Bewusst NICHT enthalten: das ISIN-LEI-Mapping (GLEIF/ANNA). Es ist von der Nutzung
ausgeschlossen, bis seine Lizenz geklärt ist. GLEIF liefert hier also keine Zuordnung
Wertpapier → Unternehmen, sondern bestätigt LEIs und Konzernbeziehungen.

Regeln der Übersetzung (Entscheid D-026)
----------------------------------------
* Unternehmensschlüssel ``lei:<LEI>``.
* Registrierungsstatus ANNULLED, CANCELLED, DUPLICATE: Datensatz wird nicht übernommen
  (Warnung). Andere Status als ISSUED/PENDING_*: übernommen mit Warnung (z. B. LAPSED =
  Angaben nicht mehr jährlich bestätigt).
* Konzernbeziehung gilt nur als **verifiziert** (überträgt Belege, D-012), wenn sie aktiv,
  veröffentlicht (PUBLISHED) und von der LEI-Vergabestelle vollständig bestätigt ist
  (``corroborationLevel`` FULLY_CORROBORATED). Alles andere: unverifiziert (nur Hinweis).
* Ist die direkte zugleich die oberste Mutter, wird eine Beziehung «direkte Mutter» gespeichert.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from transparenz.entities.enums import DatasetKind, RelationshipType
from transparenz.entities.identifiers import is_valid_lei
from transparenz.entities.models import CompanyRecord, RelationshipRecord
from transparenz.ingestion.fetchers import FetchError, FetchResult
from transparenz.ingestion.parsing import ParsedDataset, _build, _load_json, check_entities

log = logging.getLogger(__name__)

BUNDLE_FORMAT = "transparenz-gleif-bundle/1"
GLEIF_API_BASE = "https://api.gleif.org/api/v1"
MAX_LEIS = 500
CHUNK_SIZE = 100
JSONAPI = "application/vnd.api+json"

REGISTRATION_OK = frozenset({"ISSUED", "PENDING_TRANSFER", "PENDING_ARCHIVAL"})
REGISTRATION_EXCLUDED = frozenset({"ANNULLED", "CANCELLED", "DUPLICATE"})
PARENT_KINDS: dict[str, RelationshipType] = {
    "direct-parent": RelationshipType.DIREKTE_MUTTER,
    "ultimate-parent": RelationshipType.OBERSTE_MUTTER,
}
RELATIONSHIP_TYPES: dict[str, RelationshipType] = {
    "IS_DIRECTLY_CONSOLIDATED_BY": RelationshipType.DIREKTE_MUTTER,
    "IS_ULTIMATELY_CONSOLIDATED_BY": RelationshipType.OBERSTE_MUTTER,
}


def company_key_for_lei(lei: str) -> str:
    return f"lei:{lei.upper()}"


# --------------------------------------------------------------------- Abfrageliste
def read_lei_list(path: Path) -> list[str]:
    """Liest die Abfrageliste. Ungültige Einträge sind ein dauerhafter Fehler (kein Abruf)."""
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError as exc:
        raise FetchError(f"Abfrageliste nicht gefunden: {path}", transient=False) from exc
    leis: list[str] = []
    problems: list[str] = []
    for no, raw in enumerate(text.splitlines(), start=1):
        value = raw.split("#", 1)[0].strip().upper()
        if not value:
            continue
        if not is_valid_lei(value):
            problems.append(f"Zeile {no}: «{value}» ist kein gültiger LEI")
        elif value not in leis:
            leis.append(value)
    if problems:
        raise FetchError(f"Abfrageliste {path.name}: " + "; ".join(problems), transient=False)
    if not leis:
        raise FetchError(f"Abfrageliste {path.name} enthält keine LEIs.", transient=False)
    if len(leis) > MAX_LEIS:
        raise FetchError(
            f"Abfrageliste {path.name}: {len(leis)} LEIs, höchstens {MAX_LEIS} erlaubt "
            "(für grosse Mengen die Golden Copy prüfen).",
            transient=False,
        )
    return sorted(leis)


# ---------------------------------------------------------------------------- Abruf
def _parent_lei(relationship: dict[str, Any]) -> str | None:
    """LEI der Muttergesellschaft (endNode) aus einem rohen Beziehungsdatensatz."""
    attributes = relationship.get("attributes") or {}
    node = (attributes.get("relationship") or {}).get("endNode") or {}
    value = str(node.get("id") or "").upper()
    return value if is_valid_lei(value) else None


class GleifApiFetcher:
    def __init__(
        self,
        lei_list_path: Path,
        *,
        base_url: str = GLEIF_API_BASE,
        timeout: float = 30.0,
        user_agent: str,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
        min_interval_seconds: float = 1.1,
    ) -> None:
        self.lei_list_path = lei_list_path
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.user_agent = user_agent
        self._client = client
        self._sleep = sleep
        self.min_interval_seconds = min_interval_seconds
        self.request_count = 0

    def _get(self, client: httpx.Client, url: str, params: dict[str, str] | None = None) -> Any:
        if self.request_count:
            self._sleep(self.min_interval_seconds)
        self.request_count += 1
        headers = {"User-Agent": self.user_agent, "Accept": JSONAPI}
        try:
            response = client.get(url, params=params, headers=headers)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise FetchError(f"Netzwerkfehler bei {url}: {exc}", transient=True) from exc
        status = response.status_code
        if status == 429 or status >= 500:
            raise FetchError(f"HTTP {status} bei {url}", transient=True)
        if status >= 400:
            raise FetchError(f"HTTP {status} bei {url}", transient=False)
        try:
            return response.json()
        except ValueError as exc:
            raise FetchError(f"Antwort von {url} ist kein JSON.", transient=False) from exc

    def _lei_records(
        self, client: httpx.Client, leis: list[str]
    ) -> tuple[list[dict[str, Any]], str | None]:
        records: list[dict[str, Any]] = []
        publish_date: str | None = None
        for start in range(0, len(leis), CHUNK_SIZE):
            chunk = leis[start : start + CHUNK_SIZE]
            body = self._get(
                client,
                f"{self.base_url}/lei-records",
                {"filter[lei]": ",".join(chunk), "page[size]": "200"},
            )
            data = body.get("data") if isinstance(body, dict) else None
            if not isinstance(data, list):
                raise FetchError("GLEIF-Antwort ohne Datenliste (data).", transient=False)
            pagination = (body.get("meta") or {}).get("pagination") or {}
            if int(pagination.get("lastPage") or 1) > 1:
                raise FetchError(
                    "GLEIF-Antwort ist auf mehrere Seiten verteilt – nicht erwartet.",
                    transient=False,
                )
            records.extend(data)
            publish_date = ((body.get("meta") or {}).get("goldenCopy") or {}).get(
                "publishDate"
            ) or publish_date
        return records, publish_date

    def fetch(self, etag: str | None = None, last_modified: str | None = None) -> FetchResult:
        leis = read_lei_list(self.lei_list_path)
        self.request_count = 0
        client = self._client or httpx.Client(timeout=self.timeout, follow_redirects=False)
        try:
            records, publish_date = self._lei_records(client, leis)
            relationships: list[dict[str, Any]] = []
            for rec in sorted(records, key=lambda r: str(r.get("id"))):
                lei = str(rec.get("id", "")).upper()
                if not is_valid_lei(lei):
                    continue  # wird beim Parsen als Fehler gemeldet
                for kind in PARENT_KINDS:
                    links = ((rec.get("relationships") or {}).get(kind) or {}).get("links") or {}
                    if "relationship-record" not in links:
                        continue  # keine Mutter gemeldet oder Ausnahme (reporting-exception)
                    # URL aus geprüftem LEI selbst bauen – keinen fremden Links folgen.
                    url = f"{self.base_url}/lei-records/{lei}/{kind}-relationship"
                    body = self._get(client, url)
                    data = body.get("data") if isinstance(body, dict) else None
                    if isinstance(data, dict):
                        relationships.append(data)
                    elif isinstance(data, list):
                        relationships.extend(d for d in data if isinstance(d, dict))
            known = {str(r.get("id", "")).upper() for r in records}
            parent_leis = {_parent_lei(rel) for rel in relationships}
            parents = sorted(p for p in parent_leis if p and p not in known)
            if parents:
                parent_records, _ = self._lei_records(client, parents)
                records.extend(parent_records)
        finally:
            if self._client is None:
                client.close()

        bundle = {
            "_format": BUNDLE_FORMAT,
            "_hinweis": "Unveränderte Antworten der GLEIF-API (CC0 1.0), zusammengestellt von "
            "Projekt Transparenz. Quelle: GLEIF, api.gleif.org.",
            "api_base": self.base_url,
            "golden_copy_publish_date": publish_date,
            "requested_leis": leis,
            "lei_records": sorted(records, key=lambda r: str(r.get("id"))),
            "relationship_records": sorted(relationships, key=lambda r: str(r.get("id"))),
        }
        content = json.dumps(bundle, ensure_ascii=False, sort_keys=True, indent=1).encode("utf-8")
        log.info("GLEIF: %d LEIs abgefragt, %d Anfragen", len(leis), self.request_count)
        return FetchResult(origin=f"{self.base_url} ({len(leis)} LEIs)", content=content)


# ------------------------------------------------------------- Validierung (Pydantic)
class _G(BaseModel):
    """Ausschnitt der GLEIF-JSON:API-Struktur; unbekannte Felder werden ignoriert.

    Feldnamen (camelCase) wie in der GLEIF-API, damit die Rohantwort direkt validiert wird.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")


def _lei(value: str) -> str:
    value = value.strip().upper()
    if not is_valid_lei(value):
        raise ValueError(f"Ungültiger LEI (Format oder Prüfziffer): {value}")
    return value


class GleifName(_G):
    name: str = Field(min_length=1)


class GleifAddress(_G):
    country: str | None = Field(default=None, min_length=2, max_length=2)


class GleifEntity(_G):
    legalName: GleifName
    legalAddress: GleifAddress
    status: str = Field(min_length=1)


class GleifRegistration(_G):
    status: str = Field(min_length=1)
    lastUpdateDate: datetime
    corroborationLevel: str | None = None


class GleifLeiAttributes(_G):
    lei: str
    entity: GleifEntity
    registration: GleifRegistration

    @field_validator("lei")
    @classmethod
    def _check_lei(cls, v: str) -> str:
        return _lei(v)


class GleifLeiRecord(_G):
    type: Literal["lei-records"]
    id: str
    attributes: GleifLeiAttributes
    relationships: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _id_matches(self) -> GleifLeiRecord:
        if self.id.upper() != self.attributes.lei:
            raise ValueError(f"id {self.id} passt nicht zu attributes.lei {self.attributes.lei}")
        return self


class GleifNode(_G):
    id: str
    type: Literal["LEI"]

    @field_validator("id")
    @classmethod
    def _check_id(cls, v: str) -> str:
        return _lei(v)


class GleifRelationship(_G):
    startNode: GleifNode
    endNode: GleifNode
    type: str
    status: str


class GleifRelationshipRegistration(_G):
    status: str
    corroborationLevel: str | None = None


class GleifRelationshipAttributes(_G):
    relationship: GleifRelationship
    registration: GleifRelationshipRegistration


class GleifRelationshipRecord(_G):
    type: Literal["relationship-records"]
    id: str
    attributes: GleifRelationshipAttributes

    @property
    def verified(self) -> bool:
        a = self.attributes
        return (
            a.relationship.status == "ACTIVE"
            and a.registration.status == "PUBLISHED"
            and a.registration.corroborationLevel == "FULLY_CORROBORATED"
        )


# -------------------------------------------------------------------- Übersetzung
def parse_gleif_bundle(content: bytes, criteria_keys: set[str] | None = None) -> ParsedDataset:
    ds = ParsedDataset(DatasetKind.ENTITIES)
    data = _load_json(content, ds)
    if data is None:
        return ds
    if data.get("_format") != BUNDLE_FORMAT:
        ds.error(f"Unbekanntes Bündelformat «{data.get('_format')}» (erwartet {BUNDLE_FORMAT}).")
        return ds

    requested_raw = data.get("requested_leis") or []
    requested = [str(x).upper() for x in requested_raw if isinstance(x, str)]
    for value in requested:
        if not is_valid_lei(value):
            ds.error(f"Abgefragter LEI ungültig: {value}")

    publish = data.get("golden_copy_publish_date")
    if publish:
        try:
            ds.data_as_of = datetime.fromisoformat(str(publish).replace("Z", "+00:00")).date()
        except ValueError:
            ds.error(f"golden_copy_publish_date ist kein Datum: {publish}")
    else:
        ds.warn("Kein Datenstand (goldenCopy.publishDate) in der GLEIF-Antwort.")

    records = _build(GleifLeiRecord, data.get("lei_records") or [], ds, "GLEIF-LEI-Datensatz", 1)
    rels = _build(
        GleifRelationshipRecord, data.get("relationship_records") or [], ds,
        "GLEIF-Beziehungsdatensatz", 1,
    )

    companies: list[CompanyRecord] = []
    returned = {rec.attributes.lei for rec in records}
    for rec in records:
        a = rec.attributes
        reg = a.registration.status
        if reg in REGISTRATION_EXCLUDED:
            ds.warn(f"LEI {a.lei}: Registrierungsstatus {reg} – nicht übernommen.")
            continue
        if reg not in REGISTRATION_OK:
            ds.warn(
                f"LEI {a.lei}: Registrierungsstatus {reg} – Angaben sind laut GLEIF nicht "
                "aktuell bestätigt."
            )
        if a.entity.status != "ACTIVE":
            ds.warn(f"LEI {a.lei}: Rechtsträger laut GLEIF «{a.entity.status}».")
        companies.append(
            CompanyRecord(
                company_key=company_key_for_lei(a.lei),
                name=a.entity.legalName.name,
                lei=a.lei,
                country=a.entity.legalAddress.country,
            )
        )
    for lei in requested:
        if lei not in returned and is_valid_lei(lei):
            ds.warn(f"LEI {lei}: bei GLEIF nicht gefunden.")

    relationships: list[RelationshipRecord] = []
    by_child: dict[str, dict[RelationshipType, GleifRelationshipRecord]] = {}
    for rel in rels:
        r = rel.attributes.relationship
        rtype = RELATIONSHIP_TYPES.get(r.type)
        if rtype is None:
            ds.warn(f"Beziehung {rel.id}: Typ {r.type} wird nicht verwendet.")
            continue
        if r.status != "ACTIVE":
            ds.warn(f"Beziehung {r.startNode.id} → {r.endNode.id}: Status {r.status}, ignoriert.")
            continue
        if rtype in by_child.setdefault(r.startNode.id, {}):
            ds.error(f"LEI {r.startNode.id}: mehrere aktive Beziehungen vom Typ {r.type}.")
            continue
        by_child[r.startNode.id][rtype] = rel

    for child, kinds in sorted(by_child.items()):
        direct = kinds.get(RelationshipType.DIREKTE_MUTTER)
        ultimate = kinds.get(RelationshipType.OBERSTE_MUTTER)
        same = (
            direct is not None
            and ultimate is not None
            and direct.attributes.relationship.endNode.id
            == ultimate.attributes.relationship.endNode.id
        )
        for rtype, rel in kinds.items():
            if same and rtype == RelationshipType.OBERSTE_MUTTER:
                continue
            reg = rel.attributes.registration
            what = "direkte und oberste Mutter" if same else (
                "direkte Mutter" if rtype == RelationshipType.DIREKTE_MUTTER else "oberste Mutter"
            )
            relationships.append(
                RelationshipRecord(
                    parent_key=company_key_for_lei(rel.attributes.relationship.endNode.id),
                    child_key=company_key_for_lei(child),
                    relationship_type=rtype,
                    verified=rel.verified,
                    source=(
                        f"GLEIF Level 2 ({what}); Status {reg.status}, "
                        f"Bestätigung {reg.corroborationLevel or 'unbekannt'}"
                    ),
                )
            )

    check_entities(ds, companies, [], relationships)
    return ds


GLEIF_PARSERS = {(DatasetKind.ENTITIES, "gleif_json"): parse_gleif_bundle}
