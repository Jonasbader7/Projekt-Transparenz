"""Zusammenbau der Anwendung: Einstellungen → Katalog → Datenbank → Services.

Eine Stelle, die CLI, Streamlit-App und Tests gleichermassen nutzen.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from transparenz.config.catalog import Catalog, load_catalog
from transparenz.config.settings import Settings, get_settings
from transparenz.database.repository import ActiveData, load_active_data
from transparenz.database.session import init_db, make_engine, make_session_factory
from transparenz.entities.enums import DatasetKind
from transparenz.screening.engine import FundScreeningResult, ScreeningEngine
from transparenz.services.update_manager import DataUpdateManager
from transparenz.utils.timeutil import format_date, utcnow


@dataclass
class AppContext:
    settings: Settings
    catalog: Catalog
    engine: Engine
    session_factory: sessionmaker[Session]
    updates: DataUpdateManager

    @property
    def source_names(self) -> dict[str, str]:
        return {s.key: s.name for s in self.catalog.sources}

    @property
    def coverage_of(self) -> dict[str, str]:
        return {
            s.key: s.coverage_of
            for s in self.catalog.sources
            if s.kind == DatasetKind.COVERAGE and s.coverage_of
        }

    def active_data(self) -> ActiveData:
        with self.session_factory() as session:
            return load_active_data(session, self.coverage_of)

    def analyze_fund(
        self, fund_isin: str, as_of: date | None = None, data: ActiveData | None = None
    ) -> FundScreeningResult | None:
        data = data or self.active_data()
        snap = data.funds.get(fund_isin)
        if snap is None:
            return None
        engine = ScreeningEngine(
            criteria=self.catalog.criteria,
            companies=data.companies,
            securities=data.securities,
            relationships=data.relationships,
            evidence=data.evidence,
            coverage=data.coverage,
            source_names=self.source_names,
        )
        return engine.screen_fund(snap.fund, snap.positions, as_of or utcnow().date())

    def data_version_lines(self, data: ActiveData) -> list[str]:
        lines = []
        names = self.source_names
        for key, v in sorted(data.versions.items()):
            lines.append(
                f"{names.get(key, key)}: Version #{v.id}, Datenstand "
                f"{format_date(v.data_as_of)}, abgerufen {format_date(v.fetched_at)}, "
                f"Hash {v.content_hash[:10]}"
            )
        return lines


def create_context(settings: Settings | None = None) -> AppContext:
    settings = settings or get_settings()
    catalog = load_catalog(settings.sources_config, settings.criteria_config)
    engine = make_engine(settings.database_url)
    init_db(engine)
    session_factory = make_session_factory(engine)
    updates = DataUpdateManager(
        session_factory=session_factory,
        catalog=catalog,
        project_root=settings.project_root,
        raw_dir=settings.raw_dir,
        user_agent=settings.http_user_agent,
    )
    return AppContext(settings, catalog, engine, session_factory, updates)
