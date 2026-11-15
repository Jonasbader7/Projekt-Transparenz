"""Neue, leer erlaubte Spalten werden in bestehenden Datenbanken nachgetragen (D-047)."""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from transparenz.database.session import add_missing_columns, init_db


def test_existing_database_gets_new_nullable_columns(tmp_path: Path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'alt.sqlite'}")
    init_db(engine)
    with engine.begin() as conn:  # alten Stand nachbilden: Spalten entfernen
        conn.execute(text('ALTER TABLE evidence DROP COLUMN "category"'))
        conn.execute(text('ALTER TABLE evidence DROP COLUMN "consequences_until"'))
    assert "category" not in {c["name"] for c in inspect(engine).get_columns("evidence")}
    added = add_missing_columns(engine)
    assert added == ["evidence.category", "evidence.consequences_until"]
    columns = {c["name"] for c in inspect(engine).get_columns("evidence")}
    assert {"category", "consequences_until"} <= columns
    assert add_missing_columns(engine) == []  # idempotent
