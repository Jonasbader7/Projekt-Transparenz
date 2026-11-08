# Sessionlog

Neueste Einträge oben.

## 08.11.2026 – Codex: Schweizer Rohdatenfundament

- Bestehende Architektur/Doku geprüft; Starterkit unter einschlägigen Namen im Projekt und
  Downloads nicht gefunden. Keine Framework- oder Designänderung, keine Veröffentlichung.
- Offizielle Rechte geprüft: GLEIF/Wikidata CC0, Zefix-Ressource terms_open,
  SwissPRTR terms_by. Sperre um Speicher-/Ableitungsrechte erweitert; blockierte Kandidaten
  maschinenlesbar erfasst. Wikidata ist technisch HTTP 403, keine Umgehung.
- Originale tatsächlich archiviert: GLEIF CH 28'495 Treffer, Zefix 796'690 Originaleinheiten,
  SwissPRTR-Standorte und Original-Emissions-XLSX 2007–2024. Rohdaten/DB/Exporte ignoriert.
- Aktiv: 25'121 GLEIF-Rechtsträger + 796'684 Zefix-Einheiten, nach eindeutiger Kennungsfusion
  801'647 Rechtseinheiten; separat 3'254 Fondsrechtsträger und 247 Standorte. Keine bestätigten
  Wertpapiere, ETF-Anteilsklassen oder Positionen. 8 Originaleinträge in Quarantäne.
- Adapter, Cache, Cursor-/Keyset-Paginierung, Hash-/STAC-Prüfung, Quarantäne, OS-Lock,
  transaktionales Batchschreiben und atomare lokale Exportgenerationen implementiert.
- Reale Fehler behandelt: GLEIF-10'000er-Seitengrenze, ungültige LEIs/UIDs, mehrsprachige
  Zefix-Namen, doppelte UID-Registeridentitäten, SQLite-Dateisperre unter Windows.
  Gleichzeitige grosse Exporte abgebrochen; danach einzeln exportiert und OS-Lock ergänzt.
- Bestehende 151 Tests vorab bestanden; erweiterte Tests und Ruff grün (Schlusszahl im Handoff).
  Offline-Bestandsaudit bestanden: 801'647 eindeutige Schlüssel und 156 Originaldateien
  hashgeprüft; 0 laufende Updateversuche. Frühere Fehlversuche bleiben protokolliert.
  Übergabe `docs/CODEX_TO_CLAUDE_HANDOFF.md`, Betrieb über `python -m transparenz swiss-update`.

## 08.11.2026 – Session 2, Teil 2: Erste echte Datenquelle (parallele Session)

**Erledigt**
- Lizenzen an den Originalseiten geprüft und in `docs/DATA_SOURCES.md` festgehalten: GLEIF
  (CC0 1.0), GLEIF/ANNA ISIN-LEI (keine Lizenz genannt → ausgeschlossen), SEC N-PORT (öffentliche
  Information, Weiterverbreitung ohne Erlaubnis, Quellenangabe erbeten), OFAC SDN (US-Government-
  Werk; Treasury-Metadaten auf data.gov: CC0 1.0; OFAC-Seiten selbst ohne Lizenzangabe), DOL ILAB
  (Public Domain, nur Waren × Länder), Weltbank (CC BY 4.0 mit Attributionsformat), WBA
  (CC BY 4.0 vs. restriktive Tool-Bedingungen → ausgeschlossen; NC-ND-Angabe nicht gefunden)
- Fachfragen mit Jonas: US-Fonds und OFAC-Einordnung **später** (D-027); Lizenzsperre ja (D-025);
  GLEIF-Live-Test mit 2–3 Anfragen ja
- Lizenzregister + automatische Sperre (`config/licensing.py`, Status «gesperrt») (D-025)
- GLEIF-Adapter (`ingestion/gleif.py`): Abfrageliste, API-Abruf mit Pause (< 60/Min.),
  Pydantic-Validierung, Übersetzung in Stammdaten inkl. Mutterbeziehungen (D-026);
  fiktive Testdateien im GLEIF-Format (`tests/fixtures/gleif/`)
- Zuordnungsquote (`services/mapping_quality.py`, `python -m transparenz mapping --fund …`).
  Fiktiver ETF: 17 Aktien/Anleihen, 16 zugeordnet, 15 mit LEI, 0 bei GLEIF (fiktive LEIs)
- Live-Prüfung GLEIF (3 Anfragen insgesamt, je < 4 KB): Struktur der Antwort, Reporting-Exception,
  Endtest des Adapters mit dem LEI von GLEIF in temporärer Datenbank → 1 Datensatz, keine Warnungen
- Website: deaktivierte Quellen erscheinen als «deaktiviert» statt «veraltet»; `build-site`
- 151 Tests grün, ruff sauber

**Problem:** Der Fehler «annullierter LEI doppelt gemeldet» fiel erst im Update-Test auf und
ist behoben. Das N-PORT-Readme (PDF) liess sich nur behelfsmässig auslesen; die Regel, welche
Monatsmeldungen öffentlich sind, bleibt unbestätigt.

**Nicht gemacht:** kein N-PORT- oder OFAC-Download, kein Push.

## 07.11.2026 – Session 2: Umgebung, Besuchszählung, Website online

**Erledigt**
- **Website online:** https://jonasbader7.github.io/Projekt-Transparenz/ (Pages war bereits
  eingeschaltet; Workflow auf `f33bc46` neu gestartet). Online geprüft: Seite und beide
  Tracker-Skripte laden, Worker nimmt den Seitenaufruf mit 204 an, keine Konsolenfehler
- Worker bereitgestellt (Version `da476383`). Erster Versuch mit `npx wrangler deploy` scheiterte,
  weil `wrangler.jsonc` im Repo nur den Platzhalter für die D1-ID enthält → neues Skript
  `Portfoliopage/analytics/backend/deploy-windows.ps1`. Probe ohne Speicherung: `transparenz`
  angenommen, fremde Seite abgelehnt
- Portfoliopage gepusht (`b5b1418`), Projekt Transparenz gepusht (`f33bc46`), Tests auf GitHub grün
- Python-Umgebung neu eingerichtet (`scripts/setup.ps1`, `.venv` im Projektordner); 109 Tests grün
- BORS/Portfolio-Tracker auf die Website erweitert (D-024): lokale Skripte in
  `src/transparenz/site/static/`, Einbindung in `base.html`, Datenschutz-Link; Client zählt nur auf
  `jonasbader7.github.io`. In `Portfoliopage`: Worker akzeptiert `transparenz`,
  Datenschutzseite und Analytics-README ergänzt
- Tests angepasst: statt «keine Skripte» nur die zwei lokalen Tracker-Skripte, kein Token,
  Schutz gegen lokales Zählen; 110 Tests grün, ruff sauber
- Geprüft: lokal im Browser (Skripte geladen, keine Anfrage an den Worker, keine Konsolenfehler);
  Client und Worker in Node simuliert
- `docs/recht/datenschutz.md` aktualisiert (IP-Protokoll = Personendaten, offen)
- Datenquellen-Recherche (SEC N-PORT, GLEIF, OFAC) in eigene Session ausgelagert

**Hinweis:** Die Online-Prüfung hat einen echten Seitenaufruf gezählt (inkl. IP-Protokoll).

**Offen:** Repo anpinnen; rechtliche Prüfung des IP-Protokolls (D-024).

## 07.11.2026 – Session 1, Teil 3: GitHub

**Erledigt**
- Repo https://github.com/Jonasbader7/Projekt-Transparenz verbunden; GitHub-Initialcommit
  (nur `.gitattributes`) zusammengeführt, ohne Überschreiben
- Nach Zustimmung von Jonas gepusht; Repo ist öffentlich (D-023); Workflow «Tests» lief grün
- STATUS.md für die nächste Session aufbereitet (Übersicht, Hinweise zur Umgebung)

**Offen:** GitHub Pages einschalten und Website-Workflow starten (nur Jonas kann die
Repo-Einstellung ändern).

## 07.11.2026 – Session 1, Teil 2: Umzug und statische Website

**Erledigt**
- Projekt nach `OneDrive\Desktop\Projekt Transparenz` verschoben, Git-Verlauf übernommen (D-022)
- Statische Website (`transparenz.site`, `build-site`): Übersicht, Fondsanalyse, Methodik,
  Datenquellen; Bericht/CSV als Download; heller/dunkler Modus; Handybreite geprüft (D-021)
- Vorbereiteter, nur manuell auslösbarer GitHub-Pages-Workflow (`pages.yml`)
- Fehler gefunden und behoben: gleichlautende Aufzählungswerte überschrieben sich in der
  Bezeichnungstabelle («Verfahren nicht_anwendbar» statt «–»); Test über alle Aufzählungen ergänzt
- Fehler gefunden und behoben: Methodik-Querverweis auf `validierung.md` war auf der Website tot
- 109 Tests bestehen, ruff sauber

**Problem:** Jonas konnte die Skripte nicht starten, weil PowerShell in `C:\Windows\System32`
stand. README erklärt jetzt den Ordnerwechsel; die Website braucht gar keinen Start mehr.

## 07.11.2026 – Session 1: Projektaufbau und erster Meilenstein (fiktive Daten)

**Plan der Session:** Umgebung prüfen → Struktur/Konfiguration → Datenmodell → Import und
Validierung → Screening-Engine → Streamlit-App → Update-System → Tests → Doku und Commit.

**Erledigt**
- Projektstruktur, Konfiguration (`settings.py`, `sources.toml`, `criteria.toml`), Git-Repo
- Belegmodell (Pydantic), Datenbankschema mit Versionierung, Parser mit Validierung und Duplikaterkennung
- Screening-Engine; nach externem Feedback (gleicher Tag) von Zwei-Quellen-Regel auf
  **Beweisstatus** umgestellt; «festgestellt» nur nach Dokumentprüfung
- Positionsliste auf CSV umgestellt (vorher JSON)
- Unternehmenszuordnung mit Vertrauen, Schutz vor LEI-Konflikten
- DataUpdateManager (Intervalle, Hash/ETag, Wiederholungen, Transaktion, Protokoll, Aktualität)
- Streamlit-App mit vier Seiten; Bericht als Markdown/CSV mit Datenstand je Feststellung
- 84 Tests (inkl. End-to-End CSV → Streamlit), ruff sauber
- Windows-Setup (`scripts/setup.ps1`) in Windows PowerShell 5.1 ausgeführt, App im Browser geprüft
- Dokumentation: Methodik, Architektur, Datenmodell, Datenquellen, Strategie, Recht, Leitfaden

**Probleme und Lösungen**
- Der Session-Ordner hat einen sehr langen Pfad; `pip` scheitert dort an der Windows-Grenze von
  260 Zeichen. Virtuelle Umgebung deshalb ausserhalb angelegt. In einem normalen Projektordner
  (z. B. auf dem Desktop) tritt das nicht auf.
- Windows-Konsole (cp1252) konnte Sonderzeichen nicht ausgeben → CLI schreibt UTF-8.
- Anzeigetexte kollidierten bei gleichlautenden Enum-Werten («unbekannt») → Schlüssel (Typ, Wert).

**Entscheid am Ende der Session:** Erste Zielgruppe sind Privatanleger:innen (D-020).

**Nicht erledigt / offen:** siehe STATUS.md.
