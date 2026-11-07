# Datenquellen

**Stand 07.11.2026 (Session 2).** Aktiv sind ausschliesslich fiktive Demoquellen. Die erste
echte Quelle (GLEIF) ist angebunden und getestet, aber **deaktiviert**, bis ein echter Fonds
LEIs liefert. Grundsatz: **nur Quellen mit ausdrücklich erlaubter kommerzieller Nutzung oder
klar dokumentierter öffentlicher Datenfreigabe.** Öffentlich zugänglich heisst nicht
kommerziell nutzbar.

Statuswerte: **aktiv** · **angebunden (deaktiviert)** · **geprüft, geeignet** ·
**zu prüfen** (Lizenz/Zugang unklar) · **ausgeschlossen**

## Lizenzregister und automatische Sperre

Jede Quelle in `src/transparenz/config/sources.toml` trägt ihre Lizenzangaben selbst
(`license`, `license_url`, `terms_url`, `license_checked_on`, `commercial_use`,
`redistribution`, `attribution`). Eine **echte** Quelle wird automatisch **gesperrt** (kein
Abruf, auch kein Trockenlauf, Status «gesperrt» im Update-Protokoll), wenn

- kommerzielle Nutzung oder Weiterveröffentlichung nicht «ja» ist,
- die Originalseite der Nutzungsbedingungen (`terms_url`) oder die Lizenzbezeichnung fehlt,
- das Prüfdatum fehlt, in der Zukunft liegt oder **älter als 365 Tage** ist.

Umgesetzt in `src/transparenz/config/licensing.py`, getestet in `tests/test_licensing.py`.
Ein Test prüft die echte `sources.toml`: Läuft eine Lizenzprüfung ab, schlägt er Alarm. Dann
die Originalseite erneut lesen, diesen Abschnitt und `license_checked_on` nachführen.

## Lizenzprüfung vom 07.11.2026 (an den Originalseiten)

Geprüft wurden die Originalseiten selbst, nicht die Angaben der Vorlage (Recherche aus einem
anderen Chat). Zitate sind kurz und wörtlich. **Keine Rechtsberatung**: Die Einordnung ist eine
sorgfältige Lektüre der Bedingungen, keine juristische Prüfung (siehe `docs/recht/`).

### GLEIF – LEI-Daten Level 1 und Level 2 · Ergebnis: **freigegeben, angebunden (deaktiviert)**

| | |
|---|---|
| Original-URL | https://www.gleif.org/en/meta/lei-data-terms-of-use (Nutzungsbedingungen); API: https://api.gleif.org/api/v1, Doku: https://documenter.getpostman.com/view/7679680/SVYrrxuU |
| Lizenz | **CC0 1.0 Universal** – «The data available through the Access Service are provided under the CC0 licence». Der «Access Service» umfasst laut Einleitung Datei-Downloads und «Web Interfaces/APIs». |
| Lizenz-URL | https://creativecommons.org/publicdomain/zero/1.0/ |
| Kommerziell / Weiterveröffentlichung | ja / ja (CC0: keine Bedingungen). API-Doku: «There is no charge for the use of GLEIF's LEI data.» |
| Quellenangabe | **nicht verlangt** (keine Attributionspflicht gefunden). Wir nennen trotzdem «Quelle: GLEIF, LEI-Daten (CC0 1.0)». |
| Auflagen | kein Eindruck erwecken, eigene Daten/Dienste seien von GLEIF bereitgestellt oder gebilligt; GLEIF-Marke/Logo nur nach Rückfrage; keine Gewähr für Richtigkeit; GLEIF kann den Zugang bei Missbrauch sperren. |
| Technik | ohne Konto; **60 Anfragen pro Minute und Nutzer** (API-Doku); Golden Copy 3× täglich (Formate XML, CSV, JSON). |
| Level 2 | Mutter-Tochter-Beziehungen (Relationship Records) kommen über denselben Access Service; die Level-2-Seite nennt keine eigene, abweichende Lizenz. |
| Prüfdatum | 07.11.2026 |

### GLEIF/ANNA – ISIN-LEI-Zuordnungsdateien · Ergebnis: **ausgeschlossen (Lizenz ungeklärt)**

- Seite: https://www.gleif.org/en/lei-data/lei-mapping/download-isin-to-lei-relationship-files
- Die Seite nennt die Dateien «publicly available» und «open-source», beschreibt sie als
  «built upon a mapping process established by ANNA and certified by GLEIF», nennt aber **keine
  Lizenz**. Die Angabe der Vorlage («eigene Lizenzvereinbarung») konnte auf dieser Seite
  weder bestätigt noch widerlegt werden.
- Die GLEIF-API bietet ebenfalls ISIN-Abfragen an (`filter[isin]`, `/lei-records/{lei}/isins`,
  «provided according to the mapping process established by … ANNA»). **Diese Abfragen nutzt
  der Adapter bewusst nicht.** Wieder aufnehmen erst nach schriftlicher Klärung der Lizenz.

### SEC – Form N-PORT Data Sets · Ergebnis: **geprüft, lizenzrechtlich geeignet; fachlich offen**

| | |
|---|---|
| Original-URL | https://www.sec.gov/data-research/sec-markets-data/form-n-port-data-sets ; Bedingungen: https://www.sec.gov/privacy (Abschnitt «Website Dissemination») |
| Lizenz | keine Lizenz im Sinne von CC; **öffentliche Information**: «Information presented on sec.gov is considered public information and may be copied or further distributed by users of the web site without the SEC's permission.» |
| Kommerziell / Weiterveröffentlichung | Weiterverbreitung ausdrücklich ohne Erlaubnis zulässig; kommerzielle Nutzung wird **nicht erwähnt** (weder erlaubt noch verboten). Einordnung: «klar dokumentierte öffentliche Datenfreigabe». |
| Quellenangabe | erbeten, nicht verlangt: «Please consider appropriate citation to the SEC as the source.» |
| Auflagen | SEC-/EDGAR-Marken nicht in Firmen-/Domainnamen; Disclaimer der Datensätze: Daten stammen von den Fonds selbst («we cannot guarantee the accuracy of the data»), «not a substitute for such filings». Die Readme nennt die Daten «as-filed». |
| Technik | Fair Access: höchstens **10 Anfragen pro Sekunde**; User-Agent mit Firmenname **und E-Mail-Adresse** verlangt (welche Adresse, entscheidet Jonas). Neuester Datensatz: **2026q3_nport.zip, 440.95 MB**; 2026q2: 420.28 MB; 2026q1: 441.62 MB. Quartalsweise veröffentlicht. |
| Inhalt | nur **in den USA registrierte** Fonds (inkl. ETFs, ohne Geldmarktfonds). Je Position u. a. `ISSUER_NAME`, `ISSUER_LEI` («LEI (if any) of issuer»), `IDENTIFIER_ISIN`. Die Fonds melden die Zuordnung Wertpapier → Emittent damit selbst. |
| Nicht verifiziert | welche Monatsmeldungen öffentlich sind (Vorwissen: nur der dritte Monat je Quartal, mit Verzögerung); auf den gelesenen Seiten nicht bestätigt. |
| Prüfdatum | 07.11.2026 |
| Offen (fachlich) | Ist ein US-Fonds als erster echter Fonds für Schweizer Privatanleger:innen sinnvoll (D-020)? → Jonas: **später entscheiden** (STATUS.md). Kein Download ohne Zustimmung. |

### OFAC – Specially Designated Nationals (SDN) List · Ergebnis: **geprüft, lizenzrechtlich geeignet; fachlich offen**

| | |
|---|---|
| Original-URL | https://ofac.treasury.gov/sanctions-list-service ; Programm-Kürzel: https://ofac.treasury.gov/specially-designated-nationals-list-sdn-list/program-tag-definitions-for-ofac-sanctions-lists |
| Lizenz | **Beides, aber nicht von OFAC selbst formuliert.** (1) Als Werk der US-Bundesregierung nach 17 U.S.C. § 105 in den USA nicht urheberrechtlich geschützt (Public Domain). (2) Die Metadaten des Treasury auf data.gov (Datensatz `015-DO-083`) nennen `license: http://creativecommons.org/publicdomain/zero/1.0/` (**CC0 1.0**) und `accessLevel: public`: https://catalog.data.gov/harvest_record/b966879e-23e7-4b62-8da3-9d6b9caf1f56/raw. Auf den OFAC-Seiten selbst steht **keine** Lizenz- oder Urheberrechtsangabe. |
| Kommerziell / Weiterveröffentlichung | ja / ja (gemeinfrei bzw. CC0); keine Einschränkung gefunden. |
| Quellenangabe | nicht verlangt; wir nennen «Quelle: U.S. Treasury, OFAC, SDN List, Stand …». |
| Vorbehalte | Die data.gov-Metadaten sind von 2016 (`modified: 2016-11-01`), die Datensatzseite auf data.gov lieferte am Prüftag 404. Vor der Anbindung die aktuelle Datei-/Formatseite von OFAC erneut prüfen. |
| Technik | Formate laut OFAC-FAQ: XML, CSV («delimited») und Fixed-Field; Delta-Dateien über den Sanctions List Service. |
| Sanktionsgrund | Jeder Eintrag trägt Programm-Kürzel, z. B. `[GLOMAG]` = «Executive Order 13818 – Global Magnitsky», `[SDGT]` = Terrorismus, `[RUSSIA-EO14024]`. Anzuzeigen wäre das Kürzel mit der amtlichen Bezeichnung aus der Legende, nie eine eigene Deutung. |
| Prüfdatum | 07.11.2026 |
| Offen (fachlich) | Einordnung ins Belegmodell (eigener Sachverhaltstyp? welcher Status?) → Jonas: **später entscheiden** (STATUS.md). |

### US Department of Labor (ILAB) – List of Goods Produced by Child Labor or Forced Labor · Ergebnis: **geprüft, geeignet (später)**

- Seiten: https://www.dol.gov/agencies/ilab/reports/child-labor/list-of-goods ;
  Urheberrecht: https://www.dol.gov/general/aboutdol/copyright
- Lizenz: **Public Domain** (US-Bundesbehörde): «Materials created by the federal government
  are generally part of the public domain and may be used, reproduced and distributed without
  permission.» Achtung: «Not all materials on this website were created by the federal government.»
- Kommerziell / Weiterveröffentlichung: ja / ja; keine Einschränkung genannt ausser: kein
  Eindruck einer Billigung durch das DOL; Siegel und Logos nur mit Erlaubnis.
- Quellenangabe: freiwillig («You may properly credit … to the U.S. Department of Labor»).
- Inhalt: **Waren × Länder** (204 Waren, 82 Länder, Stand 05.09.2024), **keine Unternehmen**.
  Excel: `2024ListofGoodsExcel.xlsx`. Taugt nur als Länder-/Branchenrisiko, nie als Beleg
  gegen ein bestimmtes Unternehmen.
- Prüfdatum: 07.11.2026

### Weltbank – Datensätze · Ergebnis: **geprüft, geeignet je Datensatz (Metadaten prüfen)**

- Bedingungen: https://www.worldbank.org/ext/en/legal/terms-conditions/datasets
- Lizenz: **CC BY 4.0** – «Unless specifically labeled otherwise, these Datasets are provided
  … under a Creative Commons Attribution 4.0 International License (CC BY 4.0)»;
  Lizenz-URL https://creativecommons.org/licenses/by/4.0/
- Kommerziell / Weiterveröffentlichung: ja / ja (CC BY 4.0), mit Zusatzbedingungen
  (Schlichtung/Schiedsverfahren).
- Quellenangabe **verlangt**, Format: «The World Bank: Dataset name: Data source (if known)».
- Ausnahme: Datensätze Dritter können eingeschränkt sein («may not be redistributed or reused
  without the consent of the original data provider»), steht dann in den Metadaten.
- Vorbehalt: Die Bedingungsseite zeigte am Prüftag Platzhaltertext im Kopf und «Last Updated:
  Mar 23, 2018». Vor einer Anbindung die Metadaten des konkreten Datensatzes prüfen.
- Prüfdatum: 07.11.2026

### World Benchmarking Alliance (WBA) · Ergebnis: **ausgeschlossen (Bedingungen widersprüchlich)**

- https://www.worldbenchmarkingalliance.org/disclaimer: «Our work is licensed under the Creative
  Commons Attribution 4.0 International License.», mit Vorbehalt jederzeitiger Änderung.
- Dieselbe Seite gewährt für «website, Data Explorer, API» nur ein «limited, non-exclusive,
  non-transferable, revocable right» und behält Gebühren vor.
- Eine Angabe **CC BY-NC-ND 4.0** (laut Vorlage) wurde auf den gelesenen Seiten **nicht**
  gefunden; nicht gelesen wurden Benchmark-PDFs, Data Explorer und API-Doku. Der Widerspruch
  zwischen Datenlizenz und Tool-Bedingungen bleibt → ausgeschlossen bis zur schriftlichen Klärung.
- Prüfdatum: 07.11.2026

### Ausgeschlossen ohne erneute Prüfung in dieser Session

| Quelle | Grund (laut Vorlage, nicht erneut geprüft) |
|---|---|
| iShares-Downloads (BlackRock) | nur persönliche, nicht-kommerzielle Nutzung, keine Weiterverbreitung |
| NBIM-Ausschlussliste (Council on Ethics) | aus der Pipeline genommen |
| OpenSanctions | nicht-kommerziell frei, kommerziell lizenzpflichtig |

## Aktive und angebundene Quellen

| Quelle | Zweck | Format | Lizenz | Kommerziell | Status |
|---|---|---|---|---|---|
| Fiktiver ETF «Muster Nachhaltigkeit Welt» | Positionen | CSV | fiktiv, frei | ja | aktiv (Demo) |
| Fiktive Stammdaten | Unternehmen, Wertpapiere, Konzern | JSON | fiktiv, frei | ja | aktiv (Demo) |
| Fiktive Ausschlussliste «Ethikrat» + Abdeckung | Ausschlussentscheide | CSV | fiktiv, frei | ja | aktiv (Demo) |
| Fiktive Belegsammlung + Abdeckung | Sachverhalte versch. Herausgeber | CSV | fiktiv, frei | ja | aktiv (Demo) |
| GLEIF (`gleif_lei`) | LEI bestätigen, Name/Sitzland, direkte/oberste Mutter | API (JSON) | CC0 1.0 | ja | angebunden (deaktiviert) |

**GLEIF-Anbindung** (`src/transparenz/ingestion/gleif.py`): fragt die LEIs aus
`data/gleif/abfrageliste.txt` ab (höchstens 500, 100 pro Anfrage, 1.1 s Pause zwischen
Anfragen), lädt gemeldete direkte/oberste Mutterbeziehungen und deren LEI-Datensätze nach und
speichert die unveränderten Antworten als Rohdaten-Schnappschuss. Live geprüft am 07.11.2026
mit dem LEI von GLEIF selbst (`506700GE1G29325QX363`, 1 Anfrage), in einer temporären Datenbank.
Starten (nach Aktivierung): `python -m transparenz update --source gleif_lei --force`.
Zuordnungsquote messen: `python -m transparenz mapping --fund <ISIN>`.

## Kandidaten (noch nicht geprüft)

URLs sind Einstiegsseiten; die genaue Datenseite wird beim Onboarding verifiziert.

| Quelle | Zweck | URL | Lizenz (Vorwissen, unverifiziert) | Status |
|---|---|---|---|---|
| UBS ETF | Positionen UBS-ETFs | https://www.ubs.com | Website-Nutzungsbedingungen | zu prüfen |
| Xtrackers (DWS) | Positionen Xtrackers-ETFs | https://etf.dws.com | Website-Nutzungsbedingungen | zu prüfen |
| Halbjahres-/Jahresberichte | vollständige Positionen zum Stichtag | Anbieter-Websites | Urheberrecht des Anbieters | zu prüfen |
| OpenFIGI | ISIN → Instrument/Emittent | https://www.openfigi.com | eigene Nutzungsbedingungen | zu prüfen |
| Wikidata | Namen, Konzernbezüge (nur ergänzend) | https://www.wikidata.org | CC0 | zu prüfen |
| SVVK-ASIR | Ausschlussempfehlungen CH-Vorsorgeeinrichtungen | https://www.svvk-asir.ch | unklar | zu prüfen |
| Urgewald GCEL / GOGEL | Kohle / Öl und Gas | https://www.coalexit.org, https://gogel.org | eigene Bedingungen | zu prüfen |
| Business & Human Rights Resource Centre | Vorwürfe + Antworten | https://www.business-humanrights.org | unklar | zu prüfen |
| KnowTheChain | Benchmark Zwangsarbeit | https://knowthechain.org | unklar | zu prüfen |
| OECD-Kontaktstellen | Beschwerdeverfahren | https://mneguidelines.oecd.org | OECD-Bedingungen | zu prüfen |
| Forest 500 (Global Canopy) | Entwaldungsrisiko | https://forest500.org | unklar | zu prüfen |
| Global Forest Watch | Geodaten Waldverlust | https://www.globalforestwatch.org | je Datensatz, oft CC BY | zu prüfen |
| Behörden- und Gerichtsentscheide | Feststellungen, Urteile | je Behörde/Gericht | CH: amtliche Entscheide nicht geschützt (Art. 5 URG) | geplant (manuell) |

## Regeln

- Keine unzulässigen Scraper, keine Umgehung von Zugangsbeschränkungen (Login, Captcha, Paywall).
- Vor jedem Download einer echten Quelle: Jonas fragen (Dateiname, Quelle, Grösse).
- Ist eine Quelle unklar: Adapter mit fiktiven Testdaten bauen und dokumentieren, was fehlt.
- Daten, deren Lizenz eine Veröffentlichung ausschliesst, gehören nach `data/licensed/`
  (gitignored) und nie ins Repository.
- Jede Zuordnung (Wertpapier → Unternehmen, Tochter → Mutter) hat Quelle und Vertrauensstatus.

## Reihenfolge

1. **GLEIF** – erledigt (angebunden, deaktiviert bis zum ersten echten Fonds).
2. **Erster echter Fonds** – Kandidat SEC N-PORT (US-Fonds; Entscheid Jonas offen) oder eine
   frei lizenzierte UCITS-Quelle (noch keine gefunden).
3. **Erste Belegquelle** – Kandidat OFAC SDN (Einordnung ins Belegmodell offen).
4. Später: DOL ILAB (Länder-/Warenrisiko), Weltbank (Länderkennzahlen).

Erst wenn eine Quelle zuverlässig läuft (Import, Validierung, Aktualisierung), folgt die nächste.
