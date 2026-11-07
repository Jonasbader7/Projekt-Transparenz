"""Lesen des aktuell gültigen Datenstands (nur aktive Versionen)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from transparenz.database.models import (
    CompanyRow,
    CoverageRow,
    DatasetVersion,
    EvidenceRow,
    FundRow,
    HoldingRow,
    RelationshipRow,
    SecurityRow,
    UpdateRun,
)
from transparenz.entities.enums import VersionStatus
from transparenz.entities.models import (
    CompanyRecord,
    CoverageRecord,
    EvidenceRecord,
    FundInfo,
    Position,
    RelationshipRecord,
    SecurityRecord,
    SourcedCoverage,
    SourcedEvidence,
)

log = logging.getLogger(__name__)


@dataclass
class FundSnapshot:
    fund: FundInfo
    positions: list[Position]
    source_key: str
    version_id: int


@dataclass
class ActiveData:
    versions: dict[str, DatasetVersion] = field(default_factory=dict)
    funds: dict[str, FundSnapshot] = field(default_factory=dict)
    companies: list[CompanyRecord] = field(default_factory=list)
    securities: list[SecurityRecord] = field(default_factory=list)
    relationships: list[RelationshipRecord] = field(default_factory=list)
    evidence: list[SourcedEvidence] = field(default_factory=list)
    coverage: list[SourcedCoverage] = field(default_factory=list)


def active_versions(session: Session) -> dict[str, DatasetVersion]:
    rows = session.scalars(
        select(DatasetVersion).where(DatasetVersion.status == VersionStatus.ACTIVE.value)
    ).all()
    return {v.source_key: v for v in rows}


def load_active_data(session: Session, coverage_of: dict[str, str] | None = None) -> ActiveData:
    """Lädt alle Datensätze aktiver Versionen und validiert sie erneut als Domänenobjekte.

    ``coverage_of`` bildet Abdeckungsquelle → Sachverhaltsquelle ab (aus der Konfiguration).
    """
    coverage_of = coverage_of or {}
    versions = active_versions(session)
    by_id = {v.id: v for v in versions.values()}
    ids = list(by_id)
    data = ActiveData(versions=versions)
    if not ids:
        return data

    for fund_row in session.scalars(select(FundRow).where(FundRow.dataset_version_id.in_(ids))):
        holdings = session.scalars(
            select(HoldingRow)
            .where(HoldingRow.dataset_version_id == fund_row.dataset_version_id)
            .order_by(HoldingRow.weight_pct.desc(), HoldingRow.id)
        ).all()
        snap = FundSnapshot(
            fund=FundInfo.model_validate(fund_row),
            positions=[Position.model_validate(h) for h in holdings],
            source_key=by_id[fund_row.dataset_version_id].source_key,
            version_id=fund_row.dataset_version_id,
        )
        if snap.fund.isin in data.funds:
            log.warning("Fonds %s in mehreren aktiven Quellen – erste gewinnt.", snap.fund.isin)
            continue
        data.funds[snap.fund.isin] = snap

    seen_companies: set[str] = set()
    for row in session.scalars(
        select(CompanyRow).where(CompanyRow.dataset_version_id.in_(ids)).order_by(CompanyRow.id)
    ):
        if row.company_key in seen_companies:
            log.warning("Unternehmen %s doppelt in Stammdaten – erstes gewinnt.", row.company_key)
            continue
        seen_companies.add(row.company_key)
        data.companies.append(CompanyRecord.model_validate(row))

    seen_isins: set[str] = set()
    for row in session.scalars(
        select(SecurityRow).where(SecurityRow.dataset_version_id.in_(ids)).order_by(SecurityRow.id)
    ):
        if row.isin in seen_isins:
            continue
        seen_isins.add(row.isin)
        data.securities.append(SecurityRecord.model_validate(row))

    data.relationships = [
        RelationshipRecord.model_validate(r)
        for r in session.scalars(
            select(RelationshipRow).where(RelationshipRow.dataset_version_id.in_(ids))
        )
    ]
    data.evidence = [
        SourcedEvidence(
            record=EvidenceRecord.model_validate(r),
            source_key=by_id[r.dataset_version_id].source_key,
            version_id=r.dataset_version_id,
            version_hash=by_id[r.dataset_version_id].content_hash,
            imported_at=r.imported_at,
        )
        for r in session.scalars(
            select(EvidenceRow)
            .where(EvidenceRow.dataset_version_id.in_(ids))
            .order_by(EvidenceRow.id)
        )
    ]
    for r in session.scalars(select(CoverageRow).where(CoverageRow.dataset_version_id.in_(ids))):
        key = by_id[r.dataset_version_id].source_key
        data.coverage.append(
            SourcedCoverage(CoverageRecord.model_validate(r), key, coverage_of.get(key))
        )
    return data


def recent_runs(session: Session, limit: int = 50) -> list[UpdateRun]:
    return list(
        session.scalars(select(UpdateRun).order_by(UpdateRun.started_at.desc()).limit(limit))
    )
