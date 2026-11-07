# Architektur

Modularer Python-Monolith (keine Microservices). Paket `transparenz` im `src/`-Layout.

```text
Datenquelle (Datei/HTTP)
   │  ingestion/fetchers.py      Abruf, Wiederholungen bei vorübergehenden Fehlern
   ▼
ingestion/parsing.py             Parsen + Validierung (Pydantic) → ParsedDataset
   │  Fehler? → ganzer Datenstand abgelehnt, alter Stand bleibt aktiv
   ▼
services/update_manager.py       Versionierung, Transaktion, Protokoll (UpdateRun)
   ▼
database/ (SQLAlchemy, SQLite)   Datensätze je DatasetVersion; nur «active» wird gelesen
   ▼
database/repository.py           aktiver Datenstand → Domänenobjekte
   ▼
screening/engine.py              Belegmodell: Status pro Position × Kriterium (rein funktional)
   ▼
reports/                         quellenbasierte Texte, Tabellen, Markdown/CSV-Export
   ▼
site/ (statische Website, Hauptoberfläche) · app/ (Streamlit, lokal) · cli.py
```

## Module

| Ordner | Inhalt |
|---|---|
| `config/` | `settings.py` (einzige Stelle für den Anzeigenamen), `sources.toml`, `criteria.toml`, Katalog-Modelle |
| `entities/` | Aufzählungen, Anzeigetexte, ISIN/LEI-Prüfung, Pydantic-Datensätze, Unternehmenszuordnung |
| `ingestion/` | Fetcher (lokal, HTTP mit ETag), Parser je Datenart, Adapter je Quelle |
| `database/` | ORM-Modelle, Session, Schreiben (`writers.py`), Lesen (`repository.py`) |
| `screening/` | Screening-Engine |
| `reports/` | Texte («Laut Gerichtsurteil … vom …»), Tabellen, Markdown-Bericht |
| `services/` | `DataUpdateManager`, `AppContext` (Zusammenbau für CLI, App, Tests) |
| `utils/` | Zeit, Logging |
| `site/` (Modul) | Website-Generator: Jinja2-Vorlagen → statische HTML-Seiten im Ordner `site/` (Schnappschuss, keine Logik im Browser) |
| später | `portfolios/`, `analytics/`, `ai/` – bewusst noch nicht angelegt |

Abweichungen vom ursprünglichen Ordnervorschlag sind in `DECISIONS.md` begründet
(u. a. `app/views/` statt `app/pages/`, CLI statt einzelner Skripte).

## Update-System

`DataUpdateManager` (`services/update_manager.py`):

- **ein Adapter pro Quelle** (`ingestion/adapters.py`), konfiguriert in `config/sources.toml`
- **Intervalle** pro Quelle (`interval_hours`), Fälligkeit ab letzter erfolgreicher Prüfung
- **neue Datenstände erkennen:** SHA-256 des Inhalts; bei HTTP zusätzlich ETag/Last-Modified (304)
- **Validierung** vollständig vor dem Schreiben; ein Fehler lehnt die ganze Datei ab
- **Duplikaterkennung** im Parser (exakt, widersprüchlich, inhaltlich)
- **Versionierung:** jede Aktualisierung = neue `DatasetVersion`; Umschalten in EINER Transaktion
- **Logging + Protokoll:** jeder Versuch als `UpdateRun` mit Status, Fehlerliste, Versuchen
- **begrenzte Wiederholungen:** Standard 3 Versuche, exponentielles Warten, nur bei
  vorübergehenden Fehlern (Timeout, 5xx, 429)
- **Aktualität:** `freshness()` liefert Datenstand, letzte Prüfung, Alter und «veraltet»
  (Alter > `max_age_days`); sichtbar auf der Seite «Datenquellen & Aktualität»
- **manueller Auslöser:** CLI `python -m transparenz update` und Button in der App

**Wichtigste Regel:** Fehlerhafte neue Daten überschreiben nie den letzten gültigen Stand.
Getestet in `tests/test_update_manager.py` (ungültige Daten, Abbruch beim Schreiben mit
Rollback, Wiederholungen) und `tests/test_end_to_end.py`.

### Wo die Daten dauerhaft liegen

| Was | Wo | Im Git? |
|---|---|---|
| Datenbank | `data/processed/transparenz.sqlite` (lokal) | nein |
| Rohdaten-Schnappschüsse | `data/raw/<quelle>/`, abgelehnte unter `abgelehnt/` | nein |
| Fiktive Beispieldaten | `data/sample/` | ja |

**GitHub Actions ist kein dauerhafter Speicher.** Der Workflow `update-data.yml` ist nur
manuell auslösbar und legt das Ergebnis 7 Tage als Artefakt ab. Für automatische Updates braucht
es zuerst einen dauerhaften Speicher (z. B. verwaltete PostgreSQL-Datenbank oder Objektspeicher)
– das verursacht Kosten und wird erst nach Rücksprache eingerichtet. Bis dahin: lokal ausführen.

## Datenbank

SQLite lokal; die URL ist über `TRANSPARENZ_DATABASE_URL` konfigurierbar (PostgreSQL später).
Schema wird mit `create_all` angelegt. Vor dem ersten echten, dauerhaften Datenbestand werden
Migrationen (Alembic) eingeführt.

## Erweiterbarkeit (vorbereitet, nicht gebaut)

- **Echte Quellen:** neuer Parser/Adapter, der ins interne Format übersetzt (siehe `DATA_MODEL.md`)
- **Portfolio-Upload, Fondsvergleich:** Engine arbeitet bereits auf beliebigen Positionslisten
- **B2B/API:** `AppContext` kapselt Zugriff; eine API-Schicht kann ihn wiederverwenden
- **Öffentliche Demo:** nur fiktive Daten im Repo; Streamlit läuft nicht auf GitHub Pages –
  Optionen: Streamlit Community Cloud oder statischer Export des Markdown-Berichts
