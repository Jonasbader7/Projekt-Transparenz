"""Engine- und Session-Verwaltung. SQLite lokal, später PostgreSQL über die URL."""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from transparenz.database.models import Base

log = logging.getLogger(__name__)


def make_engine(database_url: str) -> Engine:
    if database_url.startswith("sqlite:///"):
        db_path = Path(database_url.removeprefix("sqlite:///"))
        if str(db_path) not in {"", ":memory:"}:
            db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(database_url, future=True)
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def _sqlite_pragmas(dbapi_conn, _record):  # type: ignore[no-untyped-def]
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.execute("PRAGMA journal_mode=WAL")
            cur.close()

    return engine


def init_db(engine: Engine) -> None:
    """Legt fehlende Tabellen an (idempotent). Migrationen folgen später (Alembic)."""
    Base.metadata.create_all(engine)
    log.info("Datenbankschema bereit (%s)", engine.url.render_as_string(hide_password=True))


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)
