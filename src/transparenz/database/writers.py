"""Schreiben validierter Datensätze in eine (noch nicht aktive) Datensatz-Version."""

from __future__ import annotations

from sqlalchemy.orm import Session

from transparenz.database.models import (
    CompanyRow,
    CoverageRow,
    EvidenceRow,
    FundRow,
    HoldingRow,
    RelationshipRow,
    SecurityRow,
)
from transparenz.entities.enums import DatasetKind
from transparenz.ingestion.parsing import ParsedDataset
from transparenz.utils.timeutil import utcnow


def write_dataset(session: Session, version_id: int, parsed: ParsedDataset) -> int:
    """Fügt alle Datensätze ein. Kein Commit – das macht der Aufrufer (Transaktion)."""
    rows: list[object] = []
    r = parsed.records
    if parsed.kind == DatasetKind.HOLDINGS:
        fund = r["funds"][0]
        rows.append(FundRow(dataset_version_id=version_id, **fund.model_dump()))
        rows.extend(
            HoldingRow(
                dataset_version_id=version_id,
                fund_isin=fund.isin,
                **p.model_dump(mode="python"),
            )
            for p in r["positions"]
        )
    elif parsed.kind == DatasetKind.ENTITIES:
        rows.extend(
            CompanyRow(dataset_version_id=version_id, **c.model_dump()) for c in r["companies"]
        )
        rows.extend(
            SecurityRow(dataset_version_id=version_id, **s.model_dump()) for s in r["securities"]
        )
        rows.extend(
            RelationshipRow(dataset_version_id=version_id, **x.model_dump())
            for x in r["relationships"]
        )
    elif parsed.kind == DatasetKind.EVIDENCE:
        now = utcnow()
        rows.extend(
            EvidenceRow(dataset_version_id=version_id, imported_at=now, **e.model_dump())
            for e in r["evidence"]
        )
    elif parsed.kind == DatasetKind.COVERAGE:
        rows.extend(
            CoverageRow(dataset_version_id=version_id, **c.model_dump()) for c in r["coverage"]
        )
    else:  # pragma: no cover - durch Enum abgesichert
        raise ValueError(f"Unbekannte Datensatzart: {parsed.kind}")
    session.add_all(rows)
    session.flush()
    return len(rows)
