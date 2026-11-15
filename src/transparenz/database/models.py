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


class MarketRecordRow(Base):
    """Source observations, distinct from verified ISIN-based screening securities."""

    __tablename__ = "market_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_version_id: Mapped[int] = mapped_column(ForeignKey("dataset_versions.id"), index=True)
    record_type: Mapped[str] = mapped_column(String(32))
    record_key: Mapped[str] = mapped_column(String(255))
    payload_json: Mapped[str] = mapped_column(Text)
    __table_args__ = (Index("ix_market_version_key", "dataset_version_id", "record_type",
                            "record_key", unique=True),)


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
    # Ergänzt am 14.11.2026 (D-047); beim Start in bestehenden Datenbanken nachgetragen.
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    consequences_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class CoverageRow(_Versioned, Base):
    __tablename__ = "coverage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_name: Mapped[str] = mapped_column(String(255))
    lei: Mapped[str | None] = mapped_column(String(20), nullable=True)
    isin: Mapped[str | None] = mapped_column(String(12), nullable=True)
    criterion: Mapped[str] = mapped_column(String(64))
    reviewed_date: Mapped[date] = mapped_column(Date)


# --------------------------------------------------------------------- SEC N-PORT (D-054)
# Eigene Tabellen statt JSON-Zeilen: rund 5.6 Mio. Positionen je Quartal. Eindeutige
# Indizes prüfen die Primärschlüssel der SEC-Readme beim Schreiben (Verstoss = Rollback).


class NportSubmissionRow(_Versioned, Base):
    __tablename__ = "nport_submissions"
    __table_args__ = (Index("ux_nport_submission", "dataset_version_id", "quarter", "accession",
                            unique=True),
                      Index("ix_nport_submission_series", "dataset_version_id", "series_id"))

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quarter: Mapped[str] = mapped_column(String(6))
    accession: Mapped[str] = mapped_column(String(20))
    filing_date: Mapped[date] = mapped_column(Date)
    sub_type: Mapped[str] = mapped_column(String(15))
    report_date: Mapped[date] = mapped_column(Date)
    fiscal_year_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_last_filing: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    cik: Mapped[str | None] = mapped_column(String(10), nullable=True)
    registrant_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    registrant_lei_reported: Mapped[str | None] = mapped_column(Text, nullable=True)
    registrant_lei: Mapped[str | None] = mapped_column(String(20), nullable=True)
    series_id: Mapped[str | None] = mapped_column(String(10), nullable=True)
    series_id_reported: Mapped[str | None] = mapped_column(Text, nullable=True)
    series_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    series_lei_reported: Mapped[str | None] = mapped_column(Text, nullable=True)
    series_lei: Mapped[str | None] = mapped_column(String(20), nullable=True)
    total_assets: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_assets: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Serien-ID, sonst «CIK» + CIK des Registranten; leer = nicht bestimmbar (fund_keys)
    fund_key: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # current | superseded | earlier_period | tie | no_series | notice (sec_nport.py)
    selection: Mapped[str] = mapped_column(String(16))


class NportHoldingRow(_Versioned, Base):
    __tablename__ = "nport_holdings"
    __table_args__ = (Index("ux_nport_holding", "dataset_version_id", "quarter", "holding_id",
                            unique=True),
                      Index("ix_nport_holding_accession", "dataset_version_id", "accession"))

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quarter: Mapped[str] = mapped_column(String(6))
    accession: Mapped[str] = mapped_column(String(20))
    holding_id: Mapped[int] = mapped_column(Integer)
    issuer_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    issuer_lei_reported: Mapped[str | None] = mapped_column(Text, nullable=True)
    issuer_lei: Mapped[str | None] = mapped_column(String(20), nullable=True)
    issuer_lei_status: Mapped[str] = mapped_column(String(16))
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    cusip: Mapped[str | None] = mapped_column(Text, nullable=True)
    balance: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(16), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    exchange_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    payoff_profile: Mapped[str | None] = mapped_column(String(16), nullable=True)
    asset_cat: Mapped[str | None] = mapped_column(String(16), nullable=True)
    issuer_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    country: Mapped[str | None] = mapped_column(String(16), nullable=True)
    is_restricted: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    fair_value_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    derivative_cat: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # Aus nport_identifiers abgeleitet (eine gültige ISIN je Position oder Status).
    isin: Mapped[str | None] = mapped_column(String(12), nullable=True)
    isin_status: Mapped[str | None] = mapped_column(String(16), nullable=True)


class NportIdentifierRow(_Versioned, Base):
    __tablename__ = "nport_identifiers"
    __table_args__ = (Index("ux_nport_identifier", "dataset_version_id", "quarter", "holding_id",
                            "identifier_id", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quarter: Mapped[str] = mapped_column(String(6))
    holding_id: Mapped[int] = mapped_column(Integer)
    identifier_id: Mapped[int] = mapped_column(Integer)
    isin_reported: Mapped[str | None] = mapped_column(Text, nullable=True)
    isin: Mapped[str | None] = mapped_column(String(12), nullable=True)
    isin_status: Mapped[str] = mapped_column(String(16))
    ticker: Mapped[str | None] = mapped_column(Text, nullable=True)
    other_identifier: Mapped[str | None] = mapped_column(Text, nullable=True)
    other_identifier_desc: Mapped[str | None] = mapped_column(Text, nullable=True)


class NportLoadStatRow(_Versioned, Base):
    """Gelesene, übernommene und abgelehnte Zeilen je Tabelle und Quartal."""

    __tablename__ = "nport_load_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quarter: Mapped[str] = mapped_column(String(6))
    table_name: Mapped[str] = mapped_column(String(64))
    rows_read: Mapped[int] = mapped_column(Integer)
    rows_accepted: Mapped[int] = mapped_column(Integer)
    rejected_json: Mapped[str] = mapped_column(Text, default="{}")
