"""Zentrale Einstellungen.

Der Anzeigename des Produkts ist an genau EINER Stelle definiert:
``DEFAULT_DISPLAY_NAME`` unten. Er kann über die Umgebungsvariable
``TRANSPARENZ_DISPLAY_NAME`` (oder eine lokale ``.env``) überschrieben werden.
Alle anderen Module lesen ihn über ``get_settings().display_name``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DEFAULT_DISPLAY_NAME = "Projekt Transparenz"

CONFIG_DIR = Path(__file__).resolve().parent


def _find_project_root() -> Path:
    env = os.environ.get("TRANSPARENZ_PROJECT_ROOT")
    if env:
        return Path(env).resolve()
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd().resolve()


def _load_dotenv(path: Path) -> None:
    """Minimaler .env-Leser (KEY=VALUE). Bereits gesetzte Variablen haben Vorrang."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value


@dataclass(frozen=True)
class Settings:
    display_name: str
    project_root: Path
    database_url: str
    log_level: str
    http_user_agent: str
    sources_config: Path
    criteria_config: Path
    raw_dir: Path  # Rohdaten-Schnappschüsse jedes Abrufs

    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def sample_dir(self) -> Path:
        return self.data_dir / "sample"

    @property
    def docs_dir(self) -> Path:
        return self.project_root / "docs"


def load_settings() -> Settings:
    """Liest die Einstellungen frisch aus Umgebung und .env (ohne Cache)."""
    root = _find_project_root()
    _load_dotenv(root / ".env")
    default_db = root / "data" / "processed" / "transparenz.sqlite"
    return Settings(
        display_name=os.environ.get("TRANSPARENZ_DISPLAY_NAME") or DEFAULT_DISPLAY_NAME,
        project_root=root,
        database_url=os.environ.get("TRANSPARENZ_DATABASE_URL")
        or f"sqlite:///{default_db.as_posix()}",
        log_level=(os.environ.get("TRANSPARENZ_LOG_LEVEL") or "INFO").upper(),
        http_user_agent=os.environ.get("TRANSPARENZ_HTTP_USER_AGENT")
        or "ProjektTransparenz/0.1 (+https://github.com/Jonasbader7/Projekt-Transparenz)",
        sources_config=Path(
            os.environ.get("TRANSPARENZ_SOURCES_CONFIG") or CONFIG_DIR / "sources.toml"
        ),
        criteria_config=Path(
            os.environ.get("TRANSPARENZ_CRITERIA_CONFIG") or CONFIG_DIR / "criteria.toml"
        ),
        raw_dir=Path(os.environ.get("TRANSPARENZ_RAW_DIR") or root / "data" / "raw"),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Gecachte Einstellungen. In Tests ``get_settings.cache_clear()`` aufrufen."""
    return load_settings()
