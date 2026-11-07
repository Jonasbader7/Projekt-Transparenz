"""Laden und Validieren der Quellen- und Kriterienkonfiguration (TOML)."""

from __future__ import annotations

import tomllib
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from transparenz.entities.enums import CommercialUse, DatasetKind


class Criterion(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str = Field(pattern=r"^[a-z0-9_]+$")
    name: str
    description: str
    severity: Literal["schwer", "hoch"]
    metric: str | None = None
    metric_unit: str | None = None
    threshold: float | None = None
    threshold_note: str = ""


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
    fetcher: Literal["local", "http", "gleif_api"]
    format: Literal["json", "csv", "gleif_json"]
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
    attribution: str = ""
    description: str = ""
    coverage_of: str | None = None
    # nur fetcher = "gleif_api": Textdatei mit den abzufragenden LEIs (relativ zum Projekt)
    lei_list: str | None = None
    enabled: bool = True

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
        return self


class Catalog(BaseModel):
    model_config = ConfigDict(frozen=True)

    defaults: UpdateDefaults
    sources: tuple[SourceConfig, ...]
    criteria: tuple[Criterion, ...]

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


def load_criteria(path: Path) -> tuple[Criterion, ...]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return tuple(Criterion(**c) for c in data.get("criterion", []))


def load_catalog(sources_path: Path, criteria_path: Path) -> Catalog:
    data = tomllib.loads(sources_path.read_text(encoding="utf-8"))
    return Catalog(
        defaults=UpdateDefaults(**data.get("defaults", {})),
        sources=tuple(SourceConfig(**s) for s in data.get("source", [])),
        criteria=load_criteria(criteria_path),
    )
