# STATUS

Stand: **16.11.2026**. Diese Datei beschreibt nur den aktuellen Stand. Der Verlauf steht in
`docs/LOG.md`, die Begründungen in `docs/DECISIONS.md`, der Plan in `docs/ROADMAP.md`.

## Phase

**Phase 2 (Wertpapierstamm ISIN → LEI) im Pilot umgesetzt:** Stamm gebaut (D-056),
Pilotverfahren gemessen (D-057), Freigabe der Namenssuche je Region an der N-PORT-Referenz
(D-058), N-PORT-Konsens als Kennungsweg vor Wikidata (D-059). Phasen 0 und 1 abgeschlossen.
Ziel laut Auftrag: alle börsenkotierten Aktien und Fonds weltweit, automatisch zugeordnet,
firmentauglich (D-049). Offen in Phase 2: GLEIF-Namen der N-PORT-LEI offline aus der lokalen
Liste Level 1.

| Baustein | Stand |
|---|---|
| Git | `main` auf GitHub bis Phase 0; Phase 1 und 2 in lokalen Commits, **nicht gepusht** |
| Datenordner | `C:\TransparenzDaten` ausserhalb OneDrive (`TRANSPARENZ_DATA_DIR`, D-050) |
| Pilot-Code | in Paketmodule zerlegt (D-051); Fondskette in Phase 1 und 2 nicht verändert |
| Herkunft | jede Eingabedatei wird bei jedem Lauf gegen ihre Begleitdatei geprüft (D-052); gilt auch für N-PORT |
| SEC N-PORT | `2026q3_nport.zip` geladen und geprüft; `nport-update` liest direkt aus dem ZIP in `processed/nport.sqlite`, jeder Lauf in `update_runs` (D-054) |
| **Wertpapierstamm** | `security-master-build` → `processed/security_master.sqlite` (87 MB, rund 2.5 Minuten), Regelversion 2026-11-16.1 (D-056) |
| Kriterienmodell | Schema 2, Profil «streng» 1.1, 12 aktive Kriterien, 7 Beziehungstypen (D-045–D-048) |
| Zuordnung | im Pilot mit `--security-master`: menschlicher Entscheid → **N-PORT-Konsens (D-059)** → Wikidata → Registernummer → GLEIF-Namenssuche (freigegeben in Europa und Asien-Pazifik, D-058, nie gegen den Konsens); ohne Stamm wie bisher |
| Website (`site/`) | fiktive Demo, unverändert |
| Tests | **386 bestanden** (4 neu für den Kennungsweg N-PORT), Ruff sauber |

## Wertpapierstamm ISIN → LEI (Phase 2, Messwerte ohne Namen)

Quelle: `C:\TransparenzDaten\processed\security_master\quality_report.json` (N-PORT-Stand 2,
GLEIF Level 1 vom 15.11., Level 2 vom 11.11., N-CEN 2025q4–2026q3). Regeln: D-056.

| Messgrösse | Wert |
|---|---|
| Umfang | 398'251 ISIN aus 4'161'239 Positionen (gültige ISIN, «current», ohne 11'455 Derivate) |
| Bestätigt | **116'216 ISIN** = 47.17 % der 246'398 ISIN mit gemeldetem LEI; **73.43 % der Positionen**; 19'530 verschiedene LEI |
| Nur eine Gesellschaft | 127'258 ISIN (5.71 % der Positionen) |
| Widerspruch | 2'707 ISIN (3.49 % der Positionen): übrige 2'059, Mutter/Tochter 210, inaktiv 186, Nachfolger 125, gleiche Gruppe 55, Fondsstruktur 37 |
| LEI unbrauchbar | nicht bei GLEIF 159, annulliert 58 |
| Kein LEI gemeldet | 151'853 ISIN (17.31 % der Positionen) |
| Unabhängigkeit | Median 3 Gruppen je bestätigter ISIN; genau 2: 32.53 %. Unter «jede CIK zählt» wären 15'045 ISIN mehr bestätigt. 89.49 % der Fonds mit Berater laut N-CEN |
| Normalisiert | 505 Meldungen GLEIF-Duplikat → Nachfolger, 474 Trust → Serie |
| Bestätigt je Anlageart | Anleihen 61.66 %, Aktien 72.54 %, Hypothekenpapiere 31.99 % (je ISIN mit LEI) |
| Gegenprüfung Pilot (D-057) | Namenssuche 675/679 richtig (untere Grenze 98.66 %; Europa 97.70 %, Asien-Pazifik 98.23 %, Nordamerika und übrige < 100 Fälle); Registernummer 115/116; Wikidata 626/642 (96.24 %) |
| Kennungsweg im Pilot (D-059) | 2'151 Positionen über den Konsens (546 vorher nicht bestätigt, 23 mit anderem LEI: 16 Papiere, jedes Mal N-PORT = börsenkotierte Gesellschaft); Wikidata gleich 901, anders 21, ohne LEI 348, kein Eintrag 847; bestätigte Abdeckung je Fonds **90–98 %**; Messung unverändert; offene Ja/Nein-Fragen 217 → 14 |
| Freigabe im Pilot (D-058) | Vergleichslauf: unabhängig 645/649, freigegeben Europa (270/272) und Asien-Pazifik (243/244). Sechs Fonds: 689 Positionen neu über den Namen (645 davon von N-PORT bestätigt), 10 gesperrt wegen Widerspruch; bestätigte Abdeckung je Fonds vorher 44–81 %, nachher 70–86 % des Gewichts |

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
| LEI bei GLEIF (Liste Level 1 vom 15.11.2026) | von 28'586 Emittenten-LEI: **99.97 % vorhanden** (10 fehlen), Rechtsträger **aktiv 98.66 %** (inaktiv 316, Duplikat/annulliert 57), Datensatz gepflegt (ISSUED) 72.41 %, überfällig (LAPSED) 26.24 %; gewichtet nach Positionen aktiv 99.58 %, aktiv und gepflegt 80.69 % |
| Serien-LEI der Fonds | 13'821 gemeldet, 100 % bei GLEIF, aktiv 99.35 %, gepflegt 95.43 % |
| Laufzeit / Speicher | Import rund 19–22 Minuten, GLEIF-Abgleich rund 4 Minuten (danach zwischengespeichert); Datenbank 4.8 GB (davon rund 2.4 GB ersetzter erster Stand) |

## Für die nächste Session

1. Wie in CLAUDE.md: STATUS, DECISIONS (ab D-049) und die letzten LOG-Einträge lesen.
2. Echte Ergebnisse: `C:\TransparenzDaten\notizen\PILOT_ERGEBNISSE.md` (lokal). Nie in
   versionierte Dateien übernehmen (D-053); vor jedem Push prüfen.
3. Plan: `docs/ROADMAP.md`. Phase 2: Stamm steht, Freigabe je Region und Kennungsweg
   N-PORT umgesetzt (D-056–D-059). Downloads brauchen Jonas' Zustimmung, alles andere läuft
   ohne Einzelentscheide (D-049).
4. Jeder Umbau der Fondskette: vorher und nachher `scripts\pilot_regression.py` (D-051).
5. N-PORT-Regeln ändern = `RULE_VERSION` in `ingestion/sec_nport.py` erhöhen, dann
   `nport-update --force` (rund 20 Minuten, im Hintergrund laufen lassen).
6. Einstieg Phase 2: Daten in `C:\TransparenzDaten\processed\nport.sqlite`, aktiver
   Datenstand 2 (`dataset_versions.status = 'active'`). Tabellen `nport_submissions`
   (`fund_key`, `selection = 'current'`, `registrant_lei`, `cik`), `nport_holdings`
   (`isin`, `issuer_lei`, `issuer_lei_status`, `asset_cat`), `nport_identifiers`.
   Meldende Gesellschaft = Registrant (CIK); «unabhängig» heisst seit D-056 verschiedene
   Beratergruppen (CIK und N-CEN-Berater mit GLEIF-Konzern), nicht bloss verschiedene CIK.
   GLEIF-Status je LEI: `ingestion/gleif_level1.py`
   (`load_lei_records`), Liste unter `raw/external/gleif_lei2_golden_copy/2026-11-15/`.
   Abfragen auf die Datenbank nur lesend (`?mode=ro`), sie ist 4.8 GB gross.
7. Wertpapierstamm: `services/security_master.py` (Regel je ISIN `classify`, rein
   funktional), `processed/security_master.sqlite` (Tabellen `securities`, `claims`,
   `build_info`). Regeländerung = `RULE_VERSION` erhöhen, neu bauen. Gegenprüfung:
   `services/reference_check.py`, Ergebnis `processed/security_master/pilot_comparison.json`
   (lokal, enthält ISIN und LEI der Abweichungen).
8. Pilot mit N-PORT-Referenz: `pilot_fund_chain.py … --security-master
   C:\TransparenzDaten\processed\security_master.sqlite`; Vergleichslauf
   `pilot_regression.py run <name> --security-master --passes 2`. Letzte Läufe:
   `p3_vorher` (Commit 2d7deea, gleich `p2_nport`) und `p3_nachher` (Kennungsweg N-PORT,
   aktueller Stand). Auswertung der Einzelfälle:
   `C:\TransparenzDaten\notizen\d059_vergleich_einzelfaelle.md` (lokal, mit Namen).
   Code nie ändern, während ein Vergleichslauf läuft (jeder Fonds lädt den Code neu).

## Pilot (sechs echte schwedische Fonds, je 30.06.2026)

Ergebnisse je Fonds mit Namen stehen nur lokal in
`C:\TransparenzDaten\notizen\PILOT_ERGEBNISSE.md` (Regel: echte Ergebnisse nie in
versionierte Dateien). Öffentlich nur die Methode und die Messwerte der Zuordnung:

- Abdeckung (Fondsgewicht mit widerspruchsfreier Zuordnung) je Fonds: ohne Wertpapierstamm
  44–81 %, mit Wertpapierstamm 90–98 % (Kennungsweg N-PORT, D-059; vorher nur Referenz der
  Namenssuche, D-058: 70–86 %).
- Namenssuche an der N-PORT-Referenz (unabhängig): 645 von 649 richtig, freigegeben in Europa
  und Asien-Pazifik; Nordamerika und übrige noch zu wenige Fälle. Ohne Wertpapierstamm (alte
  Wikidata-Referenz): 196 von 201, nicht freigegeben.
- Registernummer (Wikidata ↔ GLEIF): 115 von 116 richtig an N-PORT, wirkt als Kennung.

## Befehle

```powershell
cd "C:\Users\Bader\OneDrive\Desktop\Projekt Transparenz"
.venv\Scripts\python -m pytest -q
# Vergleichslauf: sechs Pilotfonds offline rechnen und mit einem früheren Lauf vergleichen
# (aktueller Stand: p3_nachher; rund 35 Minuten mit zwei Durchgängen, im Hintergrund)
.venv\Scripts\python scripts\pilot_regression.py run neu --security-master --passes 2
.venv\Scripts\python scripts\pilot_regression.py compare p3_nachher neu --json-only --ignore-key provenance
# SEC N-PORT: lokale Archive einlesen, Qualitätsbericht; neues Quartal nur nach Zustimmung
.venv\Scripts\python -m transparenz nport-update --force
.venv\Scripts\python -m transparenz nport-download 2026q4            # nennt nur Name und Grösse
.venv\Scripts\python -m transparenz nport-download 2026q4 --confirm  # lädt wirklich
# Wertpapierstamm ISIN → LEI (lokal, rund 2.5 Minuten), eine ISIN nachsehen, Pilot gegenprüfen
.venv\Scripts\python -m transparenz security-master-build
.venv\Scripts\python -m transparenz security-master-lookup <ISIN>
.venv\Scripts\python -m transparenz security-master-compare
# Ein Fonds einzeln (Pfade relativ zum Projekt mit data\… funktionieren weiter)
.venv\Scripts\python scripts\pilot_fund_chain.py --zip data\raw\external\fi_se_fondinnehav\2026Q2\Fondinnehav_2026Q2.zip --fund "<exakter Fondsname>" --ets-dir data\raw\external\eu_ets_union_registry\2026-11-11 --gleif-rr data\raw\external\gleif_rr_golden_copy\2026-11-11\gleif-goldencopy-rr.csv.zip --gem-dir data\raw\external\gem\2026-11-11\extracted
```

Aktuelle Berichte: `C:\TransparenzDaten\processed\pilot_regression\p3_nachher\*.html`
(mit Wertpapierstamm als Kennungsweg). Vergleich mit älteren Läufen (`herkunft`) zeigt zusätzlich eine neuere
Schweizer Exportgeneration (täglicher Task), deshalb Ausgangsstand immer frisch rechnen.
Ältere Berichte mit Herkunftsabschnitt: `C:\TransparenzDaten\processed\pilot_regression\herkunft\*.html`
(Vorschau: Startkonfiguration `pilot-report`, 127.0.0.1:8611). Die Berichte unter
`processed\pilot_fund_chain\` stammen vom 14.11.2026 und erhalten den Abschnitt beim nächsten Lauf.

## Nächste drei Schritte

1. **GLEIF-Namen offline aus der Liste Level 1:** Für 285 von 2'151 N-PORT-Positionen fehlt im
   gespeicherten Abruf der GLEIF-Name; dort prüft der Pilot die Kontoinhaber im
   EU-Emissionshandel nicht (4 Positionen mit Beleg). Namen aus der lokalen, geprüften Liste
   (`ingestion/gleif_level1.py`, Spalten `Entity.LegalName`, frühere Namen) einmal für alle
   bestätigten LEI des Stamms zwischenspeichern; mit Vergleichslauf.
2. **Herkunft auf das Update-System ausweiten** (Schweiz, SEC-Katalog), damit jede Quelle
   denselben Prüfweg hat wie N-PORT.
3. **Doppelmeldungen** (gleicher Tag, gleicher Stichtag, gleiches Nettovermögen) inhaltlich
   vergleichen: nur bei identischen Positionen eine übernehmen, sonst offen lassen.

## Offene Fragen (nur Grundsätzliches)

1. Ersetzten ersten N-PORT-Stand (rund 2.4 GB, falsche Fondsregel, aus dem Archiv
   reproduzierbar) aus `nport.sqlite` löschen?
2. Ordner `analytics-dashboard-update/` (nicht Teil dieses Projekts): verschieben oder löschen?
3. Später, vor jeder Veröffentlichung: schriftliche Lizenzbestätigungen (SEC, FI,
   EU-Kommission) und einmalige Rechtsprüfung (Kosten).

Die Bewertungsregeln (Schwellen, Notstrom, Korruptionsdauer usw.) setzen wir mit begründetem
Standard selbst und kennzeichnen sie als unsere Bewertungsentscheidung (D-049).

## Grenzen

- Freigabe der Namenssuche gilt je Region, gemessen an grossen, von US-Fonds gehaltenen
  Titeln. Seit D-059 wirkt sie nur noch dort, wo kein N-PORT-Konsens besteht (44 Positionen),
  also gerade ausserhalb der Referenz. Nordamerika und übrige: zu wenige Fälle.
- N-PORT-Konsens geht Wikidata vor (21 abweichende Positionen, im Bericht gelistet). Ein
  Konsens kann einen gemeinsam übernommenen Fehler bestätigen (D-056).
- Wertpapierstamm: Konsens heisst gleiche Meldung mehrerer Gesellschaften, nicht geprüfte
  Wahrheit; gemeinsame Datenlieferanten sind nicht erkennbar. Widersprüche werden nicht nach
  Mehrheit aufgelöst (613 ISIN mit mindestens 5 Gruppen gegen 1 bleiben offen; ob eine
  Mehrheitsregel zulässig ist, erst messen). Nur Papiere, die US-registrierte Fonds halten.

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
| Wertpapierstamm | 398'251 ISIN, davon 116'216 bestätigt (Datei 87 MB) |
| GLEIF-Liste Level 1 | 3'494'789 LEI-Datensätze, Stand 15.11.2026 (Archiv 486 MB, CC0) |
| SwissPRTR | 247 Standorte; 22'860 Emissionszeilen |
| Speicher | `C:\TransparenzDaten` rund 3.9 GB; Festplatte 34 GB frei |
| Tägliches Update | Windows-Task `ProjektTransparenz-DailyDataUpdate` (findet den Datenordner über `.env`) |

Details: `docs/DATA_SOURCES.md`, `docs/GLOBAL_MARKET_CATALOG.md`, `docs/ROADMAP.md`.
