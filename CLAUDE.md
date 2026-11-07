# CLAUDE.md – Projektgedächtnis «Projekt Transparenz»

## Mission
Fondspositionen mit nachvollziehbaren Quellen verbinden, damit Anleger:innen selbst beurteilen
können, ob ein nachhaltiger Fonds zu ihren Werten passt. Transparenz statt Greenwashing:
keine Scores, keine Urteile ohne Belege, keine Empfehlungen, keine Renditeversprechen.
Gründer: Jonas Bader (BFH Digital Business & AI, ex Bankberater). Nebenprojekt.

## Arbeitsregeln
- **Zu Beginn jeder Session:** `STATUS.md`, `docs/DECISIONS.md` und die letzten Einträge in
  `docs/LOG.md` lesen.
- **Am Ende jeder Session:** `STATUS.md` aktualisieren (Phase, Fortschritt, nächste 3 Schritte,
  offene Fragen), `docs/LOG.md` ergänzen (neueste oben), neue Entscheide in `docs/DECISIONS.md`,
  dann ein Git-Commit mit aussagekräftiger Nachricht.
- Deutsch, Schweizer Rechtschreibung (ss statt ß). Code-Bezeichner Englisch.
- Tests ausführen, bevor etwas als fertig gilt. Nicht ausgeführte oder fehlgeschlagene Tests
  ehrlich dokumentieren.
- **Priorität: Datenqualität und Nachvollziehbarkeit vor Funktionsumfang.** Keine neuen Features,
  solange die Grundlagen nicht zuverlässig laufen. Keine Platzhalterfunktionen, die fertig wirken.
- Vorher fragen: Kosten, Dateien ausserhalb des Projekts, Löschen, externe Dienste, Veröffentlichen
  (inkl. GitHub-Push).
- Niemals reale Daten erfinden. Fiktive Daten eindeutig kennzeichnen (ISIN `ZZ…`, LEI `FIKT00…`,
  `example.org`). ISIN (Wertpapier) ≠ LEI (Rechtsträger).
- Lizenz jeder Quelle prüfen und in `docs/DATA_SOURCES.md` festhalten. Keine unzulässigen Scraper.

## Architektur (Kurzfassung, Details in docs/ARCHITECTURE.md)
Python-Monolith, Paket `transparenz` (src-Layout):
`config/` → `ingestion/` (Fetcher, Parser, Adapter) → `services/update_manager.py` (Versionierung)
→ `database/` (SQLAlchemy/SQLite) → `screening/engine.py` (Belegmodell) → `reports/` →
`app/` (Streamlit) bzw. `cli.py`.

## Wichtige Pfade
| Pfad | Inhalt |
|---|---|
| `src/transparenz/config/settings.py` | **einzige Stelle für den Anzeigenamen** (`DEFAULT_DISPLAY_NAME`) |
| `src/transparenz/config/sources.toml` | Datenquellen, Intervalle, Lizenzen |
| `src/transparenz/config/criteria.toml` | Ausschlusskriterien, Schwellenwerte (offen) |
| `src/transparenz/screening/engine.py` | Belegstatus-Logik |
| `src/transparenz/services/update_manager.py` | DataUpdateManager |
| `site/` | **statische Website (Hauptoberfläche)**, erzeugt mit `python -m transparenz build-site`; nach jeder Daten- oder Darstellungsänderung neu erzeugen und mitcommitten |
| `src/transparenz/site/` | Website-Generator und Jinja2-Vorlagen |
| `app/main.py`, `app/views/` | Streamlit-App (lokal, z. B. manuelle Updates) |
| `data/sample/` | fiktive Beispieldaten (erzeugt mit `scripts/generate_sample_data.py`) |
| `docs/methodik/` | Methodik (wird in der App angezeigt) |

## Konventionen
- Typannotationen, Logging über `logging`, Pydantic-Validierung für alle importierten Daten.
- Engine bleibt rein funktional (keine DB, keine Uhr) – Eingaben werden übergeben.
- Texte immer quellenbasiert («Laut Gerichtsurteil … vom …»); nie eigene Urteile.
- Enum-Werte sind ASCII-Schlüssel; deutsche Anzeigetexte nur in `entities/labels.py`.

## Integrierte Quellen
Nur fiktive Demoquellen (siehe `sources.toml`). Echte Kandidaten mit Lizenzstatus:
`docs/DATA_SOURCES.md`. Nächste Quelle erst, wenn die vorherige zuverlässig läuft.

## Tests und Start
```powershell
.venv\Scripts\python -m pytest -q          # Tests
.venv\Scripts\python -m ruff check .       # Lint
.venv\Scripts\python -m transparenz update --force
.venv\Scripts\python -m streamlit run app\main.py
```
Erstinstallation: `powershell -ExecutionPolicy Bypass -File scripts\setup.ps1`.

## Update-System
`python -m transparenz update [--source KEY] [--force]` oder Button auf «Datenquellen &
Aktualität». Fehlerhafte Daten werden abgelehnt, der letzte gültige Stand bleibt aktiv; jeder
Versuch steht in `update_runs`. GitHub-Workflow `update-data.yml` nur manuell, kein dauerhafter
Speicher.

## Umgebung
Projektordner: `C:\Users\Bader\OneDrive\Desktop\Projekt Transparenz` (OneDrive). Jonas arbeitet
mit Windows PowerShell; Anleitungen immer mit `cd "…\Projekt Transparenz"` beginnen.
Veröffentlichen (GitHub-Push, Pages) nur nach ausdrücklicher Zustimmung.

## Grenzen
Nur fiktive Daten · nicht rechtlich geprüft · keine Anlageberatung · Schwellenwerte offen ·
keine Migrationen (Alembic) · keine echte Quelle angebunden.
