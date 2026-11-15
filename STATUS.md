# STATUS

Stand: **15.11.2026**. Diese Datei beschreibt nur den aktuellen Stand. Der Verlauf steht in
`docs/LOG.md`, die Begründungen in `docs/DECISIONS.md`, der Plan in `docs/ROADMAP.md`.

## Phase

**Phase 1 (SEC N-PORT importieren) umgesetzt.** Phase 0 abgeschlossen. Ziel laut Auftrag: alle
börsenkotierten Aktien und Fonds weltweit, automatisch zugeordnet, firmentauglich (D-049).
Nächste Phase: 2 (Wertpapierstamm ISIN → LEI aus Fondsmeldungen).

| Baustein | Stand |
|---|---|
| Git | `main` auf GitHub (Phase 0); Phase 1 lokal committet, nicht gepusht |
| Datenordner | `C:\TransparenzDaten` ausserhalb OneDrive (`TRANSPARENZ_DATA_DIR`, D-050) |
| Pilot-Code | in Paketmodule zerlegt (D-051); Fondskette in Phase 1 nicht verändert |
| Herkunft | jede Eingabedatei wird bei jedem Lauf gegen ihre Begleitdatei geprüft (D-052); gilt auch für N-PORT |
| **SEC N-PORT** | `2026q3_nport.zip` geladen und geprüft; `nport-update` liest direkt aus dem ZIP in `processed/nport.sqlite`, jeder Lauf in `update_runs` (D-054) |
| Kriterienmodell | Schema 2, Profil «streng» 1.1, 12 aktive Kriterien, 7 Beziehungstypen (D-045–D-048) |
| Zuordnung | ISIN → Wikidata → LEI und Registernummer wirken; GLEIF-Namenssuche gemessen, **nicht freigegeben** (D-046) |
| Website (`site/`) | fiktive Demo, unverändert |
| Tests | **361 bestanden** (16 neu für N-PORT), Ruff sauber |

## SEC N-PORT, Quartal 2026q3 (Messwerte, ohne Namen)

Quelle: Qualitätsbericht `C:\TransparenzDaten\processed\nport\quality_report.json`
(Datenstand 2, Regelversion 2026-11-15.2). Gemeldet von den Fonds («as filed»).

| Messgrösse | Wert |
|---|---|
| Gelesen / abgelehnt | 14'066 Meldungen, 5'627'083 Positionen, 6'996'305 Kennungszeilen; **0 Zeilen abgelehnt** |
| Meldungen | 13'938 Original, 128 Berichtigungen; eingereicht Juli–September 2026 |
| Welche Monate öffentlich | bei **100 %** der Meldungen liegt der Stichtag im Quartalsendmonat des Geschäftsjahrs (nur 3. Monat je Geschäftsquartal); Stichtage meist Mai–Juli 2026; Median 57 Tage bis zur Einreichung |
| Fonds | 13'908 (13'199 Serien, 709 Registranten ohne Serie); 13'902 mit gültigem Stand («current») |
| Nicht gewählt | 15 Meldungen unentschieden (gleicher Tag, gleicher Stichtag), davon 7 von 2 Registranten ohne Serie mit 902'141 Positionen (wohl Doppelmeldungen); 34 ersetzt, 115 älterer Stichtag |
| Positionen im gültigen Stand | 4'626'854 |
| mit gültiger ISIN | 90.18 % (fehlt 9.59 %, nur ungültige 0.22 %, mehrere verschiedene 0) |
| mit gültigem Emittenten-LEI | 72.79 % («N/A» 27.21 %, ungültig 57 Fälle) |
| beides gültig | 68.29 %; 399'511 verschiedene ISIN, 28'586 verschiedene Emittenten-LEI |
| nur Aktien (`EC`, 1'839'164) | ISIN 98.49 %, LEI 81.41 %, beides 80.68 % |
| Gewichtssumme je Meldung | Median 100.00 %; 81.64 % der Meldungen zwischen 95 und 105 % (Derivate, Leerverkäufe, Verbindlichkeiten) |
| LEI aktiv bei GLEIF | **nicht gemessen**: braucht die vollständige GLEIF-Liste (Download offen, unten) |
| Laufzeit / Speicher | Import rund 19–22 Minuten; Datenbank 4.8 GB (davon rund 2.4 GB ersetzter erster Stand) |

## Für die nächste Session

1. Wie in CLAUDE.md: STATUS, DECISIONS (ab D-049) und die letzten LOG-Einträge lesen.
2. Echte Ergebnisse: `C:\TransparenzDaten\notizen\PILOT_ERGEBNISSE.md` (lokal). Nie in
   versionierte Dateien übernehmen (D-053); vor jedem Push prüfen.
3. Plan: `docs/ROADMAP.md`. Nächster Schritt ist Phase 2; Downloads brauchen Jonas'
   Zustimmung, alles andere läuft ohne Einzelentscheide (D-049).
4. Jeder Umbau der Fondskette: vorher und nachher `scripts\pilot_regression.py` (D-051).
5. N-PORT-Regeln ändern = `RULE_VERSION` in `ingestion/sec_nport.py` erhöhen, dann
   `nport-update --force` (rund 20 Minuten).

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
# SEC N-PORT: lokale Archive einlesen, Qualitätsbericht; neues Quartal nur nach Zustimmung
.venv\Scripts\python -m transparenz nport-update --force
.venv\Scripts\python -m transparenz nport-download 2026q4            # nennt nur Name und Grösse
.venv\Scripts\python -m transparenz nport-download 2026q4 --confirm  # lädt wirklich
# Ein Fonds einzeln (Pfade relativ zum Projekt mit data\… funktionieren weiter)
.venv\Scripts\python scripts\pilot_fund_chain.py --zip data\raw\external\fi_se_fondinnehav\2026Q2\Fondinnehav_2026Q2.zip --fund "<exakter Fondsname>" --ets-dir data\raw\external\eu_ets_union_registry\2026-11-11 --gleif-rr data\raw\external\gleif_rr_golden_copy\2026-11-11\gleif-goldencopy-rr.csv.zip --gem-dir data\raw\external\gem\2026-11-11\extracted
```

Berichte mit Herkunftsabschnitt: `C:\TransparenzDaten\processed\pilot_regression\herkunft\*.html`
(Vorschau: Startkonfiguration `pilot-report`, 127.0.0.1:8611). Die Berichte unter
`processed\pilot_fund_chain\` stammen vom 14.11.2026 und erhalten den Abschnitt beim nächsten Lauf.

## Nächste drei Schritte

1. **GLEIF-Liste Level 1 laden** (`…-gleif-goldencopy-lei2-golden-copy.csv.zip`, 486.08 MB,
   3'494'789 Einträge, goldencopy.gleif.org, CC0) – braucht deine Zustimmung. Damit: «LEI
   existiert und ist aktiv» für die 28'586 gemeldeten Emittenten-LEI messen.
2. **Phase 2: Wertpapierstamm ISIN → LEI** aus N-PORT (bestätigt, wenn mindestens zwei
   unabhängige Fondsgesellschaften denselben LEI melden und keine widerspricht), dann
   Messung der GLEIF-Namenssuche gegen diese Referenz, je Region (D-046, D-049).
3. **Herkunft auf das Update-System ausweiten** (Schweiz, SEC-Katalog), damit jede Quelle
   denselben Prüfweg hat wie N-PORT.

## Offene Fragen (nur Grundsätzliches)

1. Zustimmung zum Download der GLEIF-Liste Level 1 (486.08 MB, oben).
2. Ersetzten ersten N-PORT-Stand (rund 2.4 GB, falsche Fondsregel, aus dem Archiv
   reproduzierbar) aus `nport.sqlite` löschen?
3. Ordner `analytics-dashboard-update/` (nicht Teil dieses Projekts): verschieben oder löschen?
4. Später, vor jeder Veröffentlichung: schriftliche Lizenzbestätigungen (SEC, FI,
   EU-Kommission) und einmalige Rechtsprüfung (Kosten).

Die Bewertungsregeln (Schwellen, Notstrom, Korruptionsdauer usw.) setzen wir mit begründetem
Standard selbst und kennzeichnen sie als unsere Bewertungsentscheidung (D-049).

## Grenzen

- Website zeigt nur fiktive Demodaten. Echte Daten bleiben lokal.
- N-PORT: nur US-registrierte Fonds, nur der dritte Monat je Geschäftsquartal. Ob eine
  Berichtigung immer die ganze Meldung ersetzt, ist nicht verifiziert (unsere Regel, D-054).
  Doppelmeldungen am selben Tag bleiben unentschieden.
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
| SEC N-PORT 2026q3 | 14'066 Meldungen, 5'627'083 Positionen (Archiv 441 MB, Datenbank 4.8 GB) |
| SwissPRTR | 247 Standorte; 22'860 Emissionszeilen |
| Speicher | `C:\TransparenzDaten` rund 3.9 GB; Festplatte 34 GB frei |
| Tägliches Update | Windows-Task `ProjektTransparenz-DailyDataUpdate` (findet den Datenordner über `.env`) |

Details: `docs/DATA_SOURCES.md`, `docs/GLOBAL_MARKET_CATALOG.md`, `docs/ROADMAP.md`.
