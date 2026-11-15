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


_CODE_ROOT: Path | None = next(
    (p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").exists()), None
)


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


_DATA_SUBDIRS = ("raw", "processed", "cache", "review")


def local_data_dir(project_root: Path | None = None) -> Path:
    """Ordner für grosse, nicht versionierte Daten (``raw``, ``processed``, ``cache``, ``review``).

    Standard: ``<Projekt>/data``. Für den echten Projektordner kann ``TRANSPARENZ_DATA_DIR``
    (Umgebung oder ``.env``) einen Ort ausserhalb von OneDrive setzen. Ein anderer Wurzelordner,
    etwa ``tmp_path`` in Tests, bleibt immer bei ``<root>/data`` – Tests berühren so nie die
    echten Daten. Versionierte Dateien (``data/sample``, ``data/queries``, ``data/gleif``)
    bleiben im Projektordner.
    """
    real_root = _CODE_ROOT  # bewusst nicht TRANSPARENZ_PROJECT_ROOT: Testordner nie umleiten
    root = (project_root or _find_project_root()).resolve()
    if real_root is not None and root == real_root:
        _load_dotenv(real_root / ".env")
        override = os.environ.get("TRANSPARENZ_DATA_DIR")
        if override:
            return Path(override).resolve()
    return root / "data"


def resolve_data_path(stored: str | Path, project_root: Path | None = None) -> Path:
    """Löst einen gespeicherten oder eingegebenen Datenpfad auf.

    Ältere Zeiger und Befehle nennen Pfade relativ zum Projekt (``data\\raw\\…``); neue
    Zeiger relativ zum Datenordner (``raw/…``). Beide landen im aktuellen Datenordner.
    Ein absoluter Pfad bleibt, wie er ist, solange er existiert. Zeigt er auf den früheren
    Ort ``…\\data\\raw|processed|cache|review\\…``, der nach einem Umzug fehlt, wird der Rest
    im aktuellen Datenordner gesucht (Datenbankeinträge vor dem Umzug vom 15.11.2026).
    """
    path = Path(stored)
    if path.is_absolute():
        if path.exists():
            return path
        parts = path.parts
        for i in range(len(parts) - 2, -1, -1):
            if parts[i].lower() == "data" and parts[i + 1] in _DATA_SUBDIRS:
                moved = local_data_dir(project_root).joinpath(*parts[i + 1:])
                return moved if moved.exists() else path
        return path
    parts = Path(str(stored).replace("\\", "/")).parts
    if parts and parts[0] == "data":
        parts = parts[1:]
    return local_data_dir(project_root).joinpath(*parts)


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
        """Grosse, nicht versionierte Daten (siehe ``local_data_dir``)."""
        return local_data_dir(self.project_root)

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def sample_dir(self) -> Path:
        """Fiktive Beispieldaten, versioniert im Projektordner."""
        return self.project_root / "data" / "sample"

    @property
    def docs_dir(self) -> Path:
        return self.project_root / "docs"


def load_settings() -> Settings:
    """Liest die Einstellungen frisch aus Umgebung und .env (ohne Cache)."""
    root = _find_project_root()
    _load_dotenv(root / ".env")
    data = local_data_dir(root)
    default_db = data / "processed" / "transparenz.sqlite"
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
        raw_dir=Path(os.environ.get("TRANSPARENZ_RAW_DIR") or data / "raw"),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Gecachte Einstellungen. In Tests ``get_settings.cache_clear()`` aufrufen."""
    return load_settings()
