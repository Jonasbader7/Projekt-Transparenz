# CLAUDE.md – Projektgedächtnis «Projekt Transparenz»

## Mission
Fondspositionen mit nachvollziehbaren Quellen verbinden, damit Anleger:innen selbst beurteilen
können, ob ein nachhaltiger Fonds zu ihren Werten passt. Transparenz statt Greenwashing:
kein Gesamtscore, keine Aussage ohne Beleg, keine Empfehlungen, keine Renditeversprechen.
Belege (aus Quellen) und Bewertung (unser Profil, ausdrücklich als eigene Entscheidung
bezeichnet) bleiben immer getrennt. Ziel: ein weitgehend automatisches Werkzeug, das nur bei
unsicheren Fällen einen Menschen Ja oder Nein fragen muss und den Entscheid danach behält.
Gründer: Jonas Bader (BFH Digital Business & AI, ex Bankberater). Nebenprojekt.

## Arbeitsregeln
- **Zu Beginn jeder Session:** `STATUS.md`, `docs/DECISIONS.md` und die letzten Einträge in
  `docs/LOG.md` lesen.
- **Am Ende jeder Session:** `STATUS.md` aktualisieren (Phase, Fortschritt, nächste 3 Schritte,
  offene Fragen), `docs/LOG.md` ergänzen (neueste oben), neue Entscheide in `docs/DECISIONS.md`,
  dann ein Git-Commit mit aussagekräftiger Nachricht.
- **KI-Transparenz:** Im Sessionlog Assistent, tatsächlich verwendete Skills (Name/Quelle),
  wesentliche Tools und Prüfergebnisse erfassen; Übersicht `docs/AI_USAGE.md` aktuell halten.
  Verfügbare Skills nicht als verwendet ausgeben; unbekannte Angaben als «nicht erfasst» markieren.
- Deutsch, Schweizer Rechtschreibung (ss statt ß). Code-Bezeichner Englisch.
- Tests ausführen, bevor etwas als fertig gilt. Nicht ausgeführte oder fehlgeschlagene Tests
  ehrlich dokumentieren.
- **Priorität: Datenqualität und Nachvollziehbarkeit vor Funktionsumfang.** Keine neuen Features,
  solange die Grundlagen nicht zuverlässig laufen. Keine Platzhalterfunktionen, die fertig wirken.
- Vorher fragen: Kosten, Dateien ausserhalb des Projekts, Löschen, externe Dienste, Veröffentlichen
  (inkl. GitHub-Push).
- **Echte Ergebnisse bleiben lokal (D-053):** Fonds- oder Firmennamen zusammen mit Befunden
  (Konflikte, Emissionen, Beteiligungen, Zuordnungsfehler einzelner Firmen) nie in versionierte
  Dateien. Sie gehören nach `C:\TransparenzDaten\notizen\PILOT_ERGEBNISSE.md`. In STATUS, LOG,
  DECISIONS und DATA_SOURCES nur Methode und Messwerte ohne Namen. Vor jedem Push prüfen.
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
| `src/transparenz/config/sources.toml` | Datenquellen, Intervalle, **Lizenzregister je Quelle** |
| `src/transparenz/config/licensing.py` | Lizenzsperre: echte Quellen ohne geprüfte Lizenz werden nicht abgerufen |
| `src/transparenz/ingestion/gleif.py` | GLEIF-Adapter (erste echte Quelle, deaktiviert bis zum ersten echten Fonds) |
| `src/transparenz/config/criteria.toml` | **Kriterienmodell (Schema 2), einzige Stelle für Kriterien, Profilregeln, Kennzahlen**; Änderung = `profile_version` erhöhen + Eintrag in DECISIONS (D-043) |
| `src/transparenz/config/catalog.py` | lädt und prüft Quellen und Kriterienmodell (`load_criteria_model`) |
| `src/transparenz/screening/engine.py` | Belegstatus-Logik; wendet die Profilregel an («Konflikt mit Profil») |
| `src/transparenz/services/review_decisions.py`, `scripts/review_mapping.py` | Entscheid-Speicher für Korrekturen und Referenzfälle (D-042), freiwillige Ja/Nein-Abfrage |
| `src/transparenz/services/entity_matching.py` | Automatische Zuordnung: Registernummer, GLEIF-Namenssuche mit Sitzland, Präzisionsmessung und Freigabe (D-046) |
| `src/transparenz/services/ownership.py` | Beziehungstypen in Besitzketten: eigene Rechnung, Finanzbeteiligung, Vermögensverwaltung, Verwahrung (D-045) |
| `src/transparenz/services/update_manager.py` | DataUpdateManager |
| `src/transparenz/services/global_candidates.py` | Lokale Suche über den globalen Wikidata-Firmen-/Ticker-Rohbestand (`global-candidates-build`/`-search`); getrennt von `swiss_foundation.py` und `market_catalog.py` |
| `scripts/pilot_fund_chain.py` | Befehlszeile des Pilots «Position → Unternehmen → Beleg» an echten Fonds (FI Schweden + Wikidata + GLEIF + SwissPRTR + EU-Emissionshandel + GEM-Besitzketten, D-037–D-040); nicht im Screening, nicht auf der Website. Logik seit 15.11.2026 im Paket: `ingestion/fi_holdings.py`, `wikidata_isin.py`, `gleif_lookup.py`, `eu_ets.py`, `gem.py`; `services/fund_chain.py`, `fund_findings.py`, `mapping_reference.py`, `provenance.py`; `reports/fund_chain_report.py` mit `reports/templates/fund_chain_report.html.j2` |
| `src/transparenz/ingestion/sec_nport.py`, `services/nport_catalog.py` | SEC N-PORT (D-054): `nport-download <Quartal> [--confirm]`, `nport-update`; liest lokale Quartalsarchive direkt aus dem ZIP in `processed/nport.sqlite`, Qualitätsbericht `processed/nport/quality_report.json`; LEI-Abgleich mit der GLEIF-Liste Level 1 über `ingestion/gleif_level1.py` (D-055); daraus auch fehlende Rechtsnamen im Pilot (`cached_lei_names`, D-060) |
| `src/transparenz/services/security_master.py`, `services/reference_check.py` | Wertpapierstamm ISIN → LEI aus N-PORT (D-056): `security-master-build`/`-lookup`/`-compare`; bestätigt = zwei unabhängige Gesellschaften (CIK und N-CEN-Berater, `ingestion/sec_ncen_advisers.py`), kein Widerspruch, LEI bei GLEIF; Ausgabe `processed/security_master.sqlite`. Gegenprüfung der Pilotverfahren (D-057); im Pilot mit `--security-master` Referenz der Namenssuche, Freigabe je Region, Name nie gegen den Konsens (D-058) |
| `scripts/pilot_regression.py` | Vergleichslauf: sechs Pilotfonds offline von eingefrorenem Eingang rechnen und zwei Läufe vergleichen; Pflicht vor und nach jedem Umbau der Kette |
| `TRANSPARENZ_DATA_DIR` (`.env`) | Datenordner ausserhalb OneDrive (lokal `C:\TransparenzDaten`): `raw`, `processed`, `cache`, `review`. Nur über `settings.local_data_dir()`/`resolve_data_path()` ansprechen |
| `site/` | **statische Website (Hauptoberfläche)**, erzeugt mit `python -m transparenz build-site`; nach jeder Daten- oder Darstellungsänderung neu erzeugen und mitcommitten |
| `src/transparenz/site/` | Website-Generator und Jinja2-Vorlagen |
| `app/main.py`, `app/views/` | Streamlit-App (lokal, z. B. manuelle Updates) |
| `data/sample/` | fiktive Beispieldaten (erzeugt mit `scripts/generate_sample_data.py`) |
| `docs/methodik/` | Methodik (wird in der App angezeigt) |

## Konventionen
- Typannotationen, Logging über `logging`, Pydantic-Validierung für alle importierten Daten.
- Engine bleibt rein funktional (keine DB, keine Uhr) – Eingaben werden übergeben.
- Belegtexte immer quellenbasiert («Laut Gerichtsurteil … vom …»). Die Bewertung
  «Konflikt mit Profil» stammt nur aus `criteria.toml` und wird immer als unsere
  Bewertungsentscheidung bezeichnet; nie eine Bewertung im Code verstecken.
- Enum-Werte sind ASCII-Schlüssel; deutsche Anzeigetexte nur in `entities/labels.py`.

## Integrierte Quellen und Datenstand
Aktueller Stand, Zahlen und offene Entscheide stehen in `STATUS.md` (kurz halten: nur Stand,
kein Verlauf). Auftrag: **alle weltweit börsenkotierten Aktien und ETFs**; bisher Teilbestände.

- **Schweiz** (`swiss-update`, `config/swiss_sources.toml`, `data/processed/swiss.sqlite`):
  GLEIF CH, Zefix/LINDAS, SwissPRTR, Wikidata CH. Alle vier funktionsfähig (Wikidata seit D-034).
- **SEC-Marktkatalog** (`market-update`/`market-search`, `markets.sqlite`,
  `docs/GLOBAL_MARKET_CATALOG.md`, D-033): US-Fokus, keine Weltabdeckung. CIK ≠ Serie ≠
  Anteilsklasse ≠ Listing. Kontakt nur lokal `TRANSPARENZ_SEC_CONTACT` in `.env`; nie committen.
- **Wikidata weltweit** (`global-candidates-build`/`-search`, D-036): unbestätigte Hinweise.
- **SEC N-PORT** (`nport-update`, `config/nport_sources.toml`, `nport.sqlite`, D-054): Positionen
  aller US-registrierten Fonds mit gemeldetem Emittenten-LEI und ISIN; Grundlage für Phase 2.
- **Wertpapierstamm** (`security-master-build`, `security_master.sqlite`, D-056): ISIN → LEI aus
  dem Konsens unabhängiger Fondsgesellschaften; Widersprüche bleiben offen, nie per Name.
- **Pilot echter Fonds** (`scripts/pilot_fund_chain.py`, D-037–D-043): FI Schweden, Wikidata,
  GLEIF, SwissPRTR, EU-Emissionshandel, GEM. Nur lokal, nicht im Update-System.
- `docs/CODEX_TO_CLAUDE_HANDOFF.md` ist historisch (Stand 08.11.2026), nicht mehr massgebend.

**Lizenzmassstab (D-041):** Verwendet wird nur, was an der Originalseite eine benannte Lizenz
oder ausdrückliche Gemeinfreiheit trägt, die gewerbliche Nutzung, Speicherung, Ableitung und
Weitergabe erlaubt. «Öffentlich abrufbar» oder eine Auslegung genügt nicht. Unklare Quellen:
schriftlich nachfragen oder weglassen. Keine kostenpflichtigen APIs, kein Push, keine
öffentliche Datenfreigabe ohne Zustimmung. Der Auftrag vom 08.11.2026 erlaubt kostenlose
lokale Downloads freigegebener Quellen; Dateiname, Quelle und Grösse trotzdem vorher nennen.

**Zuordnung (D-042, D-046, D-058, D-059):** Automatisch, ohne Einzelfallfreigabe. Kennungen
(N-PORT-Konsens ISIN → LEI vor Wikidata ISIN → LEI, Registernummer) wirken immer. Ein Name ist nie ein Schlüssel: Die GLEIF-Namenssuche (gleicher
Name, Sitzland, aktiv, eindeutig) wirkt nur, solange ihre an Referenzfällen gemessene
Präzision die Freigabe erreicht (≥ 100 Fälle, untere 95-%-Grenze ≥ 97 %), **je Region** und an
der N-PORT-Referenz gemessen; nie gegen einen bestätigten N-PORT-LEI; sonst bleibt der
Fall offen. Präzision und Abdeckung immer getrennt ausweisen. Menschliche Entscheide
(`data/review/mapping_decisions.csv`) gehen vor und dienen als Referenzfälle. Kennungskonflikte
und ungültige Prüfziffern bleiben separat. Fondsrechtsträger ≠ ETF-Anteilsklassen ≠ Positionen.

**Beteiligungen (D-045):** Besitzketten erst nach Beziehungstyp einordnen. Nur Eigentum auf
eigene Rechnung ist eine Eigentumsbeteiligung; Vermögensverwaltung, Verwahrung, Finanzierung,
Betrieb und Lieferverträge haben eigene Regeln in `criteria.toml` (`relationship_type`).
Grosse Import-/Exportläufe nacheinander ausführen (Speicherbedarf).

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
GitHub: https://github.com/Jonasbader7/Projekt-Transparenz (öffentlich, `origin`, Branch `main`).
Python-Umgebung fehlt zu Beginn einer neuen Session ggf.: `scripts\setup.ps1` (bei langen
Temp-Pfaden kann pip an der Windows-Pfadgrenze scheitern → `-VenvPath` mit kurzem Pfad).
Git Bash: bei `git show <ref>:<pfad>` `MSYS_NO_PATHCONV=1` setzen.

## Grenzen
Demooberfläche fiktiv; echte Register-/SEC-Daten nur lokal. Kein vollständiger Aktien-/ETF-Bestand;
Fondspositionen nur im Pilot; keine Firmenvorwürfe importiert. Keine API. SwissPRTR-Standorte ohne sichere
Betreiber-UID bleiben unzugeordnet; die Emissions-XLSX ist normalisiert (D-032), Verknüpfung
nur über die eigene, prüfzifferngeprüfte Betriebs-UID, nicht über den Namen.
Quellenprüfung anhand offizieller Bedingungen, keine externe Rechtsberatung. Keine
Migrationen (Alembic); neue Spalten nur leer erlaubt und additiv (`add_missing_columns`, D-047).
Daten nicht ungeprüft publizieren.
