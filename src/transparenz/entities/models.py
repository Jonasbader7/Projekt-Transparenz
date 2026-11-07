"""Validierte Domänen-Datensätze (Pydantic).

Diese Modelle sind die einzige Stelle, an der fachliche Validierungsregeln für
importierte Daten stehen. Sie werden beim Import UND beim Laden aus der Datenbank
verwendet.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from transparenz.entities.enums import (
    PUBLISHER_TIER,
    AssetClass,
    Confidence,
    EvidenceType,
    MappingMethod,
    ProceedingStatus,
    PublisherType,
    RelationshipType,
    SourceTier,
    VerificationLevel,
)
from transparenz.entities.identifiers import is_valid_isin, is_valid_lei


def _clean_optional(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value or None
    if isinstance(value, float) and value != value:  # NaN aus CSV
        return None
    return value


def _check_isin(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.upper()
    if not is_valid_isin(value):
        raise ValueError(f"Ungültige ISIN (Format oder Prüfziffer): {value}")
    return value


def _check_lei(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.upper()
    if not is_valid_lei(value):
        raise ValueError(f"Ungültiger LEI (Format oder Prüfziffer): {value}")
    return value


def _check_not_future(value: date | None, field: str) -> date | None:
    if value is not None and value > date.today():
        raise ValueError(f"{field} liegt in der Zukunft: {value.isoformat()}")
    return value


class _Record(BaseModel):
    model_config = ConfigDict(frozen=True, from_attributes=True, extra="ignore")


class FundInfo(_Record):
    isin: str
    name: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    as_of_date: date
    currency: str = Field(default="CHF", min_length=3, max_length=3)
    description: str = ""
    is_fictional: bool = False

    @field_validator("isin")
    @classmethod
    def _isin(cls, v: str) -> str:
        checked = _check_isin(v.strip())
        assert checked is not None
        return checked

    @field_validator("as_of_date")
    @classmethod
    def _as_of(cls, v: date) -> date:
        _check_not_future(v, "Stichtag")
        return v


class Position(_Record):
    """Eine Fondsposition. Die ISIN bezeichnet das Wertpapier, nicht den Emittenten."""

    isin: str | None = None
    name: str = Field(min_length=1)
    asset_class: AssetClass
    weight_pct: float = Field(ge=0, le=100)
    country: str | None = None
    currency: str | None = None

    @field_validator("isin", "country", "currency", mode="before")
    @classmethod
    def _clean(cls, v: object) -> object:
        return _clean_optional(v)

    @field_validator("isin")
    @classmethod
    def _isin(cls, v: str | None) -> str | None:
        return _check_isin(v)


class CompanyRecord(_Record):
    company_key: str = Field(min_length=1)
    name: str = Field(min_length=1)
    lei: str | None = None
    country: str | None = None

    @field_validator("lei", "country", mode="before")
    @classmethod
    def _clean(cls, v: object) -> object:
        return _clean_optional(v)

    @field_validator("lei")
    @classmethod
    def _lei(cls, v: str | None) -> str | None:
        return _check_lei(v)


class SecurityRecord(_Record):
    """Zuordnung Wertpapier (ISIN) → Emittent (Unternehmen), mit Quelle und Vertrauen."""

    isin: str
    name: str = Field(min_length=1)
    issuer_company_key: str | None = None
    mapping_method: MappingMethod
    mapping_confidence: Confidence
    mapping_source: str = Field(min_length=1)

    @field_validator("issuer_company_key", mode="before")
    @classmethod
    def _clean(cls, v: object) -> object:
        return _clean_optional(v)

    @field_validator("isin")
    @classmethod
    def _isin(cls, v: str) -> str:
        checked = _check_isin(v.strip())
        assert checked is not None
        return checked

    @model_validator(mode="after")
    def _consistent(self) -> SecurityRecord:
        if self.issuer_company_key is None and self.mapping_method != MappingMethod.KEINE:
            raise ValueError(f"{self.isin}: ohne Emittent muss mapping_method 'keine' sein.")
        return self


class RelationshipRecord(_Record):
    parent_key: str = Field(min_length=1)
    child_key: str = Field(min_length=1)
    relationship_type: RelationshipType
    verified: bool
    source: str = Field(min_length=1)
    ownership_pct: float | None = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def _no_self(self) -> RelationshipRecord:
        if self.parent_key == self.child_key:
            raise ValueError("Ein Unternehmen kann nicht seine eigene Muttergesellschaft sein.")
        return self


class EvidenceRecord(_Record):
    """Ein Sachverhalt: nachvollziehbarer Beleg mit Quelle, Art und Status.

    Das Unternehmen wird so identifiziert, wie die Quelle es tut (Name, ggf. LEI/ISIN).
    Die Zuordnung zu unseren Stammdaten passiert erst beim Screening – mit Vertrauensstatus.
    """

    evidence_id: str = Field(min_length=1)
    company_name: str = Field(min_length=1)
    lei: str | None = None
    isin: str | None = None
    criterion: str = Field(min_length=1)
    description: str = Field(min_length=10)
    evidence_type: EvidenceType
    proceeding_status: ProceedingStatus
    publisher: str = Field(min_length=1)
    publisher_type: PublisherType
    source_title: str = Field(min_length=1)
    source_url: str
    published_date: date
    event_date: date | None = None
    verification_level: VerificationLevel
    last_reviewed: date | None = None
    metric_name: str | None = None
    metric_value: float | None = None
    metric_unit: str | None = None

    @field_validator(
        "lei", "isin", "event_date", "last_reviewed", "metric_name", "metric_value",
        "metric_unit", mode="before",
    )
    @classmethod
    def _clean(cls, v: object) -> object:
        return _clean_optional(v)

    @field_validator("lei")
    @classmethod
    def _lei(cls, v: str | None) -> str | None:
        return _check_lei(v)

    @field_validator("isin")
    @classmethod
    def _isin(cls, v: str | None) -> str | None:
        return _check_isin(v)

    @field_validator("source_url")
    @classmethod
    def _url(cls, v: str) -> str:
        v = v.strip()
        if not (v.startswith("https://") or v.startswith("http://")):
            raise ValueError("source_url muss mit http:// oder https:// beginnen.")
        return v

    @field_validator("published_date")
    @classmethod
    def _published(cls, v: date) -> date:
        _check_not_future(v, "Veröffentlichungsdatum")
        return v

    @field_validator("last_reviewed")
    @classmethod
    def _reviewed(cls, v: date | None) -> date | None:
        return _check_not_future(v, "Letzte Überprüfung")

    @model_validator(mode="after")
    def _metric_consistency(self) -> EvidenceRecord:
        if self.metric_value is not None and not self.metric_name:
            raise ValueError("metric_value ohne metric_name.")
        if self.evidence_type in {EvidenceType.GERICHTSURTEIL} and self.publisher_type not in {
            PublisherType.GERICHT
        }:
            raise ValueError("Ein Gerichtsurteil muss von einem Gericht stammen.")
        if self.evidence_type == EvidenceType.BEHOERDLICHE_FESTSTELLUNG and (
            self.publisher_type != PublisherType.BEHOERDE
        ):
            raise ValueError("Eine behördliche Feststellung muss von einer Behörde stammen.")
        return self

    @property
    def tier(self) -> SourceTier:
        return PUBLISHER_TIER[self.publisher_type]


class CoverageRecord(_Record):
    """Belegt, dass eine Quelle ein Unternehmen für ein Kriterium geprüft hat.

    Nur mit Abdeckung darf «keine Hinweise» angezeigt werden – sonst «unbekannt».
    """

    company_name: str = Field(min_length=1)
    lei: str | None = None
    isin: str | None = None
    criterion: str = Field(min_length=1)
    reviewed_date: date

    @field_validator("lei", "isin", mode="before")
    @classmethod
    def _clean(cls, v: object) -> object:
        return _clean_optional(v)

    @field_validator("lei")
    @classmethod
    def _lei(cls, v: str | None) -> str | None:
        return _check_lei(v)

    @field_validator("isin")
    @classmethod
    def _isin(cls, v: str | None) -> str | None:
        return _check_isin(v)

    @field_validator("reviewed_date")
    @classmethod
    def _reviewed(cls, v: date) -> date:
        _check_not_future(v, "Prüfdatum")
        return v


@dataclass(frozen=True)
class SourcedEvidence:
    """Sachverhalt plus Herkunft im eigenen System (Quelle, Datenstand, Importzeit).

    Damit lässt sich jede angezeigte Feststellung auf einen konkreten, versionierten
    Datenstand zurückführen.
    """

    record: EvidenceRecord
    source_key: str
    version_id: int | None = None
    version_hash: str | None = None
    imported_at: datetime | None = None


@dataclass(frozen=True)
class SourcedCoverage:
    record: CoverageRecord
    source_key: str  # die Abdeckungsquelle
    covers_source_key: str | None = None  # Sachverhaltsquelle, deren Abdeckung sie belegt
