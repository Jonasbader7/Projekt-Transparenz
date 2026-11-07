"""Parser und Validierung für das interne Austauschformat (Version 1).

Jeder Parser liefert ein ``ParsedDataset`` mit Datensätzen und Befunden.
Regel: Gibt es mindestens einen Befund der Stufe «fehler», wird der gesamte
Datenstand verworfen (kein Teilimport). Warnungen werden protokolliert.

Formate:
* holdings  – CSV, eine Datei pro Fonds und Stichtag, Spalten siehe ``HOLDINGS_COLUMNS``
              (Fondsangaben wiederholen sich pro Zeile und müssen identisch sein)
* entities  – JSON ``{"companies": [...], "securities": [...], "relationships": [...]}``
* evidence  – CSV (Komma oder Semikolon, UTF-8), Spalten siehe ``EVIDENCE_COLUMNS``
* coverage  – CSV, Spalten siehe ``COVERAGE_COLUMNS``

Echte Quellen (z. B. Anbieter-CSV, GLEIF) bekommen später eigene Adapter, die in
dieses Format übersetzen. Siehe docs/DATA_MODEL.md.
"""

from __future__ import annotations

import csv
import io
import json
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ValidationError

from transparenz.entities.enums import DatasetKind
from transparenz.entities.identifiers import normalize_company_name
from transparenz.entities.models import (
    CompanyRecord,
    CoverageRecord,
    EvidenceRecord,
    FundInfo,
    Position,
    RelationshipRecord,
    SecurityRecord,
)

# Toleranzen für die Summe der Fondsgewichte (in Prozentpunkten)
WEIGHT_SUM_ERROR_RANGE = (95.0, 105.0)
WEIGHT_SUM_WARNING_RANGE = (99.5, 100.5)

EVIDENCE_COLUMNS = (
    "evidence_id",
    "company_name",
    "lei",
    "isin",
    "criterion",
    "description",
    "evidence_type",
    "proceeding_status",
    "publisher",
    "publisher_type",
    "source_title",
    "source_url",
    "published_date",
    "event_date",
    "verification_level",
    "last_reviewed",
    "metric_name",
    "metric_value",
    "metric_unit",
)
EVIDENCE_REQUIRED = tuple(
    c for c in EVIDENCE_COLUMNS
    if c not in {"lei", "isin", "event_date", "last_reviewed", "metric_name", "metric_value",
                 "metric_unit"}
)
HOLDINGS_COLUMNS = (
    "fund_isin",
    "fund_name",
    "fund_provider",
    "fund_as_of_date",
    "fund_currency",
    "fund_is_fictional",
    "fund_description",
    "position_isin",
    "position_name",
    "asset_class",
    "weight_pct",
    "country",
    "currency",
)
HOLDINGS_REQUIRED = (
    "fund_isin",
    "fund_name",
    "fund_provider",
    "fund_as_of_date",
    "position_name",
    "asset_class",
    "weight_pct",
)
COVERAGE_COLUMNS = ("company_name", "lei", "isin", "criterion", "reviewed_date")
COVERAGE_REQUIRED = ("company_name", "criterion", "reviewed_date")


@dataclass(frozen=True)
class ValidationIssue:
    level: Literal["fehler", "warnung"]
    message: str
    row: int | None = None

    def __str__(self) -> str:
        where = f"Zeile {self.row}: " if self.row is not None else ""
        return f"[{self.level}] {where}{self.message}"


@dataclass
class ParsedDataset:
    kind: DatasetKind
    records: dict[str, list[Any]] = field(default_factory=dict)
    issues: list[ValidationIssue] = field(default_factory=list)
    data_as_of: date | None = None

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.level == "fehler"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.level == "warnung"]

    @property
    def is_valid(self) -> bool:
        return not self.errors

    @property
    def record_count(self) -> int:
        return sum(len(v) for v in self.records.values())

    def error(self, message: str, row: int | None = None) -> None:
        self.issues.append(ValidationIssue("fehler", message, row))

    def warn(self, message: str, row: int | None = None) -> None:
        self.issues.append(ValidationIssue("warnung", message, row))


def _format_validation_error(exc: ValidationError) -> str:
    parts = []
    for err in exc.errors():
        loc = ".".join(str(x) for x in err.get("loc", ()) if x != "__root__")
        msg = err.get("msg", "ungültig").removeprefix("Value error, ")
        parts.append(f"{loc}: {msg}" if loc else msg)
    return "; ".join(parts)


def _build[T: BaseModel](
    model: type[T], rows: Iterable[dict[str, Any]], ds: ParsedDataset, label: str, row_offset: int
) -> list[T]:
    out: list[T] = []
    for i, row in enumerate(rows):
        try:
            out.append(model(**row))
        except ValidationError as exc:
            ds.error(f"{label}: {_format_validation_error(exc)}", row=i + row_offset)
        except TypeError as exc:
            ds.error(f"{label}: {exc}", row=i + row_offset)
    return out


def _dedupe[T: BaseModel](
    items: list[T], key: Callable[[T], object], ds: ParsedDataset, label: str
) -> list[T]:
    """Exakte Duplikate werden entfernt (Warnung), widersprüchliche sind ein Fehler."""
    seen: dict[object, T] = {}
    out: list[T] = []
    for item in items:
        k = key(item)
        if k in seen:
            if seen[k] == item:
                ds.warn(f"{label}: exaktes Duplikat entfernt ({k}).")
            else:
                ds.error(f"{label}: widersprüchliche Einträge mit gleichem Schlüssel ({k}).")
            continue
        seen[k] = item
        out.append(item)
    return out


def _load_json(content: bytes, ds: ParsedDataset) -> dict[str, Any] | None:
    try:
        data = json.loads(content.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        ds.error(f"Datei ist kein gültiges UTF-8-JSON: {exc}")
        return None
    if not isinstance(data, dict):
        ds.error("JSON muss ein Objekt auf oberster Ebene sein.")
        return None
    return data


def _read_csv(
    content: bytes, columns: tuple[str, ...], required: tuple[str, ...], ds: ParsedDataset
) -> list[dict[str, Any]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        ds.error(f"CSV ist nicht UTF-8-kodiert: {exc}")
        return []
    if not text.strip():
        ds.error("CSV ist leer.")
        return []
    first_line = text.splitlines()[0]
    delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    header = [h.strip() for h in (reader.fieldnames or [])]
    missing = [c for c in required if c not in header]
    if missing:
        ds.error(f"Pflichtspalten fehlen: {', '.join(missing)}")
        return []
    unknown = [h for h in header if h not in columns]
    if unknown:
        ds.warn(f"Unbekannte Spalten werden ignoriert: {', '.join(unknown)}")
    rows = []
    for raw in reader:
        row = {(k or "").strip(): (v.strip() if isinstance(v, str) else v) for k, v in raw.items()}
        rows.append({c: (row.get(c) or None) for c in columns})
    if not rows:
        ds.error("CSV enthält keine Datenzeilen.")
    return rows


def _to_number(value: Any) -> Any:
    """Akzeptiert «4.5», «4,5» und «4.5 %» (Excel-Export mit Schweizer Einstellungen)."""
    if not isinstance(value, str):
        return value
    text = value.replace("%", "").replace("'", "").replace("’", "").strip()
    if "," in text and "." not in text:
        text = text.replace(",", ".")
    return text


_TRUE = {"ja", "true", "1", "yes", "wahr"}
_FALSE = {"nein", "false", "0", "no", "falsch", ""}


def parse_holdings_csv(content: bytes, criteria_keys: set[str] | None = None) -> ParsedDataset:
    """Positionsliste eines Fonds (eine Datei = ein Fonds, ein Stichtag)."""
    ds = ParsedDataset(DatasetKind.HOLDINGS)
    rows = _read_csv(content, HOLDINGS_COLUMNS, HOLDINGS_REQUIRED, ds)
    if not rows:
        return ds

    fund_fields = [c for c in HOLDINGS_COLUMNS if c.startswith("fund_")]
    fund_values = {tuple(r.get(c) for c in fund_fields) for r in rows}
    if len(fund_values) > 1:
        ds.error(
            "Die Datei enthält abweichende Fondsangaben (fund_*-Spalten). "
            "Pro Datei ist genau ein Fonds mit einem Stichtag erlaubt."
        )
        return ds
    first = rows[0]
    fictional_raw = (first.get("fund_is_fictional") or "").strip().lower()
    if fictional_raw not in _TRUE | _FALSE:
        ds.error(f"fund_is_fictional: unbekannter Wert «{fictional_raw}» (ja/nein).")
    fund_row = {
        "isin": first.get("fund_isin"),
        "name": first.get("fund_name"),
        "provider": first.get("fund_provider"),
        "as_of_date": first.get("fund_as_of_date"),
        "currency": first.get("fund_currency") or "CHF",
        "description": first.get("fund_description") or "",
        "is_fictional": fictional_raw in _TRUE,
    }
    funds = _build(FundInfo, [fund_row], ds, "Fonds", row_offset=2)
    position_rows = [
        {
            "isin": r.get("position_isin"),
            "name": r.get("position_name"),
            "asset_class": (r.get("asset_class") or "").lower() or None,
            "weight_pct": _to_number(r.get("weight_pct")),
            "country": r.get("country"),
            "currency": r.get("currency"),
        }
        for r in rows
    ]
    positions = _build(Position, position_rows, ds, "Position", row_offset=2)
    positions = _dedupe(positions, lambda p: p.isin or f"name:{p.name}", ds, "Position")
    if positions and not ds.errors:
        total = round(sum(p.weight_pct for p in positions), 4)
        lo, hi = WEIGHT_SUM_ERROR_RANGE
        wlo, whi = WEIGHT_SUM_WARNING_RANGE
        if not lo <= total <= hi:
            ds.error(f"Summe der Gewichte {total:.2f} % ausserhalb von {lo}–{hi} %.")
        elif not wlo <= total <= whi:
            ds.warn(f"Summe der Gewichte beträgt {total:.2f} % (erwartet ≈ 100 %).")
    ds.records = {"funds": funds, "positions": positions}
    if funds:
        ds.data_as_of = funds[0].as_of_date
    return ds


def parse_entities_json(content: bytes, criteria_keys: set[str] | None = None) -> ParsedDataset:
    ds = ParsedDataset(DatasetKind.ENTITIES)
    data = _load_json(content, ds)
    if data is None:
        return ds
    companies = _build(CompanyRecord, data.get("companies", []), ds, "Unternehmen", 1)
    securities = _build(SecurityRecord, data.get("securities", []), ds, "Wertpapier", 1)
    relationships = _build(
        RelationshipRecord, data.get("relationships", []), ds, "Konzernbeziehung", 1
    )
    if not companies:
        ds.error("Keine Unternehmen enthalten.")
    companies = _dedupe(companies, lambda c: c.company_key, ds, "Unternehmen")
    securities = _dedupe(securities, lambda s: s.isin, ds, "Wertpapier")
    relationships = _dedupe(
        relationships, lambda r: (r.parent_key, r.child_key), ds, "Konzernbeziehung"
    )

    keys = {c.company_key for c in companies}
    leis: dict[str, str] = {}
    for c in companies:
        if c.lei:
            if c.lei in leis:
                ds.error(f"LEI {c.lei} ist mehreren Unternehmen zugeordnet.")
            leis[c.lei] = c.company_key
    for s in securities:
        if s.issuer_company_key and s.issuer_company_key not in keys:
            ds.error(f"Wertpapier {s.isin}: Emittent {s.issuer_company_key} unbekannt.")
    for r in relationships:
        for k in (r.parent_key, r.child_key):
            if k not in keys:
                ds.error(f"Konzernbeziehung verweist auf unbekanntes Unternehmen {k}.")
    _check_cycles(relationships, ds)

    ds.records = {"companies": companies, "securities": securities, "relationships": relationships}
    return ds


def _check_cycles(relationships: list[RelationshipRecord], ds: ParsedDataset) -> None:
    parents: dict[str, set[str]] = defaultdict(set)
    for r in relationships:
        parents[r.child_key].add(r.parent_key)

    def visit(node: str, path: tuple[str, ...]) -> None:
        for p in parents.get(node, ()):
            if p in path:
                ds.error(f"Zirkuläre Konzernbeziehung: {' → '.join((*path, p))}")
                continue
            visit(p, (*path, p))

    for child in list(parents):
        visit(child, (child,))


def parse_evidence_csv(content: bytes, criteria_keys: set[str] | None = None) -> ParsedDataset:
    ds = ParsedDataset(DatasetKind.EVIDENCE)
    rows = _read_csv(content, EVIDENCE_COLUMNS, EVIDENCE_REQUIRED, ds)
    records = _build(EvidenceRecord, rows, ds, "Sachverhalt", row_offset=2)
    if criteria_keys is not None:
        for r in records:
            if r.criterion not in criteria_keys:
                ds.error(f"Sachverhalt {r.evidence_id}: unbekanntes Kriterium «{r.criterion}».")
    records = _dedupe(records, lambda r: r.evidence_id, ds, "Sachverhalt")

    semantic: dict[tuple[object, ...], str] = {}
    for r in records:
        key = (
            normalize_company_name(r.company_name),
            r.criterion,
            r.publisher.strip().lower(),
            r.published_date,
            r.evidence_type,
        )
        if key in semantic:
            ds.warn(
                f"Mögliches inhaltliches Duplikat: {r.evidence_id} und {semantic[key]} "
                "(gleiches Unternehmen, Kriterium, Herausgeber und Datum)."
            )
        else:
            semantic[key] = r.evidence_id

    ds.records = {"evidence": records}
    dates = [r.last_reviewed or r.published_date for r in records]
    ds.data_as_of = max(dates) if dates else None
    return ds


def parse_coverage_csv(content: bytes, criteria_keys: set[str] | None = None) -> ParsedDataset:
    ds = ParsedDataset(DatasetKind.COVERAGE)
    rows = _read_csv(content, COVERAGE_COLUMNS, COVERAGE_REQUIRED, ds)
    records = _build(CoverageRecord, rows, ds, "Abdeckung", row_offset=2)
    if criteria_keys is not None:
        for r in records:
            if r.criterion not in criteria_keys:
                ds.error(f"Abdeckung {r.company_name}: unbekanntes Kriterium «{r.criterion}».")
    records = _dedupe(
        records, lambda r: (r.lei or normalize_company_name(r.company_name), r.criterion), ds,
        "Abdeckung",
    )
    ds.records = {"coverage": records}
    ds.data_as_of = max((r.reviewed_date for r in records), default=None)
    return ds


PARSERS: dict[tuple[DatasetKind, str], Callable[[bytes, set[str] | None], ParsedDataset]] = {
    (DatasetKind.HOLDINGS, "csv"): parse_holdings_csv,
    (DatasetKind.ENTITIES, "json"): parse_entities_json,
    (DatasetKind.EVIDENCE, "csv"): parse_evidence_csv,
    (DatasetKind.COVERAGE, "csv"): parse_coverage_csv,
}
