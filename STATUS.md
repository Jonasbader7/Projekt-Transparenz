# STATUS

Stand: **15.11.2026**. Diese Datei beschreibt nur den aktuellen Stand. Der Verlauf steht in
`docs/LOG.md`, die Begründungen in `docs/DECISIONS.md`, der Plan in `docs/ROADMAP.md`.

## Phase

**Phase 0 (Fundament) abgeschlossen.** Ziel laut Auftrag: alle börsenkotierten Aktien und
Fonds weltweit, automatisch zugeordnet, firmentauglich (D-049). Nächste Phase: SEC N-PORT.

| Baustein | Stand |
|---|---|
| Git | `main` auf GitHub (15.11.2026, ein zusammengefasster Commit ohne echte Ergebnisse, D-053) |
| Datenordner | `C:\TransparenzDaten` ausserhalb OneDrive (`TRANSPARENZ_DATA_DIR`, D-050); 14 alte Schweizer Exportstände gelöscht |
| Pilot-Code | in Paketmodule zerlegt (D-051); Vergleichslauf sechs Fonds vorher/nachher: 45 Dateien, 0 Abweichungen |
| Herkunft | jede Eingabedatei wird bei jedem Lauf gegen ihre Begleitdatei geprüft und mit SHA-256 im Bericht geführt (D-052) |
| Kriterienmodell | Schema 2, Profil «streng» 1.1, 12 aktive Kriterien, 7 Beziehungstypen (D-045–D-048) |
| Zuordnung | ISIN → Wikidata → LEI und Registernummer wirken; GLEIF-Namenssuche gemessen, **nicht freigegeben** (D-046) |
| Website (`site/`) | fiktive Demo, neu erzeugt (Methodik mit Kategorien, Beziehungstypen, Wirkungsdauer) und veröffentlicht; Beispielquelle zeigt ehrlich «veraltet» (fester Stichtag der Beispieldaten) |
| Tests | **345 bestanden**, Ruff sauber |

## Für die nächste Session

1. Wie in CLAUDE.md: STATUS, DECISIONS (ab D-049) und die letzten LOG-Einträge lesen.
2. Echte Ergebnisse: `C:\TransparenzDaten\notizen\PILOT_ERGEBNISSE.md` (lokal). Nie in
   versionierte Dateien übernehmen (D-053); vor jedem Push prüfen.
3. Plan: `docs/ROADMAP.md`. Nächster Schritt ist Phase 1 (N-PORT); der Download braucht Jonas'
   Zustimmung, alles andere läuft ohne Einzelentscheide (D-049).
4. Jeder Umbau der Fondskette: vorher und nachher `scripts\pilot_regression.py` (D-051).

## Pilot (sechs echte schwedische Fonds, je 30.06.2026)

Ergebnisse je Fonds mit Namen stehen nur lokal in
`C:\TransparenzDaten\notizen\PILOT_ERGEBNISSE.md` (Regel: echte Ergebnisse nie in
versionierte Dateien). Öffentlich nur die Methode und die Messwerte der Zuordnung:

- Abdeckung (Fondsgewicht mit widerspruchsfreier Zuordnung) je Fonds zwischen 44 und 81 %;
  ausserhalb globaler Grosswerte kennt Wikidata oft keinen LEI.
- Präzision der Namenssuche (unabhängig): 196 von 201 richtig, untere 95-%-Grenze 94.8 %
  (Schwelle 97 %) → nicht freigegeben. Die Wikidata-Referenz ist in mehreren Fällen selbst
  falsch. Lösung ohne Handarbeit: Referenz aus N-PORT (Phase 2).
- Registernummer (Wikidata ↔ GLEIF): 102 von 103 richtig, wirkt als Kennung.

## Befehle

```powershell
cd "C:\Users\Bader\OneDrive\Desktop\Projekt Transparenz"
.venv\Scripts\python -m pytest -q
# Vergleichslauf: sechs Pilotfonds offline rechnen und mit einem früheren Lauf vergleichen
.venv\Scripts\python scripts\pilot_regression.py run neu
.venv\Scripts\python scripts\pilot_regression.py compare herkunft neu
# Ein Fonds einzeln (Pfade relativ zum Projekt mit data\… funktionieren weiter)
.venv\Scripts\python scripts\pilot_fund_chain.py --zip data\raw\external\fi_se_fondinnehav\2026Q2\Fondinnehav_2026Q2.zip --fund "<exakter Fondsname>" --ets-dir data\raw\external\eu_ets_union_registry\2026-11-11 --gleif-rr data\raw\external\gleif_rr_golden_copy\2026-11-11\gleif-goldencopy-rr.csv.zip --gem-dir data\raw\external\gem\2026-11-11\extracted
```

Berichte mit Herkunftsabschnitt: `C:\TransparenzDaten\processed\pilot_regression\herkunft\*.html`
(Vorschau: Startkonfiguration `pilot-report`, 127.0.0.1:8611). Die Berichte unter
`processed\pilot_fund_chain\` stammen vom 14.11.2026 und erhalten den Abschnitt beim nächsten Lauf.

## Nächste drei Schritte

1. **SEC N-PORT laden** (`2026q3_nport.zip`, 440.95 MB, sec.gov) – braucht deine Zustimmung.
   Danach Adapter mit Prüfung, direkt aus dem ZIP gelesen, mit Herkunftsprüfung.
2. **Wertpapierstamm ISIN → LEI** aus den Fondsmeldungen (Konsens mehrerer Meldender) und
   Messung der Namenssuche gegen diese Referenz, je Region (Phase 2).
3. **Herkunft auf das Update-System ausweiten** (Schweiz, SEC-Katalog), damit jede Quelle
   denselben Prüfweg hat.

## Offene Fragen (nur Grundsätzliches)

1. Zustimmung zum N-PORT-Download (oben).
2. Ordner `analytics-dashboard-update/` (nicht Teil dieses Projekts): verschieben oder löschen?
3. Später, vor jeder Veröffentlichung: schriftliche Lizenzbestätigungen (SEC, FI,
   EU-Kommission) und einmalige Rechtsprüfung (Kosten).

Die Bewertungsregeln (Schwellen, Notstrom, Korruptionsdauer usw.) setzen wir mit begründetem
Standard selbst und kennzeichnen sie als unsere Bewertungsentscheidung (D-049).

## Grenzen

- Website zeigt nur fiktive Demodaten. Echte Daten bleiben lokal.
- Pilot ist nicht Teil des Update-Systems; FI, EU-ETS und GEM ohne Lizenzsperre. FI und
  EU-ETS tragen keine benannte Lizenz (Bericht: «keine benannte Lizenz»).
- Abfrage-Zwischenspeicher (Wikidata, GLEIF) haben keine Begleitdatei; ihr Stand und ihre
  Prüfsumme stehen im Bericht, ihre Herkunft ist die jeweilige Abfrage.
- Beziehungstypen teils an Firmennamen erkannt; GEM nennt Besitzstand zum Ausgabedatum, nicht
  zum Fondsstichtag. Finanzierung, Betrieb, Lieferverträge: keine Quelle mit Kennung.
- Lizenzprüfung = Lektüre der Originalseiten, keine Rechtsberatung.

## Lokaler Datenbestand

| Bestand | Anzahl |
|---|---|
| Schweizer Rechtseinheiten (GLEIF CH, Zefix) | 801'732 |
| Wikidata weltweit | 15'624 Firmen-/Ticker-Kandidaten |
| SEC-Marktkatalog | 44'085 Einträge (USA) |
| SwissPRTR | 247 Standorte; 22'860 Emissionszeilen |
| Speicher | `C:\TransparenzDaten` rund 3.9 GB; Festplatte 34 GB frei |
| Tägliches Update | Windows-Task `ProjektTransparenz-DailyDataUpdate` (findet den Datenordner über `.env`) |

Details: `docs/DATA_SOURCES.md`, `docs/GLOBAL_MARKET_CATALOG.md`, `docs/ROADMAP.md`.
