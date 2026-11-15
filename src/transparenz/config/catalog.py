"""Laden und Validieren der Quellen- und Kriterienkonfiguration (TOML)."""

from __future__ import annotations

import tomllib
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from transparenz.entities.enums import (
    FINDING_STATUSES,
    AssessmentStatus,
    CommercialUse,
    DatasetKind,
)

CRITERIA_SCHEMA_VERSION = 2
CRITERION_GROUPS: dict[str, str] = {
    "klima": "Klima",
    "umwelt": "Umwelt",
    "soziales": "Soziales",
    "unternehmensfuehrung": "Unternehmensführung",
}
# Wirkung einer Kategorie im Profil; Anzeigetexte für Berichte und Website.
CATEGORY_EFFECTS: dict[str, str] = {
    "conflict": "Konflikt mit dem Profil",
    "separate": "gesondert gezeigt, kein Konflikt",
    "info": "Kennzahl oder Information",
}
DECISION_LABELS: dict[str, str] = {
    "decided": "entschieden",
    "proposed": "Vorschlag, noch zu bestätigen",
}


RELATIONSHIP_KEYS = ("own_account", "financial_stake_unclear", "asset_management", "custody",
                     "financing", "operation", "supply_contract")
# Stand der Datenanbindung je Beziehungstyp bzw. Quelle (für Berichte, einheitliches Vokabular).
DATA_STATUS_LABELS: dict[str, str] = {
    "no_source": "keine geeignete Quelle gefunden",
    "rights_unclear": "Quelle vorhanden, Nutzungsrechte ungeklärt",
    "mapping_open": "Nutzungsrechte dokumentiert, Unternehmenszuordnung offen",
    "not_integrated": "Quelle technisch noch nicht integriert",
    "integrated": "Quelle integriert",
    "unchecked": "ungeprüft (Seite automatisch nicht lesbar)",
}


class RelationshipRule(BaseModel):
    """Bewertungsregel des Profils für einen Beziehungstyp zwischen Unternehmen und Anlage.

    Eigentum auf eigene Rechnung, Vermögensverwaltung, Verwahrung, Finanzierung, Betrieb und
    Lieferverträge sind verschiedene Sachverhalte. Welcher davon im Profil als Konflikt gilt,
    steht hier und nirgends im Code.
    """

    model_config = ConfigDict(frozen=True)

    key: Literal["own_account", "financial_stake_unclear", "asset_management", "custody",
                 "financing", "operation", "supply_contract"]
    name: str
    description: str
    effect: Literal["conflict", "separate"]
    decision: Literal["decided", "proposed"] = "decided"
    reason: str = ""
    data_status: Literal["no_source", "rights_unclear", "mapping_open", "not_integrated",
                         "integrated", "unchecked"] = "no_source"
    data_note: str = ""

    @property
    def data_status_label(self) -> str:
        return DATA_STATUS_LABELS[self.data_status]


class CriterionCategory(BaseModel):
    """Unterkategorie eines Kriteriums mit ihrer Wirkung im Profil."""

    model_config = ConfigDict(frozen=True)

    key: str = Field(pattern=r"^[a-z0-9_]+$")
    name: str
    description: str = ""
    effect: Literal["conflict", "separate", "info"]
    decision: Literal["decided", "proposed"] = "decided"
    reason: str = ""


class Criterion(BaseModel):
    """Ein Kriterium samt Bewertungsregel des Profils.

    ``rule``, ``conflict_statuses`` und die Kategorien sind unsere Bewertungsentscheidung,
    keine Aussage einer Quelle. ``decision = "proposed"`` heisst: Regel vorgeschlagen, noch
    nicht bestätigt. ``status = "proposed"`` heisst: Kriterium noch nicht aktiv; Engine und
    Parser kennen es nicht.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    key: str = Field(pattern=r"^[a-z0-9_]+$")
    name: str
    description: str
    severity: Literal["schwer", "hoch"]
    group: Literal["klima", "umwelt", "soziales", "unternehmensfuehrung"] | None = None
    status: Literal["active", "proposed"] = "active"
    # activity: Tätigkeit oder Beteiligung (z. B. Kohleanlage); conduct: Verhalten/Verstoss
    basis: Literal["activity", "conduct"] = "conduct"
    decision: Literal["decided", "proposed"] = "decided"
    rule: str = ""
    conflict_statuses: tuple[AssessmentStatus, ...] = ()
    display: tuple[str, ...] = ()
    separate: tuple[str, ...] = ()
    open_questions: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    source_gap: str = ""
    # Stand der Datenanbindung (Vokabular DATA_STATUS_LABELS): Was fehlt bis zum ersten Beleg?
    data_status: Literal["no_source", "rights_unclear", "mapping_open", "not_integrated",
                         "integrated", "unchecked"] = "no_source"
    conflict_expiry_years: int | None = Field(default=None, gt=0)
    # Kürzeste Wirkungsdauer, wenn eine Behörde die Abhilfe bestätigt hat (nur mit Ablaufdauer).
    conflict_min_years_with_remediation: int | None = Field(default=None, gt=0)
    expiry_reason: str = ""
    # Beteiligungsschwelle für Eigentum auf eigene Rechnung, in Prozent (0 = jede Beteiligung).
    min_own_account_share_percent: float = Field(default=0.0, ge=0, le=100)
    categories: tuple[CriterionCategory, ...] = Field(default=(), alias="category")
    metric: str | None = None
    metric_unit: str | None = None
    threshold: float | None = None
    threshold_note: str = ""

    @model_validator(mode="after")
    def _check(self) -> Criterion:
        keys = [c.key for c in self.categories]
        dupes = {k for k in keys if keys.count(k) > 1}
        if dupes:
            raise ValueError(f"Kriterium {self.key}: doppelte Kategorien {sorted(dupes)}")
        wrong = [s.value for s in self.conflict_statuses if s not in FINDING_STATUSES]
        if wrong:
            raise ValueError(f"Kriterium {self.key}: {wrong} ist kein Belegstatus mit Beleg "
                             "und kann keinen Konflikt auslösen.")
        if self.conflict_min_years_with_remediation is not None and (
                self.conflict_expiry_years is None
                or self.conflict_min_years_with_remediation > self.conflict_expiry_years):
            raise ValueError(f"Kriterium {self.key}: conflict_min_years_with_remediation braucht "
                             "eine mindestens gleich lange conflict_expiry_years.")
        return self

    @property
    def data_status_label(self) -> str:
        return DATA_STATUS_LABELS[self.data_status]

    def category(self, key: str | None) -> CriterionCategory | None:
        return next((c for c in self.categories if c.key == key), None)

    @property
    def category_decides(self) -> bool:
        """Hängt die Konfliktwirkung von der Kategorie des Belegs ab?"""
        return any(c.effect != "conflict" for c in self.categories)

    @property
    def group_label(self) -> str:
        return CRITERION_GROUPS.get(self.group or "", "")

    def is_conflict(self, status: AssessmentStatus) -> bool:
        """Zählt dieser Belegstatus im Profil als Konflikt? (Unsere Bewertungsentscheidung.)"""
        return status in self.conflict_statuses


class EvidenceLevel(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str = Field(pattern=r"^[a-z0-9_]+$")
    name: str
    description: str
    statuses: tuple[AssessmentStatus, ...] = ()


class Metric(BaseModel):
    """Kennzahl ohne Ausschlusswirkung (z. B. Emissionen)."""

    model_config = ConfigDict(frozen=True)

    key: str = Field(pattern=r"^[a-z0-9_]+$")
    name: str
    unit: str
    criterion: str | None = None
    required_fields: tuple[str, ...] = ()
    exclusion_threshold_set: bool = False
    rule: str = ""
    note: str = ""


class SanctionsPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: Literal["evidence"] = "evidence"
    rule: str = ""
    note: str = ""


class CriteriaModel(BaseModel):
    """Das versionierte Kriterienmodell aus ``criteria.toml``."""

    model_config = ConfigDict(frozen=True)

    schema_version: Literal[2]
    profile_key: str = Field(pattern=r"^[a-z0-9_]+$")
    profile_name: str
    profile_version: str = Field(pattern=r"^\d+\.\d+$")
    decided_on: date
    statement: str
    criteria: tuple[Criterion, ...]
    metrics: tuple[Metric, ...] = ()
    evidence_levels: tuple[EvidenceLevel, ...] = ()
    sanctions: SanctionsPolicy = SanctionsPolicy()
    relationship_rules: tuple[RelationshipRule, ...] = ()

    @model_validator(mode="after")
    def _check(self) -> CriteriaModel:
        for label, keys in (("Kriterien", [c.key for c in self.criteria]),
                            ("Kennzahlen", [m.key for m in self.metrics]),
                            ("Beziehungstypen", [r.key for r in self.relationship_rules]),
                            ("Belegstufen", [e.key for e in self.evidence_levels])):
            dupes = {k for k in keys if keys.count(k) > 1}
            if dupes:
                raise ValueError(f"Doppelte {label}-Schlüssel: {sorted(dupes)}")
        known = {c.key for c in self.criteria}
        for metric in self.metrics:
            if metric.criterion and metric.criterion not in known:
                raise ValueError(f"Kennzahl {metric.key}: unbekanntes Kriterium "
                                 f"«{metric.criterion}».")
        return self

    @property
    def active(self) -> tuple[Criterion, ...]:
        return tuple(c for c in self.criteria if c.status == "active")

    def relationship_rule(self, key: str) -> RelationshipRule | None:
        return next((r for r in self.relationship_rules if r.key == key), None)

    def relationship_conflicts(self) -> frozenset[str]:
        """Beziehungstypen, die im Profil einen Konflikt auslösen können."""
        return frozenset(r.key for r in self.relationship_rules if r.effect == "conflict")

    @property
    def proposed(self) -> tuple[Criterion, ...]:
        return tuple(c for c in self.criteria if c.status == "proposed")

    @property
    def profile_label(self) -> str:
        return f"{self.profile_name}, Version {self.profile_version} vom " \
               f"{self.decided_on:%d.%m.%Y}"

    def grouped(self) -> list[tuple[str, tuple[Criterion, ...]]]:
        """Aktive Kriterien je Themengruppe, in der Reihenfolge von CRITERION_GROUPS."""
        return [(label, tuple(c for c in self.active if c.group == key))
                for key, label in CRITERION_GROUPS.items()
                if any(c.group == key for c in self.active)]


class UpdateDefaults(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_attempts: int = Field(default=3, ge=1, le=10)
    backoff_seconds: float = Field(default=2.0, ge=0)
    http_timeout_seconds: float = Field(default=30.0, gt=0)


class SourceConfig(BaseModel):
    """Eine Datenquelle inkl. Lizenzregistrierung.

    Lizenzfelder (siehe docs/DATA_SOURCES.md): ``license`` (genaue Bezeichnung),
    ``license_url``, ``terms_url`` (Originalseite mit den Nutzungsbedingungen),
    ``license_checked_on`` (Prüfdatum), ``commercial_use``, ``redistribution``
    (Weiterveröffentlichung) und ``attribution`` (verlangte/erbetene Quellenangabe).
    Ob eine Quelle genutzt werden darf, entscheidet ``config.licensing``.
    """

    model_config = ConfigDict(frozen=True)

    key: str = Field(pattern=r"^[a-z0-9_]+$")
    name: str
    kind: DatasetKind
    publisher: str
    fetcher: Literal["local", "http", "gleif_api", "external", "market"]
    format: Literal["json", "csv", "gleif_json", "external_json", "market_json"]
    location: str
    interval_hours: float = Field(gt=0)
    max_age_days: int = Field(gt=0)
    license: str
    commercial_use: CommercialUse
    is_fictional: bool
    license_url: str | None = None
    terms_url: str | None = None
    license_checked_on: date | None = None
    redistribution: CommercialUse = CommercialUse.UNKLAR
    storage: CommercialUse = CommercialUse.UNKLAR
    derivatives: CommercialUse = CommercialUse.UNKLAR
    attribution: str = ""
    description: str = ""
    coverage_of: str | None = None
    # nur fetcher = "gleif_api": Textdatei mit den abzufragenden LEIs (relativ zum Projekt)
    lei_list: str | None = None
    enabled: bool = True
    disabled_reason: str = ""
    external_mode: Literal[
        "gleif_ch", "zefix", "wikidata", "swissprtr",
        "sec_exchange", "sec_fund_classes", "sec_ncen",
    ] | None = None
    query_file: str | None = None
    supplementary_url: str | None = None

    @model_validator(mode="after")
    def _check_coverage(self) -> SourceConfig:
        if self.kind == DatasetKind.COVERAGE and not self.coverage_of:
            raise ValueError(f"Quelle {self.key}: coverage-Quellen brauchen 'coverage_of'.")
        if self.fetcher == "gleif_api" and not self.lei_list:
            raise ValueError(f"Quelle {self.key}: fetcher 'gleif_api' braucht 'lei_list'.")
        if (self.fetcher == "gleif_api") != (self.format == "gleif_json"):
            raise ValueError(
                f"Quelle {self.key}: 'gleif_api' und 'gleif_json' gehören zusammen."
            )
        if self.fetcher == "external" and (
            self.format != "external_json" or self.external_mode is None
        ):
            raise ValueError("external braucht external_json und external_mode")
        if self.fetcher == "market" and (
            self.kind != DatasetKind.MARKET or self.format != "market_json"
            or self.external_mode not in {"sec_exchange", "sec_fund_classes", "sec_ncen"}
        ):
            raise ValueError("market braucht kind market, market_json und unterstützten Modus")
        return self


class Catalog(BaseModel):
    model_config = ConfigDict(frozen=True)

    defaults: UpdateDefaults
    sources: tuple[SourceConfig, ...]
    # nur aktive Kriterien: Engine und Parser kennen keine blossen Vorschläge
    criteria: tuple[Criterion, ...]
    criteria_model: CriteriaModel | None = None

    @model_validator(mode="after")
    def _unique_keys(self) -> Catalog:
        for label, keys in (
            ("Quellen", [s.key for s in self.sources]),
            ("Kriterien", [c.key for c in self.criteria]),
        ):
            dupes = {k for k in keys if keys.count(k) > 1}
            if dupes:
                raise ValueError(f"Doppelte {label}-Schlüssel: {sorted(dupes)}")
        return self

    def source(self, key: str) -> SourceConfig:
        for s in self.sources:
            if s.key == key:
                return s
        raise KeyError(f"Unbekannte Quelle: {key}")

    def criterion(self, key: str) -> Criterion:
        for c in self.criteria:
            if c.key == key:
                return c
        raise KeyError(f"Unbekanntes Kriterium: {key}")

    @property
    def criterion_keys(self) -> set[str]:
        return {c.key for c in self.criteria}


def load_criteria_model(path: Path) -> CriteriaModel:
    """Lädt und prüft das ganze Kriterienmodell (aktive Kriterien, Vorschläge, Kennzahlen)."""
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    header = data.get("model")
    if not header:
        raise ValueError(f"{path}: Abschnitt [model] fehlt (schema_version, Profil, Version).")
    if header.get("schema_version") != CRITERIA_SCHEMA_VERSION:
        raise ValueError(f"{path}: schema_version {header.get('schema_version')!r} wird nicht "
                         f"unterstützt (erwartet {CRITERIA_SCHEMA_VERSION}).")
    return CriteriaModel(
        **header,
        criteria=tuple(Criterion(**c) for c in data.get("criterion", [])),
        metrics=tuple(Metric(**m) for m in data.get("metric", [])),
        evidence_levels=tuple(EvidenceLevel(**e) for e in data.get("evidence_level", [])),
        sanctions=SanctionsPolicy(**data.get("sanctions", {})),
        relationship_rules=tuple(RelationshipRule(**r)
                                 for r in data.get("relationship_type", [])),
    )


def load_criteria(path: Path) -> tuple[Criterion, ...]:
    """Nur die aktiven Kriterien (für Engine, Parser und Berichte)."""
    return load_criteria_model(path).active


def load_catalog(sources_path: Path, criteria_path: Path) -> Catalog:
    data = tomllib.loads(sources_path.read_text(encoding="utf-8"))
    model = load_criteria_model(criteria_path)
    return Catalog(
        defaults=UpdateDefaults(**data.get("defaults", {})),
        sources=tuple(SourceConfig(**s) for s in data.get("source", [])),
        criteria=model.active,
        criteria_model=model,
    )
