"""Gemeinsame Test-Hilfen. Tests schreiben nie in den Projektordner (nur tmp_path)."""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from datetime import date
from pathlib import Path

import pytest

from transparenz.config.catalog import Catalog, Criterion, load_catalog
from transparenz.config.settings import CONFIG_DIR, get_settings
from transparenz.database.session import init_db, make_engine, make_session_factory
from transparenz.entities.enums import (
    Confidence,
    EvidenceType,
    MappingMethod,
    ProceedingStatus,
    PublisherType,
    VerificationLevel,
)
from transparenz.entities.identifiers import make_isin, make_lei
from transparenz.entities.models import (
    CompanyRecord,
    CoverageRecord,
    EvidenceRecord,
    SecurityRecord,
    SourcedCoverage,
    SourcedEvidence,
)

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "sample"
FUND_ISIN = make_isin("ZZFIKETF001")


@pytest.fixture
def catalog() -> Catalog:
    return load_catalog(CONFIG_DIR / "sources.toml", CONFIG_DIR / "criteria.toml")


@pytest.fixture
def session_factory(tmp_path: Path):  # type: ignore[no-untyped-def]
    engine = make_engine(f"sqlite:///{(tmp_path / 'test.sqlite').as_posix()}")
    init_db(engine)
    yield make_session_factory(engine)
    engine.dispose()


@pytest.fixture
def isolated_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Kopiert die Beispieldaten nach tmp und richtet eine eigene sources.toml darauf aus.

    So läuft der komplette Import (CSV/JSON → Validierung → DB) ohne den
    Projektordner zu verändern.
    """
    data = tmp_path / "daten"
    shutil.copytree(SAMPLE, data)
    toml = (CONFIG_DIR / "sources.toml").read_text(encoding="utf-8")
    toml = toml.replace('location = "data/sample/', f'location = "{data.as_posix()}/')
    sources = tmp_path / "sources.toml"
    sources.write_text(toml, encoding="utf-8")
    db_url = f"sqlite:///{(tmp_path / 'e2e.sqlite').as_posix()}"
    monkeypatch.setenv("TRANSPARENZ_DATABASE_URL", db_url)
    monkeypatch.setenv("TRANSPARENZ_SOURCES_CONFIG", str(sources))
    monkeypatch.setenv("TRANSPARENZ_RAW_DIR", str(tmp_path / "raw"))
    get_settings.cache_clear()
    yield data
    get_settings.cache_clear()


# ---------------------------------------------------------------- Bausteine
def criterion(key: str = "kohle", threshold: float | None = None, metric: str | None = None):
    return Criterion(
        key=key, name=key.capitalize(), description="Testkriterium", severity="hoch",
        metric=metric, metric_unit="%" if metric else None, threshold=threshold,
    )


def company(key: str, name: str | None = None, lei: bool = True) -> CompanyRecord:
    base = f"FIKT00{key.upper():0>12}"[:18]
    return CompanyRecord(company_key=key, name=name or f"Testfirma {key} AG",
                         lei=make_lei(base) if lei else None, country="CH")


def security(c: CompanyRecord, confidence: Confidence = Confidence.HOCH) -> SecurityRecord:
    body = f"ZZ{c.company_key.upper():0>9}"[:11]
    method = MappingMethod.NAME if confidence == Confidence.TIEF else MappingMethod.REGISTER
    return SecurityRecord(isin=make_isin(body), name=f"{c.name} Aktie",
                          issuer_company_key=c.company_key, mapping_method=method,
                          mapping_confidence=confidence, mapping_source="Test")


_counter = {"n": 0}


def evidence(
    c: CompanyRecord | None,
    *,
    crit: str = "kohle",
    etype: EvidenceType = EvidenceType.VORWURF,
    ptype: PublisherType = PublisherType.NGO,
    publisher: str = "Test-NGO",
    status: ProceedingStatus = ProceedingStatus.NICHT_ANWENDBAR,
    verification: VerificationLevel = VerificationLevel.QUELLE_GESICHTET,
    use_lei: bool = True,
    name: str | None = None,
    lei: str | None = None,
    metric: tuple[str, float] | None = None,
    reviewed: date | None = date(2026, 10, 1),
) -> SourcedEvidence:
    _counter["n"] += 1
    rec = EvidenceRecord(
        evidence_id=f"T-{_counter['n']}",
        company_name=name or (c.name if c else "Unbekannt AG"),
        lei=lei or (c.lei if (c and use_lei) else None),
        criterion=crit,
        description="Testbeschreibung eines Sachverhalts.",
        evidence_type=etype,
        proceeding_status=status,
        publisher=publisher,
        publisher_type=ptype,
        source_title="Testdokument",
        source_url="https://example.org/test",
        published_date=date(2026, 1, 15),
        verification_level=verification,
        last_reviewed=reviewed,
        metric_name=metric[0] if metric else None,
        metric_value=metric[1] if metric else None,
        metric_unit="%" if metric else None,
    )
    return SourcedEvidence(rec, "test_quelle", version_id=1, version_hash="abc123",
                           imported_at=None)


def coverage_for(c: CompanyRecord, crit: str = "kohle", by_name: bool = False) -> SourcedCoverage:
    rec = CoverageRecord(company_name=c.name, lei=None if by_name else c.lei, criterion=crit,
                         reviewed_date=date(2026, 9, 1))
    return SourcedCoverage(rec, "test_abdeckung", "test_quelle")
