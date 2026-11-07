"""SQLAlchemy-Datenmodell.

Versionierung: Jeder importierte Datensatz gehört zu genau einer ``DatasetVersion``.
Pro Quelle ist höchstens eine Version ``active``. Ein Update schreibt eine NEUE
Version und schaltet erst nach erfolgreicher Validierung und vollständigem
Schreiben in einer Transaktion um. Alte Versionen bleiben als ``superseded``
erhalten (Nachvollziehbarkeit). Fehlerhafte Daten erzeugen keine Version, nur
einen ``UpdateRun`` mit Status ``fehlgeschlagen``.

Verweise zwischen Datensätzen laufen über stabile fachliche Schlüssel
(``company_key``, ISIN), nicht über Datenbank-IDs, damit Versionen unabhängig
voneinander ausgetauscht werden können.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from transparenz.utils.timeutil import utcnow


class Base(DeclarativeBase):
    pass


class Source(Base):
    """Registrierte Datenquelle (Spiegel der Konfiguration + Lizenzangaben)."""

    __tablename__ = "sources"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(32))
    publisher: Mapped[str] = mapped_column(String(255))
    location: Mapped[str] = mapped_column(Text)
    license: Mapped[str] = mapped_column(Text)
    commercial_use: Mapped[str] = mapped_column(String(16))
    is_fictional: Mapped[bool] = mapped_column(Boolean)
    interval_hours: Mapped[float] = mapped_column(Float)
    max_age_days: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_key: Mapped[str] = mapped_column(ForeignKey("sources.key"), index=True)
    status: Mapped[str] = mapped_column(String(16), index=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    fetched_at: Mapped[datetime] = mapped_column(DateTime)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, default=0)
    data_as_of: Mapped[date | None] = mapped_column(Date, nullable=True)
    raw_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    etag: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_modified: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (Index("ix_versions_source_status", "source_key", "status"),)


class UpdateRun(Base):
    """Protokoll jedes Aktualisierungsversuchs – auch fehlgeschlagener."""

    __tablename__ = "update_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_key: Mapped[str] = mapped_column(ForeignKey("sources.key"), index=True)
    trigger: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dataset_version_id: Mapped[int | None] = mapped_column(
        ForeignKey("dataset_versions.id"), nullable=True
    )
    message: Mapped[str] = mapped_column(Text, default="")
    errors_json: Mapped[str] = mapped_column(Text, default="[]")
    warnings_json: Mapped[str] = mapped_column(Text, default="[]")
    raw_path: Mapped[str | None] = mapped_column(Text, nullable=True)


class _Versioned:
    dataset_version_id: Mapped[int] = mapped_column(
        ForeignKey("dataset_versions.id"), index=True
    )


class FundRow(_Versioned, Base):
    __tablename__ = "funds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    isin: Mapped[str] = mapped_column(String(12), index=True)
    name: Mapped[str] = mapped_column(String(255))
    provider: Mapped[str] = mapped_column(String(255))
    as_of_date: Mapped[date] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(3))
    description: Mapped[str] = mapped_column(Text, default="")
    is_fictional: Mapped[bool] = mapped_column(Boolean, default=False)


class HoldingRow(_Versioned, Base):
    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fund_isin: Mapped[str] = mapped_column(String(12), index=True)
    isin: Mapped[str | None] = mapped_column(String(12), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    asset_class: Mapped[str] = mapped_column(String(32))
    weight_pct: Mapped[float] = mapped_column(Float)
    country: Mapped[str | None] = mapped_column(String(64), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)


class CompanyRow(_Versioned, Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_key: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(255))
    lei: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    country: Mapped[str | None] = mapped_column(String(64), nullable=True)


class SecurityRow(_Versioned, Base):
    __tablename__ = "securities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    isin: Mapped[str] = mapped_column(String(12), index=True)
    name: Mapped[str] = mapped_column(String(255))
    issuer_company_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mapping_method: Mapped[str] = mapped_column(String(32))
    mapping_confidence: Mapped[str] = mapped_column(String(16))
    mapping_source: Mapped[str] = mapped_column(Text)


class RelationshipRow(_Versioned, Base):
    __tablename__ = "company_relationships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    parent_key: Mapped[str] = mapped_column(String(64), index=True)
    child_key: Mapped[str] = mapped_column(String(64), index=True)
    relationship_type: Mapped[str] = mapped_column(String(32))
    verified: Mapped[bool] = mapped_column(Boolean)
    source: Mapped[str] = mapped_column(Text)
    ownership_pct: Mapped[float | None] = mapped_column(Float, nullable=True)


class EvidenceRow(_Versioned, Base):
    """Sachverhalt gemäss Belegmodell."""

    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evidence_id: Mapped[str] = mapped_column(String(128), index=True)
    company_name: Mapped[str] = mapped_column(String(255))
    lei: Mapped[str | None] = mapped_column(String(20), nullable=True)
    isin: Mapped[str | None] = mapped_column(String(12), nullable=True)
    criterion: Mapped[str] = mapped_column(String(64), index=True)
    description: Mapped[str] = mapped_column(Text)
    evidence_type: Mapped[str] = mapped_column(String(64))
    proceeding_status: Mapped[str] = mapped_column(String(32))
    publisher: Mapped[str] = mapped_column(String(255))
    publisher_type: Mapped[str] = mapped_column(String(32))
    source_title: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text)
    published_date: Mapped[date] = mapped_column(Date)
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    verification_level: Mapped[str] = mapped_column(String(32))
    last_reviewed: Mapped[date | None] = mapped_column(Date, nullable=True)
    metric_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    metric_unit: Mapped[str | None] = mapped_column(String(16), nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class CoverageRow(_Versioned, Base):
    __tablename__ = "coverage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_name: Mapped[str] = mapped_column(String(255))
    lei: Mapped[str | None] = mapped_column(String(20), nullable=True)
    isin: Mapped[str | None] = mapped_column(String(12), nullable=True)
    criterion: Mapped[str] = mapped_column(String(64))
    reviewed_date: Mapped[date] = mapped_column(Date)
