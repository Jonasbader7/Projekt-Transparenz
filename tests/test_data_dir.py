"""Datenordner ausserhalb des Projekts (TRANSPARENZ_DATA_DIR) und alte Pfadangaben."""

from __future__ import annotations

from pathlib import Path

import pytest

from transparenz.config import settings as s


def test_foreign_root_never_redirected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRANSPARENZ_DATA_DIR", str(tmp_path / "anderswo"))
    monkeypatch.setenv("TRANSPARENZ_PROJECT_ROOT", str(tmp_path))
    assert s.local_data_dir(tmp_path) == tmp_path / "data"
    assert s.local_data_dir() == tmp_path / "data"  # auch über TRANSPARENZ_PROJECT_ROOT nicht


def test_project_root_uses_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    assert s._CODE_ROOT is not None
    monkeypatch.setenv("TRANSPARENZ_DATA_DIR", str(tmp_path / "daten"))
    assert s.local_data_dir(s._CODE_ROOT) == (tmp_path / "daten").resolve()


def test_project_root_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(s, "_load_dotenv", lambda path: None)
    monkeypatch.delenv("TRANSPARENZ_DATA_DIR", raising=False)
    assert s._CODE_ROOT is not None
    assert s.local_data_dir(s._CODE_ROOT) == s._CODE_ROOT / "data"


@pytest.mark.parametrize("stored", [
    r"data\raw\external\x\a.json", "data/raw/external/x/a.json", "raw/external/x/a.json"])
def test_resolve_data_path_old_and_new(tmp_path: Path, stored: str) -> None:
    assert s.resolve_data_path(stored, tmp_path) == tmp_path / "data/raw/external/x/a.json"


def test_resolve_data_path_keeps_absolute(tmp_path: Path) -> None:
    target = tmp_path / "irgendwo.zip"
    assert s.resolve_data_path(target, tmp_path) == target


def test_resolve_moved_absolute_path(tmp_path: Path) -> None:
    moved = tmp_path / "data/raw/external/manifests/x/a.json"
    moved.parent.mkdir(parents=True)
    moved.write_text("{}", encoding="utf-8")
    # absoluter Pfad am früheren Ort (plattformunabhängig, existiert nicht mehr)
    old = tmp_path / "alt/OneDrive/Projekt/data/raw/external/manifests/x/a.json"
    assert s.resolve_data_path(old, tmp_path) == moved
    missing = tmp_path / "alt/OneDrive/Projekt/data/raw/fehlt.json"
    assert s.resolve_data_path(missing, tmp_path) == missing  # nichts erfinden
