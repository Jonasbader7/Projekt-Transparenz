"""Engine- und Session-Verwaltung. SQLite lokal, später PostgreSQL über die URL."""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import Engine, create_engine, event, inspect, text
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


def add_missing_columns(engine: Engine) -> list[str]:
    """Trägt neue, leer erlaubte Spalten in bestehenden Tabellen nach (D-047).

    Nur additive Ergänzungen: keine Spalte wird geändert oder gelöscht, bestehende Zeilen
    erhalten «leer». Alles andere bleibt einer echten Migration vorbehalten.
    """
    added: list[str] = []
    with engine.begin() as conn:
        # Dieselbe Verbindung prüfen und ändern: SQLite liest den Schemastand je Verbindung.
        inspector = inspect(conn)
        existing_tables = set(inspector.get_table_names())
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue
            present = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in present:
                    continue
                if not column.nullable:
                    raise RuntimeError(f"Spalte {table.name}.{column.name} ist neu und darf "
                                       "nicht leer sein: braucht eine Migration.")
                kind = column.type.compile(dialect=engine.dialect)
                conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN '
                                  f'"{column.name}" {kind}'))
                added.append(f"{table.name}.{column.name}")
    return added


def init_db(engine: Engine) -> None:
    """Legt fehlende Tabellen an und ergänzt neue, leer erlaubte Spalten (idempotent)."""
    Base.metadata.create_all(engine)
    added = add_missing_columns(engine)
    if added:
        log.info("Spalten ergänzt: %s", ", ".join(added))
    log.info("Datenbankschema bereit (%s)", engine.url.render_as_string(hide_password=True))


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)
