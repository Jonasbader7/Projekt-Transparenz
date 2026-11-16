# Datenquellen

## Quellenlage nach Stufen (14.11.2026, ersetzt die pauschalen Aussagen vom 13.11.)

Jede Quelle steht in genau einer Stufe. Eine Seite, die automatisch nicht lesbar war, gilt als
**ungeprüft**, nicht als «ohne Lizenz». «Ausgeschlossen» heisst: Die Bedingungen verbieten
gewerbliche Nutzung oder Bearbeitung ausdrücklich. Massstab weiterhin D-041.

| Stufe | Bedeutung |
|---|---|
| A. Keine geeignete Quelle gefunden | Gesucht, nichts mit Unternehmensbezug gefunden |
| B. Quelle vorhanden, Nutzungsrechte ungeklärt | Inhalt passt, Lizenz fehlt, ist zweideutig oder verlangt Registrierung/Anfrage |
| C. Nutzungsrechte dokumentiert, Unternehmenszuordnung offen | Lizenz an der Originalseite gelesen; Unternehmen nur mit Namen oder ohne Unternehmensbezug |
| D. Quelle technisch noch nicht integriert | Lizenz und Kennung tragen, Einbau fehlt |
| E. Integriert, ohne Treffer im untersuchten Fonds | Läuft im Pilot, findet im Fonds nichts |
| F. Integriert, mit Treffern | Läuft im Pilot |
| Ungeprüft | Originalseite automatisch nicht lesbar (403, 404, leer, nur JavaScript) |
| Ausgeschlossen | Bedingungen verbieten gewerbliche Nutzung oder Bearbeitung |

### Die vier am 13.11. genannten Ansätze: Entscheid je Quelle

| Quelle | Stufe | Was an der Originalseite steht | Entscheid und Begründung |
|---|---|---|---|
| [ATF AFMER](https://www.atf.gov/resource-center/data-statistics) (Produktionsberichte von US-Waffenherstellern) | **Ungeprüft** | Beide ATF-Seiten lieferten beim automatischen Abruf HTTP 403. Gelesen wurde nur die allgemeine Rechtsseite des Justizministeriums ([justice.gov/legalpolicies](https://www.justice.gov/legalpolicies)): Inhalte seiner Websites sind «unless otherwise indicated» gemeinfrei, die Seite gilt aber ausdrücklich nur für die Website des Ministeriums und verweist für Teilbehörden auf deren eigene Regeln. | **Nicht verwendet, bis die ATF-Seite gelesen ist.** Felder (Lizenznehmer, Lizenznummer, Stückzahlen je Waffenart), Ausschlüsse (z. B. Produktion für das US-Militär) und Verzögerung sind unbestätigt. Inhaltlich deckt AFMER nur die Kategorie «zivile Schusswaffen» in den USA ab und nennt Hersteller über die Waffenhandelslizenz, nicht über LEI. Nächster Schritt: Seite im Browser öffnen (Jonas oder Browser der App), Bedingungen und Spalten nachtragen. |
| [IDB, Dataset of Sanctioned Firms and Individuals](https://data.iadb.org/dataset/dataset-of-sanctioned-firms-and-individuals) | **C** | Datensatzseite (gelesen): Lizenz «Creative Commons Attribution 4.0 International». Eine CSV (146 KB, Stand 12.11.2026, rund 1'350 Zeilen, Zahl laut Schnittstelle geschätzt). Spalten: Name, Art (Firma oder Person), Land, Nationalität, von/bis, «Prohibited Practice» (Betrug, Korruption, Absprache, Nötigung, Behinderung), Sanktionsart (z. B. Ausschluss), Quelle. **Keine Kennung** (keine Registernummer, kein LEI). Die allgemeinen Nutzungsbedingungen der IDB (Fusszeile) waren nicht lesbar (403). | Nutzungsrechte dokumentiert, Zuordnung offen. Bei Einbau: natürliche Personen weglassen; Sanktionsgrund getrennt führen (nur «corruption» gehört zum Kriterium Korruption; Betrug und Absprache sind eine Information ohne Konfliktwirkung, D-043 Sanktionen); Zuordnung nur über das Namensverfahren mit Sitzland, dessen Präzision für diese Art von Namen erst gemessen werden muss. Erwarteter Nutzen für börsenkotierte Titel gering (meist kleinere Firmen in Lateinamerika). |
| [DOL WHD Compliance Action Data](https://catalog.data.gov/dataset/wage-and-hour-division-compliance-action-data) | **C (Felder ungeprüft)** | Katalogeintrag (gelesen): Lizenz «http://www.usa.gov/publicdomain/label/1.0/», Zugang «public», vierteljährlich, Stand 06.03.2026; «all concluded WHD compliance actions since FY 2005», inklusive ob Verstösse festgestellt wurden. DOL: Bundesmaterial «generally part of the public domain». Datenportal und Datenwörterbuch (data.dol.gov, dataportal.dol.gov) nur mit JavaScript, nicht gelesen. | Nutzungsrechte dokumentiert. **Spalten zu Kinderarbeit und zur Unternehmenskennung nicht bestätigt**; ob es mehr als Betriebsname und Adresse gibt, ist offen. Abgeschlossene Verfahren wären «Feststellung» im Sinn des Profils, aber je Betrieb, nicht je Konzern: Die Verbindung Betrieb → börsenkotierte Mutter fehlt. Nächster Schritt: Datenwörterbuch im Browser lesen. |
| [UMD/GLAD Global Forest Change 2000–2024](https://storage.googleapis.com/earthenginepartners-hansen/GFC-2024-v1.12/download.html) | **C (Unternehmensbezug fehlt)** | Downloadseite (gelesen): «Creative Commons Attribution 4.0 International License», Quellenangabe «Hansen/UMD/Google/USGS/NASA». Rasterdaten 30 m, Kacheln 10×10 Grad, Ebenen Baumbedeckung 2000, Zuwachs, Verlustjahr. Die Seite sagt nichts über Unternehmen, Konzessionen oder Eigentümer. «Verlust» umfasst auch Brand, Holzschlag und Plantagenumtrieb; Flächen sollen nicht aus Pixelzählungen geschätzt werden. | Lizenz trägt, aber **allein kein Unternehmensbeleg** (Kriterium Entwaldung: «Satellitensignale allein reichen nicht»). Nutzbar erst mit belastbarer räumlicher und geschäftlicher Verbindung (Konzessions- oder Betriebsflächen mit Eigentümerkennung unter freier Lizenz). Eine solche Quelle ist nicht gefunden. Kein Einbau. |

### Alle bisher geprüften Quellen nach Stufe

| Stufe | Quellen |
|---|---|
| **F. Integriert, mit Treffern** | Finansinspektionen Fondinnehav (Positionen); Wikidata (ISIN → Unternehmen, Branche, Registernummern, CC0); GLEIF (LEI, Konzernbeziehungen, Namens- und Registernummernsuche, CC0); EU-Emissionshandel (Lizenz als Auslegung, D-041); GEM Energy Ownership Tracker, Global Oil and Gas Plant Tracker und Global Coal Plant Tracker (CC BY 4.0); SwissPRTR |
| **E. Integriert, ohne Treffer im untersuchten Fonds** | SwissPRTR in einzelnen Pilotfonds ohne zugeordnete Position; Treffer je Fonds lokal unter `C:\TransparenzDaten\notizen\` dokumentiert, nicht veröffentlicht |
| **D. Noch nicht integriert** | Wikidata «CO2-Fussabdruck» (P5991); UK Sanctions List (OGL, Registernummern); Kanada GHGRP (OGL; Spalten noch lesen) |
| **C. Nutzungsrechte dokumentiert, Zuordnung offen** | IDB-Sanktionen; DOL WHD; UMD/GLAD; Climate TRACE; US EPA GHGRP (Muttergesellschaften mit Namen); US CBP Einfuhrsperren; US SEC FCPA; UK Serious Fraud Office; GEM Coal Project Finance Tracker und Gas Finance Tracker (CC BY 4.0 laut «About»-Blatt der Dateien; Geldgeber nur mit Namen wie «JP Morgan»); GEM Öl- und Gasfelder (Eigentümer nur mit Namen) |
| **B. Nutzungsrechte ungeklärt** | SVVK-ASIR (Registrierung nötig); Australien NGER (zweideutig); Trase (Anfrage nötig); US DHS UFLPA (keine Angabe); Etikkrådet; World Benchmarking Alliance; filings.xbrl.org; Science Based Targets; GLEIF/ANNA ISIN–LEI; Japan Treibhausgas-Meldesystem |
| **Ungeprüft** | ATF AFMER (403); US DOJ FCPA-Fallliste (404); EU-Zwangsarbeitsdatenbank (429); NZDPU; Wikirate; IBAMA; SPOTT; OFAC-Liste; US-Liste «1260H»; EU-Sanktionsliste; UK-Emissionshandel; Text der Richtlinie 2014/24/EU auf EUR-Lex (leere Antwort; für die Begründung der Korruptionsdauer am Original nachzulesen) |
| **Ausgeschlossen** | Norges Bank (nur privat); Weltbank-Sperrliste (keine gewerbliche Nutzung); Urgewald GCEL/GOGEL (öffentliche Fassung nicht kommerziell); Forest 500 (CC BY-NC); InfluenceMap; Brasilien «Lista Suja» (CC BY-ND, Personen) |
| **A. Keine geeignete Quelle gefunden** | Biodiversität, Wasser, Ressourcen/Abfall, Menschenrechte/Landrechte (je Unternehmen, frei gewerblich nutzbar); Stromabnahme- und Lieferverträge mit Kennung |

## Quellensuche 13.11.2026: Kriterien, Korruption, Emissionen (D-041)

Auftrag Jonas: Belege für Waffen, Zwangs-/Kinderarbeit, Entwaldung und Korruption sowie mehr
Emissionsdaten finden; verwendet wird **nur**, was nachweislich gewerblich genutzt werden darf.
Rund 40 Quellen an den Originalseiten gelesen (Lizenz, Kennungen, Format). **Nichts
heruntergeladen, nichts eingebaut. Keine Rechtsberatung.** «Nicht gelesen» heisst: Seite
lieferte Fehler oder sperrt automatische Abrufe; das ist kein Urteil über die Quelle.

**Massstab (D-041):** Eine Quelle ist nur «freigegeben», wenn die Originalseite eine benannte
Lizenz oder eine ausdrückliche Gemeinfreiheits- bzw. Weiterverwendungsaussage trägt, die
gewerbliche Nutzung, Speicherung, Ableitung und Weitergabe erlaubt. «Öffentlich abrufbar»,
«open» ohne Lizenz und Auslegungen genügen nicht.

### Freigegeben nach Massstab (Kandidaten für den Einbau)

| Quelle | Wofür | Lizenz laut Original | Kennung | Einordnung |
|---|---|---|---|---|
| Climate TRACE | Emissionen je Anlage weltweit (Schätzwerte) | CC BY 4.0, «for any purpose, including commercial use» ([Terms](https://climatetrace.org/terms)) | Anlagen-ID, Eigentümer mit Namen; LEI nicht belegt | **geeignet als Kennzahl «geschätzt»**. Ausnahmen laut Terms: Länderdaten (EDGAR, FAOSTAT, CEDS) und Teile von «Other manufacturing» (E-PRTR, EPA FLIGHT, Israel PRTR) haben eigene Bedingungen → diese Teile weglassen. Zuordnung über Namen = nur mit bestätigtem Entscheid. |
| US EPA, Greenhouse Gas Reporting Program | Gemeldete Emissionen je Anlage, USA; Datei «Reported Parent Companies» mit Eigentumsanteil | «all data produced by the U.S EPA is by default in the public domain» ([EPA Data License](https://edg.epa.gov/EPA_Data_License.html)) | Name der US-Muttergesellschaft, keine Kennung | **geeignet** (zwei Drittel des Pilotfonds sind US-Titel). Zuordnung nur über bestätigte Namensentscheide. |
| Kanada, Greenhouse Gas Reporting Program | Gemeldete Emissionen je Anlage | Open Government Licence – Canada, «including for commercial purposes» ([Lizenz](https://open.canada.ca/en/open-government-licence-canada)) | Spalten der Datei nicht gelesen | **geeignet**, Kennungen vor Einbau prüfen |
| Australien, Clean Energy Regulator (NGER) | Gemeldete Konzernemissionen Scope 1 und 2 | CC BY 4.0 für die Website ([Copyright](https://cer.gov.au/about-us/our-policies/copyright)); dort steht aber auch «use our website solely for commercial practices» unter «nicht erlaubt» | Spalte «Identifying details» im ABN-Format | **Lizenz zweideutig → nicht freigegeben**, schriftlich nachfragen |
| Wikidata, Eigenschaft «CO2-Fussabdruck» (P5991) | Von Unternehmen gemeldete Emissionen, v. a. schwedische Firmen (Projekt Klimatkollen) | CC0 ([Wikidata:Licensing](https://www.wikidata.org/wiki/Wikidata:Licensing)) | Wikidata-ID, bereits über ISIN verknüpft | **sofort nutzbar mit bestehender Kette**; Abdeckung noch nicht gemessen; jede Angabe braucht ihre Belegstelle |
| OpenFIGI | ISIN → Wertpapier, Ticker, Börse | FIGI gemeinfrei, «for any purpose, commercial or non-commercial» ([Terms](https://www.openfigi.com/docs/terms-of-service)) | FIGI; **kein Emittent, kein LEI** | geeignet für Wertpapier-Stammdaten, hilft nicht bei Position → Unternehmen |
| US CBP, Withhold Release Orders | Zwangsarbeit: Einfuhrsperren | «in the public domain», Hinweis «not endorsed by CBP» Pflicht ([Copyright](https://www.cbp.gov/site-policy-notices/copyright-notice)) | Felder nicht gelesen, vermutlich Name | **geeignet als «Verdachtsmassnahme»**, kein bestätigter Verstoss |
| US-Arbeitsministerium, Vollzugsdaten (WHD) | Kinderarbeit, Arbeitsrecht: Feststellungen je Arbeitgeber | Bundesmaterial «generally part of the public domain» ([DOL](https://www.dol.gov/general/aboutdol/copyright)) | Datenkatalog nicht lesbar (leere Seite) | Lizenz geeignet, **Felder ungeprüft** |
| US SEC, FCPA-Fälle | Korruption: Vollzugsfälle je Jahr | «public information and may be copied or further distributed … without the SEC's permission» ([SEC](https://www.sec.gov/privacy)) | nur Name; HTML-Liste je Jahr | **geeignet**; gewerbliche Nutzung nicht wörtlich genannt (wie bei N-PORT) |
| US-Justizministerium, FCPA-Fälle | Korruption: Strafverfahren | «in the public domain and may be copied and distributed without permission» ([DOJ](https://www.justice.gov/legalpolicies)) | Fallliste nicht lesbar (404) | Lizenz geeignet, **Liste ungeprüft** |
| UK Serious Fraud Office | Korruption: laufende und abgeschlossene Fälle | Open Government Licence v3.0 (Fusszeile gov.uk) | nur Name; 29 Fälle | geeignet, klein; OGL-Text selbst nicht gelesen |
| UK Sanctions List | Sanktionen mit Grund | Open Government Licence v3.0 | Registernummern, keine LEI/ISIN; CSV/XML | geeignet als Beleg mit Sanktionsgrund |

### Nicht freigegeben

| Quelle | Wofür | Befund an der Originalseite |
|---|---|---|
| Norges Bank (NBIM), Ausschlussliste | Waffen, Korruption, Menschenrechte | «exclusively for personal non-commercial use» ([Disclaimer](https://www.nbim.no/en/disclaimer/)) → **ausgeschlossen** |
| SVVK-ASIR, Ausschlussempfehlungen | Geächtete Waffen, Kernwaffen | gewerbliche Nutzung nur nach **Registrierung** und AGB ([Impressum](https://www.svvk-asir.ch/en/imprint-and-data-protection)); Liste als CSV, nur Namen → möglich, wenn Jonas sich registriert und die AGB es erlauben |
| Weltbank, gesperrte Firmen | Korruption | «you may not make any derivative work or commercial use» (allgemeine Bedingungen) → **ausgeschlossen** ohne schriftliche Zustimmung |
| Etikkrådet (Norwegen) | Waffen, Menschenrechte | keine Lizenzangabe gefunden |
| US DHS, UFLPA Entity List | Zwangsarbeit | keine Lizenz- oder Gemeinfreiheitsangabe auf den Seiten; nur Namen. Als US-Bundeswerk vermutlich gemeinfrei, aber nicht ausgewiesen → **nicht freigegeben nach Massstab** |
| Brasilien, «Lista Suja» (Arbeitsministerium) | Zwangsarbeit | Website unter CC BY-**ND** 3.0 (keine Bearbeitungen); viele natürliche Personen mit Steuernummer → **ausgeschlossen** |
| KnowTheChain, Forests & Finance | Zwangsarbeit, Entwaldung | keine Lizenz; «All rights reserved» |
| World Benchmarking Alliance | Menschenrechte, Natur | weiterhin widersprüchlich (CC BY 4.0 und zugleich widerrufliches Nutzungsrecht mit Gebührenvorbehalt) |
| InfluenceMap Carbon Majors, Net Zero Tracker | Emissionen, Ziele | nur nicht-kommerziell |
| GLEIF/ANNA ISIN–LEI | Zuordnung | weiterhin **keine Lizenz benannt**; die CC0-Klausel der GLEIF-Bedingungen nennt die Zuordnungsdateien nicht; Vertragsstrafe CHF 100'000 je Verstoss gegen die Bedingungen → nicht ohne schriftliche Klärung |
| filings.xbrl.org (Geschäftsberichte, LEI-Schlüssel) | gemeldete Emissionen | «no restrictions», aber keine Lizenz und Urheberrecht der Berichte offen |
| Japan, Treibhausgas-Meldesystem | gemeldete Emissionen mit Unternehmensnummer und ISIN-Feld | Fusszeile «All rights reserved»; Nutzungsbedingungen auf anderer Seite, nicht gelesen → **vielversprechend, ungeprüft** |
| ADEME «Bilans GES» (Frankreich) | gemeldete Emissionen mit SIREN | Licence Ouverte 2.0, aber Datensatz ist eine private Zusammenstellung eines gelöschten Kontos, nicht der amtliche Export |
| Science Based Targets | Klimaziele | keine Nutzungsbedingungen gefunden |

### Nicht gelesen (technisch)

NZDPU (Bedingungen 404), Wikirate (403; laut Suchtreffer CC BY 4.0 mit Gebührenvorbehalt für
gewerbliche API-Nutzung), IBAMA Brasilien (403), SPOTT (500), OFAC-Liste chinesischer
Rüstungsfirmen (404), US-Liste «1260H» (Federal Register sperrt Automaten), EU-Sanktionsliste
(leere Seite), UK-Emissionshandel (404), Schweizer Emissionshandelsregister (keine
öffentlichen Tabellen gefunden), Inter-Amerikanische Entwicklungsbank (403). Diese kann Jonas
im Browser öffnen; dann lässt sich die Lizenz in wenigen Minuten nachtragen.

### Was das für die Kriterien heisst

| Kriterium | Freigegebene Quelle | Stand |
|---|---|---|
| Kohle, fossile Expansion | GEM (CC BY 4.0, LEI) | **belegt, im Pilot** |
| Korruption | SEC, DOJ, UK SFO (nur Namen) | Quelle vorhanden; braucht Namensentscheide |
| Zwangs-/Kinderarbeit | CBP (Verdachtsmassnahme), DOL (Felder ungeprüft) | teilweise; kein bestätigter Verstoss mit Kennung |
| Arbeitsrechte | DOL-Vollzugsdaten (Felder ungeprüft) | offen |
| Umweltverschmutzung | Kennzahlen (SwissPRTR, EU-ETS, EPA); Vollzugsdaten EPA ungeprüft | Kennzahlen ja, Verstösse offen |
| Waffen | keine | nur über SVVK-Registrierung oder schriftliche Erlaubnis |
| Entwaldung, Biodiversität, Wasser, Ressourcen, Menschenrechte | keine | unbekannt |

**Ehrliches Fazit:** Informationen gibt es zu allen Themen. Frei gewerblich nutzbar **und**
mit harter Kennung ist fast nichts davon. Der grösste Hebel sind gemeinfreie US-, UK- und
kanadische Behördendaten, die Unternehmen nur mit Namen nennen. Sie werden nutzbar, sobald
Namenszuordnungen als bestätigte Entscheide gespeichert sind (D-042). Für Waffen und
Entwaldung führt der Weg über schriftliche Erlaubnis der Herausgeber.

## GEM im Pilotbericht (12.11.2026, D-040)

Verwendet wird nur der **Global Energy Ownership Tracker** (CC BY 4.0, Vermerk in der Datei)
mit den Blättern Coal Plant, Coal Mine, Gas Plant, LNG Terminal, Gas Pipeline und Oil & NGL
Pipeline Ownership. Zuordnung ausschliesslich über GEMs eigene LEI-Spalte; die GLEIF-GEM-Datei
(Lizenz unbenannt) bleibt ungenutzt. Quellenangabe im Bericht: «Global Energy Monitor, Global
Energy Ownership Tracker, October 2026 (CC BY 4.0); Daten gefiltert, Anteile und Status
zusammengefasst», mit Lizenzlink und dem Hinweis, dass GEM die Auswertung nicht geprüft oder
unterstützt hat (CC BY 4.0, Abschnitt 2 «No endorsement»). Gas Finance und LNG Carrier
(ohne Lizenzvermerk) sowie Stahl/Zement bleiben ungenutzt.

## GEM-Daten geladen und geprüft (11.11.2026)

Jonas hat das GEM-Formular selbst ausgefüllt. Geladen: `gem-data.zip` (197 MB) mit Coal
Plant, Coal Mine (inkl. Ergänzungen), Coal Terminals, Oil and Gas Extraction, Oil and Gas
Plant, Oil/NGL Pipelines, Gas Pipelines, LNG Terminals, LNG Carrier, Energy Ownership, Coal
Project Finance, Gas Finance, Iron and Steel, Cement. Lokal unter
`data/raw/external/gem/2026-11-11/` mit Hash und Nachweis; Git-ignoriert.

- **Lizenz:** 16 von 18 Excel-Dateien enthalten selbst «Distributed under a Creative Commons
  Attribution 4.0 International License» samt empfohlener Zitierweise. **Ohne Vermerk:** Gas
  Finance Tracker und LNG Carrier Tracker; bis zur Klärung nicht verwenden.
- **Kennungen:** Der Energy Ownership Tracker führt je Rechtsträger eine GEM-ID und eine
  LEI-Spalte (6'482 LEIs; 13'641 «not found»). Die GLEIF-GEM-Datei stimmt damit überein:
  6'471 von 6'860 Paaren auch in der GEM-Spalte, keine widersprüchliche Zuordnung.
  Besitzblätter je Anlagetyp nennen oberste Mutter (GEM-ID), durchgerechneten Anteil
  («Share»), vollständige Besitzkette mit Prozenten, Status und Kapazität.
- **Lücke:** Der Oil and Gas Extraction Tracker nennt Eigentümer von Öl-/Gasfeldern **nur
  mit Namen**, ohne GEM-ID. Ohne Namensabgleich (D-013) nicht zuordenbar.
- **Falle:** GEM verfolgt Besitzketten bis ganz nach oben, auch über Portfolio-Beteiligungen
  ab 5 % und Treuhand-/Nominee-Gesellschaften. Ungefiltert «besitzen» Vermögensverwalter
  und Börsen Hunderte Anlagen (eine Depotbank über tausend Kohleeinheiten mit < 10 % oder
  unbekanntem Anteil; eine Börse Hunderte über ihre Nominee-Gesellschaft).

**Messung am Pilotfonds** (277 bestätigt zugeordnete Positionen; nur Kennungen): Mit
einer Anteilsregel (≥ 50 % Besitz, 20–50 % bedeutende Minderheit separat, < 20 % oder
unbekannt nicht gezählt) bleiben wenige Positionen mit Mehrheit oder bedeutender Minderheit
an Kohle- bzw. Gas-/Öl-Anlagen; ohne Regel erscheinen vor allem Banken,
Vermögensverwalter und Börsen. Zahlen und Namen lokal unter `C:\TransparenzDaten\notizen\` dokumentiert, nicht veröffentlicht.

Für den Kriterienbeleg offen (Entscheid Jonas): Anteilsregel; ob Gaskraftwerke, LNG-
Terminals und Pipelines unter «Öl-/Gas-Expansion» fallen (heute: neue Felder und
Förderkapazitäten); ob GEM-Besitzketten (mit Quellen-URL) als Zurechnung gelten, obwohl
sie nicht von GLEIF bestätigt sind (D-012).

## Belegquellen für Ausschlusskriterien (geprüft 11.11.2026)

Auftrag Jonas: eine Quelle für die fünf Kriterien aus `criteria.toml` suchen (Kohle,
Öl-/Gas-Expansion, geächtete Waffen, Zwangs-/Kinderarbeit, Entwaldung). Massstab: Lizenz
erlaubt spätere gewerbliche Nutzung **und** harte Unternehmenskennung (keine Namensfusion,
D-013). **Keine Rechtsberatung.**

| Quelle | Kriterium | Lizenz laut Original | Kennung | Ergebnis |
|---|---|---|---|---|
| Global Energy Monitor (GEM): Coal Plant, Coal Mine, Oil & Gas Extraction, Energy Ownership Tracker | Kohle, Öl-/Gas-Expansion | **CC BY 4.0**, vollständiger Lizenztext unter [GEM-Lizenzseite](https://globalenergymonitor.org/creative-commons-license); das Download-Formular verweist darauf und protokolliert «Creative Commons Attribution 4.0 International (CC BY 4.0)» | GEM Entity ID; über die GLEIF-Zuordnung mit dem LEI verbunden | **geeignet, Download nur über Formular** (Name, E-Mail, Organisation, Branche, Verwendungszweck ≥ 100 Zeichen). Nicht ausgefüllt: persönliche Angaben gibt nur Jonas selbst ein. Den Kartendienst im Hintergrund nicht angezapft (Zugangsweg nicht umgehen). |
| GLEIF/GEM Entity ID-to-LEI | Zuordnung für GEM | «open-source relationship file», keine Lizenz benannt ([Seite](https://www.gleif.org/en/lei-data/lei-mapping/download-gem-to-lei-relationship-files)) | LEI ↔ GEM-ID, 6'860 Paare, je LEI genau eine GEM-ID | nur lokal für eine Messung geladen (`data/raw/external/gleif_gem_lei/2026-11-04/`, mit Nachweis), nicht im Bericht |
| Urgewald GCEL / GOGEL | Kohle, Öl-/Gas-Expansion | öffentliche Version nur nicht-kommerziell; «Commercial users like financial institutions or consultants must ask for a license» ([GCEL-Bedingungen](https://www.coalexit.org/terms-conditions), [GOGEL-Bedingungen](https://gogel.org/terms-conditions-without-identifiers)) | öffentliche Version ohne Kennungen; Version mit Kennungen nur auf Anfrage für Finanzinstitute | **ausgeschlossen** |
| Forest 500 (Global Canopy) | Entwaldung | CC BY-NC 4.0 ([Bedingungen](https://forest500.org/terms-and-conditions/)) | nicht bestätigt | **ausgeschlossen** (nicht kommerziell) |
| Trase | Entwaldung | CC BY 4.0 nur für Grafiken der Website belegt; «If you are using our data for commercial purposes, please get in touch» ([Datensatzseite](https://trase.earth/open-data/datasets/supply-chains-brazil-soy)) | Exporteurgruppe, Kennung nicht bestätigt | **nicht freigegeben** (Anfrage nötig) |
| Global Forest Watch | Entwaldung | je Datensatz eigene Lizenz ([Bedingungen](https://globalnaturewatch.org/terms/)) | keine Unternehmensverknüpfung belegt | nicht geeignet für Unternehmensbelege |
| US DHS UFLPA Entity List | Zwangsarbeit | keine Lizenz- oder Gemeinfreiheitsangabe auf den gelesenen Seiten ([Liste](https://www.dhs.gov/uflpa-entity-list)) | **nur Name** (mit Alias), keine Kennung | ohne Namensfusion nicht zuordenbar |
| US CBP Withhold Release Orders | Zwangsarbeit | Portal-Bedingungen verlangen Hinweis «not endorsed by CBP» und Abrufdatum ([Bedingungen](https://www.cbp.gov/newsroom/stats/cbp-public-data-portal/terms-and-conditions)) | CSV nicht gelesen; vermutlich Name | offen |
| NBIM / Etikkrådet | Waffen, Menschenrechte | keine Lizenzangabe; Empfehlungsseite 404 | **nur Name** | ohne Namensfusion nicht zuordenbar |
| EU-Zwangsarbeitsverordnung (EU) 2024/3015, Datenbank | Zwangsarbeit | Seite nicht ladbar (HTTP 429) | – | ungeprüft |

**Messung ohne GEM-Trackerdaten (nur GLEIF-GEM-Zuordnung, exakte LEI-Gleichheit):** Von den
277 bestätigt zugeordneten Positionen des Pilotfonds sind **49 (23.94 %)** bei GEM als
Rechtsträger erfasst, 47 direkt und 2 über eine von GLEIF vollständig bestätigte Tochter.
**Das ist kein Beleg für Kohle oder Öl/Gas**: Unter den Treffern sind Technologiekonzerne
und Grossbanken, weil GEM auch Finanzierer, Minderheitsaktionäre und andere Anlagetypen führt. Ob
ein Unternehmen Kohlekraftwerke, Kohleminen oder neue Öl-/Gasfelder (in Planung, im Bau)
besitzt, steht erst in den Tracker-Dateien.

**Ergebnis:** Für «Kohle» und «Öl-/Gas-Expansion» gibt es mit GEM eine Quelle mit passender
Lizenz und harter Kennung; der Download braucht Jonas' eigene Angaben im GEM-Formular. Für
geächtete Waffen, Zwangs-/Kinderarbeit und Entwaldung wurde keine Quelle gefunden, die
gewerbliche Nutzung erlaubt **und** Unternehmen über eine Kennung identifiziert. Diese drei
Kriterien bleiben «unbekannt».

## Zweite Belegquelle: EU-Industrieemissionen und EU-Emissionshandel (geprüft 11.11.2026)

Frage: Gibt es eine Belegquelle ausserhalb der Schweiz mit klarer Lizenz **und** harter
Kennung (keine Zuordnung über Namen)? Beide Lizenzstellen im Browser selbst gelesen.
**Keine Rechtsberatung.** Das EU-Emissionshandelsregister ist seit D-038 im **lokalen
Pilot-Skript** eingebaut (siehe Ergebnis unten), nicht im Screening und nicht auf der Website.

| | EEA Industrial Reporting (IED/E-PRTR), Version 16, Feb. 2026 | EU-Emissionshandel: Union Registry, Tagesauszüge |
|---|---|---|
| Original | [Datensatz](https://www.eea.europa.eu/en/datahub/datahubitem-view/9405f714-8015-4b5b-a63c-280b82861b3d), [Katalogeintrag](https://sdi.eea.europa.eu/catalogue/srv/api/records/657ac3cb-affa-4295-a4a9-27b4f539adab) | [Union Registry Public Website](https://union-registry-data.ec.europa.eu/) |
| Lizenz | im Datensatz selbst: «License CC-BY 4.0 … Copyright holder: European Environment Agency (EEA).» | keine Angabe an den Dateien; die Seite verlinkt als «Legal notice» die [Kommissionsseite](https://commission.europa.eu/legal-notice_en): «content owned by the EU on this website is licensed under the Creative Commons Attribution 4.0 International (CC BY 4.0) licence» |
| Kommerziell / Speichern / Ableiten / Weitergabe | ja / ja / ja / ja (CC BY 4.0), Quellenangabe und Änderungshinweis Pflicht | ja / ja / ja / ja **als Auslegung** der verlinkten Kommissionsregel; «names» und Inhalte Dritter sind dort ausgenommen |
| Automatisierter Abruf | nicht geregelt; Dateien über ein Download-Portal | nicht geregelt; statische Dateien, täglich neu |
| Inhalt | Freisetzungen und Abfalltransfers grosser Industriebetriebe 2007–2024 | verifizierte Jahresemissionen je Anlage (t CO2e), Zuteilungen, Abgaben; 24'857 Anlagen-/Betreiberzeilen |
| Kennung des Unternehmens | **nur Name** (`parentCompanyName`, Freitext), optional Website. Kein LEI, keine Registernummer. Zusätzlich je Anlage eine EU-ETS-Kennung | **LEI des Kontoinhabers** bei 5'528 Zeilen (5'450 prüfzifferngültig, 3'141 verschiedene LEIs); **Registernummer** bei 24'385 Zeilen (98 %) |
| Ergebnis | **Lizenz geeignet, allein nicht zuordenbar** (keine Namensfusion). Nur über die ETS-Kennung als Brücke nutzbar | **Kandidat für die zweite Belegquelle**; Lizenzauslegung offen |
| Geladen | nur das Metadaten-PDF gelesen, keine Daten | `operators_daily` (1.9 MB) und `operators_yearly_activity_daily` (6.1 MB) nach `data/raw/external/eu_ets_union_registry/2026-11-11/`, mit Hash und Nachweis |

Einmalige Messung am Pilotfonds (285 Positionen mit genau einem LEI), nur exakte LEI-Gleichheit.
Konzernbezug aus der GLEIF-Beziehungsdatei vom 11.11.2026 (CC0, 23 MB, lokal unter
`data/raw/external/gleif_rr_golden_copy/2026-11-11/`): 261'325 Mutterbeziehungen, davon
104'265 aktiv, veröffentlicht und vollständig bestätigt; nur diese zählen (D-012).

| Stufe | Positionen | Gewicht in % |
|---|---:|---:|
| Kontoinhaber-LEI = LEI der Position | 3 | 1.25 |
| zusätzlich über bestätigte Tochterfirma | 12 | 3.18 |
| **mit EU-ETS-Anlage insgesamt** | **15** | **4.43** |

46 Anlagen verknüpft. Zum Vergleich: SwissPRTR allein ergab 1 Position (0.71 %).

Grenzen und offene Punkte:

- Nur 22 % der Registerzeilen tragen einen LEI. Die Registernummer (98 %) wäre der grössere
  Hebel, verlangt aber den Abgleich mit der Registernummer in den GLEIF-Stammdaten (Golden
  Copy Level 1, 485 MB) samt Registerstelle. Noch nicht versucht.
- Ein Emissionshandelseintrag ist ein amtlich verifizierter Jahreswert, kein Verstoss. Der
  Fonds ist zu zwei Dritteln in US-Titeln; das Register deckt nur Anlagen im EU-ETS ab.
  «Kein Eintrag» heisst deshalb nie «keine Emissionen».
- Die LEI im Register stammt vom Kontoinhaber selbst (vom nationalen Verwalter freigegeben).
  Einzelne Treffer wirken ungewöhnlich (z. B. sehr kleine Jahreswerte) und brauchen vor einer
  Anzeige eine Sichtprüfung.
- Offene Rechtsfrage: Gilt die CC-BY-Regel der Kommissionsseite wörtlich für die Registerdateien,
  und sind Firmennamen der Kontoinhaber von der Namensausnahme betroffen?
- EEA-Metadaten nennen zusätzlich den Vermerk «public access limited according to Article
  13(1)(a) of the INSPIRE Directive»; Bedeutung für die Weiterverwendung nicht geklärt.

**Ergebnis nach Einbau in den Pilot (D-038):** Ein Beleg zählt nur bei mindestens einem
verifizierten Jahreswert («n/a» ist kein Wert). Deshalb fallen zwei Unternehmen aus der
Messung oben heraus (Anlage registriert, aber kein verifizierter Wert).

| Stufe | Positionen | Gewicht in % |
|---|---:|---:|
| mit Beleg aus mindestens einer Quelle | 14 | 3.73 |
| – SwissPRTR | 1 | 0.71 |
| – EU-Emissionshandel | 13 | 3.02 |
| – davon Namensabweichung, Sichtprüfung nötig | 1 | 0.86 |
| nur unbestätigter Konzernhinweis (kein Beleg übertragen) | 6 | 4.91 |

Sichtprüfung von Hand (alle 14): Die meisten sind EU-Töchter mit eigenem LEI und von GLEIF
vollständig bestätigter Mutterbeziehung. Auffällig:

- In einem Fall führt das Register unter dem LEI eines Konzerns einen Kontoinhaber, der eine
  andere Gesellschaft ist. Automatisch markiert («Sichtprüfung nötig»), nicht entfernt.
- Sehr kleine Jahreswerte (z. B. ein Flugzeugbetreiber mit wenigen Tonnen CO2e).
- Anlagen mit widerrufener Genehmigung oder letztem Wert vor Jahren; Jahr und Widerruf
  stehen je Anlage im Bericht.
- Konzernbezüge, die GLEIF nur mit «ENTITY_SUPPLIED_ONLY» bzw. «PARTIALLY_CORROBORATED»
  führt, übertragen keinen Beleg.

**Nachtrag D-039 (zeitliche Zurechnung und Identitätskonflikte):** Seit dem verständlichen
Pilotbericht zählen nur noch Belege mit widerspruchsfreier Zuordnung, ohne Identitätskonflikt
und mit Konzernbeziehung über das ganze Emissionsjahr. Ergebnis: **11 Positionen (2.02 %)**
statt 14. Ein Identitätskonflikt und zwei Fälle mit Emissionsjahren vor Beginn der Beziehung
stehen separat. Einzelfälle mit Namen lokal unter `C:\TransparenzDaten\notizen\` dokumentiert, nicht veröffentlicht.

## Datenversorgung für die Fondsanalyse: Vergleich und erster echter Fonds (11.11.2026, D-037)

Auftrag Jonas: nicht eine perfekte Gratisquelle suchen, sondern die **Kombination**, die das
geplante Produkt erlaubt. Die drei Bausteine dürfen aus verschiedenen Quellen kommen:
(1) Fondspositionen, (2) Wertpapier → Unternehmen, (3) Unternehmen → Beleg. Alle Aussagen
stammen aus den verlinkten Originalseiten (gelesen am 11.11.2026). **Keine Rechtsberatung.**
«Nicht geregelt» heisst: Die Seite sagt dazu nichts, weder Erlaubnis noch Verbot.

### Neu: Finansinspektionen (FI, Schweden) – Register «Fondinnehav» · Ergebnis: **geeignet, im Pilot verwendet**

| | |
|---|---|
| Original-URL | [Register](https://www.fi.se/sv/vara-register/fondinnehav/), [Quartalsdateien](https://www.fi.se/sv/vara-register/fondinnehav-per-kvartal/) |
| Bedingungen | [Öppen data](https://www.fi.se/sv/om-fi/om-webbplatsen/oppen-data/) («Senast granskad: 2026-11-05»), im Browser nachgelesen |
| Wortlaut | «FI:s information är fri att användas. Ange källa, FI och datum.» und «FI:s data är fritt tillgänglig utan avgift och får fritt bearbetas och vidareutnyttjas utan att något särskilt medgivande eller avtal krävs.» «Fondinnehav … (.xml)» ist auf derselben Seite als offener Datenbestand aufgeführt. |
| Inhalt | Vollständige Quartalsbestände aller **schwedischen Wertpapierfonds (UCITS)**, ab 2018 Q4, zwei Monate Verzögerung; Spezialfonds nicht. Je Position: Name, ISIN, Emittentenland, Währung, Marktwert, Anteil am Fondsvermögen, Branche. Kein Emittenten-LEI. Nur die jeweils letzte gemeldete Version. |
| Automatisierter Abruf | nicht geregelt; `robots.txt` existiert nicht (HTTP 404). Eine ZIP-Datei je Quartal. |
| Speicherung / Bearbeitung | ja («fritt bearbetas») |
| Kommerzielle Nutzung | nicht wörtlich genannt; Weiterverwendung «ohne besondere Zustimmung oder Vertrag». **Offene Rechtsfrage:** keine benannte Standardlizenz (kein CC0/CC BY). |
| Anzeige / Weitergabe | ja («vidareutnyttjas»), **Pflicht: Quelle FI und Datum** |
| Geladen | `Fondinnehav_2026Q2` (6'693'565 Bytes, SHA-256 `e49b23b2…e614b1`), lokal unter `data/raw/external/fi_se_fondinnehav/2026Q2/` mit Nachweisdatei; Git-ignoriert |
| Gemessen | 726 Fonds, 122'248 Positionen, davon 117'412 mit ISIN (96 %) |
| Grenze | Schwedische Fonds sind nicht die Fonds, die Schweizer Privatanleger:innen typischerweise halten (D-020). Die Quelle beweist die Kette an echten UCITS-Daten, ersetzt aber keine Schweizer Fondsversorgung. Noch **nicht** im Update-System (`sources.toml`), nur Pilot-Skript. |

### Vergleich der Kombinationen

| Kombination | Abdeckung | Kosten | Einschränkungen | Offene Rechtsfragen |
|---|---|---|---|---|
| **A. FI-Positionen + Wikidata + GLEIF + amtliche Register** | 726 schwedische UCITS-Fonds, quartalsweise. Zuordnung im Pilotfonds: 90.7 % des Gewichts mit Wikidata-Treffer, 81.6 % mit genau einem LEI | 0 | keine Schweizer Fonds; Quellenangabe FI + Datum; Wikidata-Angaben unbestätigt | «kommerziell» bei FI nicht wörtlich genannt |
| **B. Nutzer-Upload der eigenen Positionsliste (CSV, D-015) + dieselbe Zuordnung/Belege** | jeder Fonds, zu dem die Nutzerin eine Liste hat | 0 | Nutzer:in muss die Liste selbst beschaffen; wir verteilen keine Anbieterdaten | dürfen Nutzer:innen Anbieterlisten hochladen (Anbieter-AGB)? Speicherdauer bei uns; Haftung/AGB |
| **C. SEC N-PORT + gemeldeter Emittenten-LEI** | alle US-registrierten Fonds, quartalsweise | 0 | nur US-Fonds (D-020/D-027); E-Mail im User-Agent | keine neuen; SEC erlaubt Weiterverbreitung ausdrücklich |
| **D. Jahres-/Halbjahresberichte CH/EU (manuell oder KI-Extraktion)** | theoretisch jeder Fonds, halbjährlich | 0 + viel Handarbeit | Swiss Fund Data verlangt für kommerzielle Nutzung die schriftliche Zustimmung von SIX; Bundesanzeiger beruft sich auf Datenbankschutz | Sind reine Positionsangaben geschützt? Nur mit Rechtsauskunft oder Anbietererlaubnis belastbar |
| **E. Kommerzielle API** | je Anbieter; UCITS-Abdeckung per ISIN nicht bestätigt | EODHD: 399 USD/Monat nur intern, 2'499 USD/Monat «Enterprise» | EODHD intern: keine Anzeige nach aussen; Finnhub: keine Weitergabe von Daten **oder abgeleiteten Ergebnissen**; SIX/FE fundinfo/Morningstar: Preis nur auf Anfrage | Anzeige abgeleiteter Ergebnisse braucht schriftliche Zusage; erfordert Anbieterkontakt (nur mit Auftrag) |
| **F. ESAP (EU-Zugangsportal)** | künftig UCITS-Berichte EU-weit | 0 | UCITS erst ab Januar 2028 | Wiederverwendungsbedingungen noch in technischen Standards |

Empfehlung (Entscheid Jonas offen): **A als Beweis der Kette jetzt, B als Produkteinstieg.**
A liefert echte, vollständige UCITS-Positionen mit klarer Freigabe und zeigt, dass Zuordnung
und Belegkette funktionieren. B löst das Schweizer Problem, ohne dass wir Anbieterdaten
verteilen: Die Nutzerin bringt die Liste, wir liefern Zuordnung und Belege aus offenen Quellen.
C bleibt der einfachste Weg zu vielen Fonds, falls US-Fonds doch akzeptiert werden.

### Einzelprüfungen dieser Recherche

| Quelle | Baustein | Befund | Nachweis |
|---|---|---|---|
| Swiss Fund Data (SIX) | Positionen/Berichte | Anlegerkategorie-Abfrage vor Inhalten; «Jegliche Vervielfältigung … oder Nutzung der Website oder ihres Inhalts für öffentliche oder kommerzielle Zwecke bedarf der vorherigen schriftlichen Zustimmung von SIX FI»; Rechte an Fondsdokumenten «verbleiben bei den jeweiligen Rechteinhabern». **Gesperrt.** | [Disclaimer](https://www.swissfunddata.ch/sfdpub/de/disclaimer) |
| Bundesanzeiger (DE) | Berichte deutscher Fonds | einzige Nutzeraussage: «Der Bundesanzeiger genießt Datenbankschutz nach §§ 87a ff. UrhG». Keine Aussage zu automatisiertem Abruf oder Weiterverwendung; Nutzungsbedingungen-Seite nicht ladbar. **Nicht freigegeben.** | [Impressum](https://www.bundesanzeiger.de/pub/de/impressum) |
| fundinfo | Berichte | Bedingungen nicht auffindbar (Seite 404). **Ungeprüft.** | – |
| CNMV (ES), CMVM (PT) | evtl. Positionen | Seiten verweigerten den automatischen Abruf (403) bzw. lieferten leeren Inhalt. **Ungeprüft**, weder bestätigt noch ausgeschlossen. | – |
| EODHD | Positionen (API) | Privatpläne: kein «displaying» oder «redistributing»; «internal-usage»: Anzeige ausserhalb der Firma nicht erlaubt; Enterprise mit «Data services agreement» | [Terms](https://eodhd.com/financial-apis/terms-conditions), [Commercial](https://eodhd.com/commercial-pricing) |
| Finnhub | Positionen (API) | gelistete Pläne nur persönlich; keine Weitergabe von Daten oder abgeleiteten Ergebnissen; Löschpflicht nach Abo-Ende | [Terms](https://finnhub.io/terms-of-service) |
| Financial Modeling Prep | Positionen (API) | Seiten nicht ladbar (403). **Ungeprüft.** | – |
| OpenFIGI | Zuordnung | FIGI-Kennungen: «for any purpose, commercial or non-commercial», inkl. Weitergabe an Kunden. Beschreibende Felder (Name, Ticker) sind in dieser Freigabe **nicht** genannt. 25 Anfragen/Minute ohne Schlüssel. Liefert keinen LEI. | [Terms](https://www.openfigi.com/docs/terms-of-service) |
| GLEIF/ANNA ISIN–LEI | Zuordnung | weiterhin keine ausdrückliche Lizenz für die Zuordnungsdateien; enthält nur neue ISINs teilnehmender Vergabestellen. **Bleibt ausgeschlossen (D-026).** | [Seite](https://www.gleif.org/en/lei-data/lei-mapping/download-isin-to-lei-relationship-files) |
| Wikidata, exakter ISIN-Abgleich | Zuordnung | CC0 (bereits freigegeben). Einmalige Messung für die 411 ISINs des Pilotfonds: 336 Treffer, 331 mit genau einem Eintrag, 285 mit genau einem LEI. Angaben unbestätigt. | [Licensing](https://www.wikidata.org/wiki/Wikidata:Licensing) |
| EEA Industrieemissionen (E-PRTR) | Beleg | Rechtshinweis erlaubt Weiterverwendung «for commercial or non-commercial purposes» mit Quellenangabe; Datensatzseite selbst nicht ladbar. **Kandidat, Datensatzlizenz noch prüfen.** | [Legal notice](https://www.eea.europa.eu/en/legal-notice) |
| EU-Finanzsanktionsliste | Beleg | Kommissionsinhalte allgemein CC BY 4.0; Lizenzfeld des Datensatzes nicht lesbar. **Kandidat, noch prüfen.** | [Legal notice](https://commission.europa.eu/legal-notice_en) |
| NBIM-Ausschlussliste | Beleg | keine Lizenzangabe auf der Seite; Unternehmen **nur mit Namen**, keine ISIN/LEI. Ohne sichere Kennung nicht zuordenbar (keine Namensfusion). | [Liste](https://www.nbim.no/en/responsible-investment/exclusion-of-companies/) |
| NBIM-Bestände (Snowflake) | Vergleich | nur über Snowflake-Konto; keine entgeltliche Weitergabe; nur Namen. **Nicht geeignet.** | [Terms](https://www.nbim.no/en/terms-of-use-holdings-data-in-snowflake-marketplace/) |
| Weltbank, gesperrte Firmen | Beleg | keine Nutzungsangabe auf der Seite; Name + Adresse, keine Kennung. **Ungeklärt.** | [Liste](https://www.worldbank.org/en/projects-operations/procurement/debarred-firms) |
| US EPA, EU-ETS-Register | Beleg | allgemeine Seiten ohne Aussage zum konkreten Datensatz. **Ungeprüft.** | – |

### Pilot am echten Fonds (lokal, nicht veröffentlicht)

`scripts/pilot_fund_chain.py`, ein schwedischer Aktienfonds (Quartalsende 30.06.2026,
Quelle FI). Auswahlregel: der Fonds mit Nachhaltigkeitsbezug im Namen, Schweizer Positionen
und den meisten Positionen. Name und Einzelergebnisse lokal unter `C:\TransparenzDaten\notizen\` dokumentiert, nicht veröffentlicht.

- 411 Positionen, alle mit gültiger ISIN (99.88 % des Fondsvermögens; Rest laut Meldung
  Liquidität/Sonstiges).
- Mit dem **lokalen Schweizer Bestand** (293 Wikidata-Kandidaten): 6 Positionen / 2.49 % mit
  Unternehmenshinweis; 405 Positionen / 97.39 % bleiben «unbekannt» (keine Zuordnungsquelle
  für Nicht-Schweizer ISINs im lokalen Bestand).
- **Eine vollständige Kette:** Aktie eines Schweizer Konzerns → Wikidata → GLEIF → von
  GLEIF vollständig bestätigte direkte Mutterbeziehung zu einer Schweizer Tochter → SwissPRTR:
  Meldezeilen 2007–2024 für deren Betriebs-UID. Amtlich gemeldete Jahreswerte, kein Nachweis
  eines Rechtsverstosses.
- GLEIF-Abfrage: 68 meldende Rechtsträger mit LEI, 53 gemeldete Mutterbeziehungen, davon 33
  aktiv/veröffentlicht/vollständig bestätigt. Nur diese übertragen einen Beleg (D-012).
- Lehre: Von den 232 lokalen Wertpapierkandidaten mit LEI melden nur zwei Rechtsträger selbst
  an SwissPRTR. Ohne bestätigte Konzernbeziehungen bleibt der Belegschritt fast leer.

**Nachtrag gleicher Tag: weltweiter ISIN-Abgleich fest eingebaut** (`--fetch-wikidata`, eine
SPARQL-Abfrage je 200 ISINs, exakter Abgleich über P946, LEI über P1278; Antwort wird lokal
gespeichert, danach läuft das Skript offline):

| Stufe | Positionen | Gewicht in % |
|---|---:|---:|
| mit Unternehmenshinweis | 336 | 90.71 |
| davon genau ein Wikidata-Eintrag und genau ein LEI, LEI bei GLEIF vorhanden | 285 | 81.56 |
| Eintrag ohne LEI | 41 | 6.10 |
| mehrdeutig (zwei Einträge oder zwei LEIs je ISIN), bewusst ohne Belegübertragung | 10 | 3.05 |
| ohne Wikidata-Treffer («unbekannt») | 75 | 9.17 |
| mit Beleg (SwissPRTR) | 1 | 0.71 |

- Gegenprobe GLEIF: alle 285 LEIs existieren; 249 mit Registrierung ISSUED, 36 LAPSED
  (Rechtsträger aktiv, LEI nicht erneuert) – im Bericht je Zeile ausgewiesen.
- Sichtprüfung Positionsname ↔ GLEIF-Rechtsname: Bei 50 der 285 gibt es kein gemeinsames
  Namenswort. Meist erklärbar (japanische Rechtsnamen in Originalschrift; Umbenennungen wie
  Anthem → Elevance Health, Square → Block, Deutsche Post → DHL). **Mindestens ein
  wahrscheinlicher Fehler:** Ein US-Finanzdienstleister führt über Wikidata zum LEI eines
  anderen Rechtsträgers derselben Gruppe. Wikidata-Zuordnungen bleiben
  deshalb unbestätigte Hinweise und brauchen vor einer Veröffentlichung eine Prüfung.
- Der Engpass liegt jetzt beim **Beleg**: Trotz 81.6 % Zuordnung bleibt es bei einer Position
  mit Beleg, weil SwissPRTR nur Schweizer Betriebe abdeckt.

## Rechercheergänzung 08.11.2026: weltweite Firmenstichprobe (D-035)

`COVERAGE_AUDIT_100.md` dokumentiert 100 Einzelprüfungen: 57 Firmenhinweise, 43 ohne Treffer.
Keine neue Quellenfreigabe und kein Produktionsimport. Börsen-/Index-/Emittentenseiten nur
zur Recherche verwendet; keine Kurse oder vollständigen Börsenverzeichnisse übernommen.

- Wikidata: strukturierte Daten CC0; globale börsenweise Kandidatenabfrage als Ausbauweg.
- [JPX-Verzeichnis](https://www.jpx.co.jp/english/markets/statistics-equities/misc/01.html):
  Excel technisch verfügbar; [Bedingungen](https://www.jpx.co.jp/english/term-of-use/) verlangen
  für kommerzielle Sammlung/Weiterverwendung Erlaubnis oder Vertrag. Keine Importfreigabe.
- [CVM cia_aberta-cad](https://dados.cvm.gov.br/dataset/cia_aberta-cad): tägliche Registerdaten,
  [konkrete CSV-Ressource](https://dados.cvm.gov.br/dataset/cia_aberta-cad/resource/2391143f-1423-48a5-9f6a-423245aca362)
  weist ODbL aus. Datenbankpflichten vor Integration konkret umsetzen; CNPJ/Registrierung
  ersetzt keine aktuelle Instrument-/Listingliste. Noch nicht importiert.
- B3-Portalbedingungen erlauben keine pauschale kommerzielle Nutzung ohne schriftliche
  Zustimmung. Kein B3-Massenimport. [Offizielle Bedingungen](https://www.b3.com.br/main.jsp?doui_processActionId=setLocaleProcessAction&locale=en_US&lumA=1&lumII=8AE690F77A1A49BA017A5CE182412193&lumPageId=8AE690F77A1A49BA017A5CDEBBCF67BD).
- ESMA-/FCA-FIRDS, HKEX, NSE/BSE, ASX und JSE: Beschaffungskandidaten mit konkreter
  Datei-/Rechteprüfung weiterhin offen; öffentliche Ansicht bedeutet keine Datenfreigabe.

Bisheriges Quellenregister folgt:

**Stand 08.11.2026.** Die Demooberfläche und der lokale Schweizer Rohdatenkatalog sind
getrennt. `sources.toml` bleibt Demo + deaktivierte LEI-Abfrageliste; produktive lokale
Registerimporte stehen in `swiss_sources.toml`. Grundsatz: nur nachgewiesene kommerzielle
Rechte; öffentliche Abrufbarkeit genügt nicht. Der neue Auftrag erlaubt diese lokalen
kostenlosen Downloads ausdrücklich. Frühere Einzelrückfragen sind dafür aufgehoben.
Der weltweite Aktien-/ETF-Auftrag startet zusätzlich separat mit `market_sources.toml`.

## Aktien-/Fonds-Katalog: SEC-Freigaben (08.11.2026)

| Quelle | Verarbeitung kommerziell | Speichern | Ableiten | Weitergeben | Tatsächlicher Import |
|---|---|---|---|---|---|
| `sec_exchange_tickers` | ja | ja | ja | ja | 10'419 Ticker/CIK/Börsen-Zuordnungen, Instrumenttyp offen |
| `sec_fund_classes` | ja | ja | ja | ja | 28'647 Serien-/Klassen-/Ticker-Zuordnungen, nicht ausschliesslich ETFs |
| `sec_ncen` | ja | ja | ja | ja | 45'456 Fonds-/Klassenbeobachtungen, Quartale 2025Q4–2026Q3 |

Grundlage: [SEC Website Dissemination](https://www.sec.gov/about/privacy-information),
öffentliche Informationen dürfen kopiert und weiterverteilt werden. Quellenangabe wird
erbeten und hier mitgeführt; keine Billigung durch die SEC, keine Übernahme ihrer Marken.
Kein CC0-Schild und keine pauschale Freigabe von Drittanbieter-Websites. Eigene Auswahl und
Normalisierung der öffentlichen Register-/Meldedaten unter dieser Freigabe; Rechtefelder sind
die dokumentierte Quellenprüfung, keine individuelle juristische Zusicherung.

Die [offizielle EDGAR-Zugangsdokumentation](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)
benennt beide Tickerdateien und warnt vor ungesicherter Genauigkeit/Abdeckung. 1.1 Sekunden
Mindestabstand pro Anfrage; Kontakt im User-Agent ausschliesslich aus lokalem
`TRANSPARENZ_SEC_CONTACT`, vom Nutzer ausdrücklich bereitgestellt. Keine Adresse in Git
oder Daten-Sidecars. HTTP 403 bleibt ein Fehler, keine Sperrumgehung.

[N-CEN-Datenseite und Quartalsarchive](https://www.sec.gov/data-research/sec-markets-data/form-n-cen-data-sets)
und [Readme](https://www.sec.gov/file/ncen_readme): Jahresmeldungen, as-filed, Berichtigungen
möglich; laut SEC fehlen Meldungen nach Schema 3.1 im Bulkbestand. `IS_ETF` gilt für die
Fondsserie; nur bei genau einer gemeldeten Klasse wird diese einzelne Klasse historisch als
ETF belegt. Mehrklassenserien offen. Keine Aussage heutiger Handelbarkeit oder Weltabdeckung.
Originale mit Hash-/Lizenzmetadaten lokal archiviert; sieben Dateien im Offline-Audit geprüft.
Bestand und Bedienung: [GLOBAL_MARKET_CATALOG.md](GLOBAL_MARKET_CATALOG.md).

Weitere geprüfte Kandidaten, **keine produktiven Imports**:

| Kandidat | Ergebnis | Offizielle Grundlage |
|---|---|---|
| NasdaqTrader Symbol Directory | persönliche, nicht kommerzielle Verwendung ohne separate Erlaubnis; keine kommerzielle Importfreigabe | [Copyright](https://nasdaqtrader.com/Trader.aspx?id=CopyDisclaimMain) |
| TickerInside identifiers / Holdings | CC BY für eigene Beiträge ist keine Freigabe der Upstream-Daten; NasdaqTrader als Börsenquelle, deshalb kein pauschaler Katalogimport | [Legal](https://tickerinside.com/legal/), [API-Herkunft](https://tickerinside.com/api/) |
| ESMA FIRDS | konkrete Freigabe der Venue-/Drittanbieter-Instrumentdaten noch offen; allgemeine Website-/Library-Erlaubnis nicht pauschal übertragen | [ESMA Legal Notice](https://www.esma.europa.eu/about-esma/legal-notice-and-data-protection) |
| FCA FIRDS | OGL gilt nur für konkrete FCA-eigene numerische Daten; andere und Drittanbieter-Daten nicht pauschal frei | [FCA Legal](https://www.fca.org.uk/legal) |
| OpenFIGI | FIGI-Identifier selbst offen; keine verifizierte Vollfreigabe eines weltweiten Beschreibungs-/Stammdatenbestands | [Terms](https://www.openfigi.com/docs/terms-of-service) |
| CVM Brasilien Fondsregister | Datensatz nennt ODbL; Share-Alike, passende Fonds-/Klassenfelder und fehlender Listing-Nachweis vor Import klären | [amtlicher Datensatz](https://dados.cvm.gov.br/dataset/fi-cad) |
| FSMA Belgien | eigene Website-Informationen CC BY 4.0, Attribution und Auflagen bei Weiterverkauf; passende Instrumentdatei noch nicht ausgewählt | [FSMA Copyright](https://www.fsma.be/en/disclaimer-copyright) |

## Schweizer Fundament: aktuelle Freigaben (geprüft 08.11.2026)

| Quelle | Interne kommerzielle Verarbeitung | Speicherung | Ableitungen | Redistribution | Quellenangabe | Tatsächlicher Stand |
|---|---|---|---|---|---|---|
| `gleif_ch` – LEI-Referenzdaten CC0 | ja | ja | ja | ja | freiwillig; keine Billigung suggerieren | CH-Filter vollständig abgerufen; 25'121 Rechtsträger, 3'254 Fondsrechtsträger; 118 Statusausschlüsse, 2 ungültige LEIs separat |
| `zefix_lindas` – terms_open | ja | ja | ja | ja | empfohlen; wird mitgeführt | 796'684 gültige Registereinheiten; Mehrsprachigkeit als Namensvarianten; Konflikte/ungültige UID separat |
| `wikidata_ch` – strukturierte Daten CC0 | ja | ja | ja | ja | freiwillig | **D-034: 287 Datensätze, 293 Wertpapierkandidaten** (u. a. Roche, Nestlé, Novartis, UBS, ABB); läuft im Standardlauf mit |
| `swissprtr` – terms_by | ja | ja | ja | ja | **BAFU, Datensatztitel und Link verpflichtend** | 247 Standorte; 22'860 Emissionszeilen 2007–2024 normalisiert (D-032) |

Offizielle Nachweise und Geltungsbereiche:

- **GLEIF:** [LEI Data Terms of Use](https://www.gleif.org/en/meta/lei-data-terms-of-use),
  [CC0](https://creativecommons.org/publicdomain/zero/1.0/).
  Freigabe betrifft Level-1-/Level-2-Referenzdaten; **keine** pauschale Freigabe des ANNA-Mappings.
  Die API verlangt für mehr als 10'000 Ergebnisse Cursor-Paginierung (`page[cursor]=*`).
  Der Import prüft Golden-Copy-Zeitpunkt, Gesamtzahl und eindeutige LEIs über alle Seiten.
- **Zefix:** [offizielle Linked-Data-Ressource](https://opendata.swiss/de/dataset/zefix-zentraler-firmenindex/resource/ba772d7c-171b-47bf-b958-ee87419090d6),
  [CKAN-Originalmetadaten](https://ckan.opendata.swiss/api/3/action/package_show?id=zefix-zentraler-firmenindex),
  [terms_open](https://opendata.swiss/terms-of-use#terms_open).
  Wichtig: Dataset-Level `license_id=null` bedeutet hier keine fehlende Ressourcenfreigabe.
  `rights` und `license` der Ressource nennen terms_open; die separate Metadatenressource
  nennt terms_by. [Offizielles Nutzungsmodell](https://opendata.swiss/en/terms-of-use)
  erlaubt kommerzielle Nutzung. Speicherung, Bearbeitung und Weitergabe werden als von der
  offenen Nutzung umfasst eingeordnet, ohne zusätzliche Beschränkung in der Ressource.
  Kontrollzählung derselben Abfrage: 796'690 Rechtseinheiten; sechs zurückgehaltene
  Originaleinheiten erklären die Differenz zu 796'684. Kein atomarer Extraktionszeitpunkt,
  kein Vollständigkeitsnachweis für sämtliche Schweizer Unternehmen oder Börsenkotierungen.
- **Wikidata:** [Licensing](https://www.wikidata.org/wiki/Wikidata:Licensing),
  [Datenzugriff](https://www.wikidata.org/wiki/Wikidata:Data_access),
  [CC0](https://creativecommons.org/publicdomain/zero/1.0/).
  Nur strukturierte Statements; keine Wikipedia-Artikel oder sonstige lizenzierte Texte.
  **D-034 (08.11.2026):** Der frühere HTTP 403 war grösstenteils selbstverschuldet (falsche
  Wikidata-IDs in der Abfrage, zu teure Transitivsuche, generischer User-Agent ohne
  Kontaktangabe – verletzt die [Wikimedia-User-Agent-Policy](https://meta.wikimedia.org/wiki/User-Agent_policy)).
  Abfrage auf SIX-Notierung (korrekte ID Q661834) bzw. CH-Sitz mit ISIN eingegrenzt; Antwortzeit
  seitdem 1–3 s. Ein echter, nicht selbstverschuldeter HTTP 403/429 bliebe weiterhin ein harter
  Fehler, keine Umgehung. 287 Datensätze, 293 ISIN-Kandidaten aktiv; Fonds-/ETF-Teilabfrage im
  Schweizer/SIX-Zuschnitt 0 Treffer (weltweit 19 instance-of ETF/Investmentfonds mit ISIN).
- **SwissPRTR:** [offizieller Datensatz](https://opendata.swiss/en/dataset/schadstofffreisetzungs-und-transferregister-der-schweiz-swissprtr),
  [CKAN-Originalmetadaten](https://ckan.opendata.swiss/api/3/action/package_show?id=schadstofffreisetzungs-und-transferregister-der-schweiz-swissprtr),
  [terms_by](https://opendata.swiss/terms-of-use#terms_by),
  [BAFU-Datenpublikation](https://www.bafu.admin.ch/de/swissprtr).
  Standort-GeoPackage wird über STAC entdeckt und gegen die amtliche SHA-256 geprüft.
  Die Datenpublikation verlinkt das 3'106'306-Byte-XLSX mit Emissionen bis 2024;
  2025 wird laut BAFU spätestens Ende März 2027 erwartet. Diese Emissionen sind derzeit
  **nur archiviert**, nicht im Screening. Standortdaten enthalten keine sichere Betreiber-UID;
  keine Firmenzuordnung allein nach dem Betriebsnamen, keine Zurechnung zu Mutterkonzernen.

Das Register speichert fünf Rechte getrennt. Bei OGD sind Speicherung/Ableitung/Weitergabe
eine dokumentierte Auslegung der offenen Nutzung, keine individuell erteilte Rechtsauskunft.
Originaldateien samt Metadaten: `data/raw/external/<quelle>/objects/` (Git-ignoriert).
Jede Sidecar-Datei hält offizielle URLs, Rechte, Prüfdatum, Abrufzeit, Format, Grösse und Hash
fest. Ein unbekannter Datenstichtag wird ausdrücklich nicht durch das Downloaddatum ersetzt.

## Gesperrte oder noch nicht freigegebene Kandidaten

Maschinenlesbar: `src/transparenz/config/source_reviews.json`, geprüft am 08.11.2026.
Diese Einträge besitzen **keinen produktiven Downloadadapter**.

| Quelle | Status/Grund | Offizieller Nachweis |
|---|---|---|
| SIX-Aktien-/ETF-Listen und kommerzielle Referenzdaten | keine kommerzielle Website-Wiederverwendung freigegeben; Datenvertrag erforderlich | [SIX Terms of use](https://www.six-group.com/en/services/legal/terms-and-conditions/terms-of-use.html) |
| GLEIF/ANNA ISIN–LEI | separate Rechte ungeklärt, D-026 bleibt bestehen | [Mapping-Seite](https://www.gleif.org/en/lei-data/lei-mapping/download-isin-to-lei-relationship-files) |
| Anbieter-Fondspositionen | keine konkrete vollständige CH-/UCITS-Datei mit allen Rechten verifiziert | je Anbieter und Datei zu prüfen |
| OpenSanctions | kommerzielle Datenlizenz erforderlich, keine beauftragt | [offizielle Downloadbedingungen](https://www.opensanctions.org/docs/bulk/updates/) |
| SECO XML | offizieller maschinenlesbarer Bestand gefunden; alle fünf Nutzungsrechte noch nicht belegt; fachliche Einordnung offen | [SECO-Datenseite](https://www.seco.admin.ch/de/suche-nach-sanktionsadressaten) |
| Climate TRACE | CC BY 4.0 mit expliziten Ausnahmen für Drittquellen/Eigentümerdaten; Schweizer Teilbestand nicht separat geklärt | [Terms](https://climatetrace.org/terms) |
| BHRRC, SVVK, Urgewald und weitere Firmenvorwürfe | kein konkreter Datensatz mit vollständiger Prüfung und sicherem Firmenmapping freigegeben | noch nicht abschliessend geprüft |

**Lücken:** derzeit 0 bestätigte Wertpapiere, 0 ETF-Anteilsklassen mit ISIN, 0 Fondspositionen.
Ein GLEIF-Fondsrechtsträger darf nicht als börsengehandelter ETF gezählt werden. Schweizer Sitz,
SIX-Kotierung, einzelne Aktien, Fondsmantel, Anteilsklasse und Position sind getrennte Begriffe.
Kein aktuelles Universum zur Messung der Aktien-/ETF-Abdeckung freigegeben. Quellen ohne Belege
für Unternehmensabdeckung erlauben keine Aussage «keine Hinweise». Länder-/Branchenrisiken
(z. B. DOL ILAB) sind keine Unternehmensvorwürfe. Sanktionslistungen sind keine Gerichtsurteile.

## Frühere Recherche vom 07.11.2026

Die folgenden Einzelprüfungen bleiben als Vorarbeit erhalten. Aussagen «deaktiviert» betreffen
den alten Demokatalog; neue lokale Schweizer Freigaben und der Auftrag oben haben Vorrang.

Statuswerte: **aktiv** · **angebunden (deaktiviert)** · **geprüft, geeignet** ·
**zu prüfen** (Lizenz/Zugang unklar) · **ausgeschlossen**

## Lizenzregister und automatische Sperre

Jede Quelle in `sources.toml` und `swiss_sources.toml` trägt ihre Lizenzangaben selbst
(`license`, `license_url`, `terms_url`, `license_checked_on`, `commercial_use`,
`storage`, `derivatives`, `redistribution`, `attribution`). Eine **echte** Quelle wird gesperrt (kein
Abruf, auch kein Trockenlauf, Status «gesperrt» im Update-Protokoll), wenn

- kommerzielle Verarbeitung, Speicherung, Ableitung oder Weiterveröffentlichung nicht «ja» ist,
- Nutzungsbedingungen (`terms_url`), offizielle Lizenz-URL oder Lizenzbezeichnung fehlen,
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

### GLEIF – Golden Copy Level 1 (alle LEI-Datensätze) · Ergebnis: **lokal integriert als Prüfquelle (D-055)**

| | |
|---|---|
| Original-URL | https://goldencopy.gleif.org/api/v2/golden-copies/publishes/latest (Metadaten, Datei-Link) ; Bedingungen: https://www.gleif.org/en/meta/lei-data-terms-of-use |
| Lizenz | **CC0 1.0** (wie die bereits genutzte Level-2-Datei; Bedingungen am 08.11.2026 gelesen) |
| Lokaler Stand | `raw/external/gleif_lei2_golden_copy/2026-11-15/gleif-goldencopy-lei2.csv.zip`, 509'687'964 Bytes, SHA-256 `7e8158b9…7f03`, Stand 15.11.2026 16:00, Format LEI_3.1, 3'494'789 Datensätze, abgerufen 16.11.2026 (Zustimmung Jonas). Entpackt 5.1 GB, 338 Spalten. |
| Verwendung | Prüfung gemeldeter LEI (vorhanden, `Entity.EntityStatus`, `Registration.RegistrationStatus`); später Grundlage des Wertpapierstamms. Keine Abfrage der ISIN-Zuordnung von GLEIF/ANNA (Lizenz ungeklärt, siehe oben). |

### SEC – Form N-PORT Data Sets · Ergebnis: **integriert (lokal, D-054); Messung Phase 1**

| | |
|---|---|
| Original-URL | https://www.sec.gov/data-research/sec-markets-data/form-n-port-data-sets ; Bedingungen: https://www.sec.gov/privacy (Abschnitt «Website Dissemination») |
| Lizenz | keine Lizenz im Sinne von CC; **öffentliche Information**: «Information presented on sec.gov is considered public information and may be copied or further distributed by users of the web site without the SEC's permission.» |
| Kommerziell / Weiterveröffentlichung | Weiterverbreitung ausdrücklich ohne Erlaubnis zulässig; kommerzielle Nutzung wird **nicht erwähnt** (weder erlaubt noch verboten). Einordnung: «klar dokumentierte öffentliche Datenfreigabe». |
| Quellenangabe | erbeten, nicht verlangt: «Please consider appropriate citation to the SEC as the source.» |
| Auflagen | SEC-/EDGAR-Marken nicht in Firmen-/Domainnamen; Disclaimer der Datensätze: Daten stammen von den Fonds selbst («we cannot guarantee the accuracy of the data»), «not a substitute for such filings». Die Readme nennt die Daten «as-filed». |
| Technik | Fair Access: höchstens **10 Anfragen pro Sekunde**; User-Agent mit Firmenname **und E-Mail-Adresse** verlangt (welche Adresse, entscheidet Jonas). Neuester Datensatz: **2026q3_nport.zip, 440.95 MB**; 2026q2: 420.28 MB; 2026q1: 441.62 MB. Quartalsweise veröffentlicht. |
| Inhalt | nur **in den USA registrierte** Fonds (inkl. ETFs, ohne Geldmarktfonds). Je Position u. a. `ISSUER_NAME`, `ISSUER_LEI` («LEI (if any) of issuer»), `IDENTIFIER_ISIN`. Die Fonds melden die Zuordnung Wertpapier → Emittent damit selbst. |
| Öffentliche Monatsmeldungen | Readme (im ZIP, `nport_readme.htm`): «monthly portfolio holdings», «disseminated quarterly»; welche Monate, steht dort nicht. **Gemessen am Archiv 2026q3 (15.11.2026):** Bei allen 14'066 Meldungen liegt der Stichtag in einem Quartalsendmonat des gemeldeten Geschäftsjahrs, also nur der dritte Monat je Geschäftsquartal. Eingereicht Juli–September 2026, Stichtage überwiegend Mai–Juli 2026 (Median 57 Tage zwischen Stichtag und Einreichung). Der Stichtag ist je Fonds verschieden; massgebend ist `REPORT_DATE` der Meldung. |
| Lokaler Stand | `raw/external/sec_nport/2026q3/2026q3_nport.zip`, 462'371'568 Bytes, SHA-256 `2f5ee059…6c38`, abgerufen 15.11.2026 (Zustimmung Jonas), HTTP Last-Modified 07.10.2026. Archiv enthält Readme und Metadaten (W3C Tabular Data). Eingelesen mit `nport-update` in `processed/nport.sqlite`; Messwerte in `processed/nport/quality_report.json` und STATUS.md. |
| Prüfdatum | 07.11.2026 |
| Verwendung | Roadmap: Phase 1 Import und Messung, Phase 2 Wertpapierstamm ISIN → LEI aus dem Konsens mehrerer Meldender. Nur US-registrierte Fonds; die Frage nach Fonds für Schweizer Privatanleger:innen (D-020) bleibt davon getrennt. Weitere Quartale nur mit `nport-download <Quartal> --confirm` nach Zustimmung. |

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

### Raiffeisen Futura – Fonds-Factsheet (PDF) · Ergebnis: **ausgeschlossen (keine Weiterverbreitung ohne Genehmigung; ausserdem keine Vermögensaufstellung)**

- Geprüftes Dokument: `GlobalStock-d.pdf` («Raiffeisen Futura – Global Stock A», Stand
  30.09.2026), direkt von raiffeisen.ch geladen (öffentlich, ohne Anlegerfreigabe-Gate).
- **Explizites Weiterverbreitungsverbot** im Abschnitt «Rechtliche Hinweise»: «Das vorliegende
  Dokument darf ohne schriftliche Genehmigung von Raiffeisen weder auszugsweise noch
  vollständig vervielfältigt und/oder weitergegeben werden.»
- Zusätzlich eigene Urheberrechtsklausel für die ESG-Daten (Inrate AG, FE fundinfo):
  «Sowohl die teilweise als auch gesamthafte Reproduktion oder Vervielfältigung in jeglicher
  Form ist ohne vorherige schriftliche Genehmigung der betreffenden ESG-Partei untersagt.»
  Dazu eine separate MSCI-Klausel: «MSCI Daten sind ausschliesslich für den internen Gebrauch
  bestimmt und dürfen weder weiterverteilt noch … gebraucht werden.»
- **Fachlich zusätzlich ungeeignet:** Das Factsheet nennt nur die **10 grössten Aktienpositionen**
  (Gewicht in %), keine vollständige Vermögensaufstellung. Die rechtlich massgebliche
  Vermögensaufstellung steht laut demselben Dokument nur im **Jahres-/Halbjahresbericht**
  («kostenlos bei der Raiffeisen Schweiz Genossenschaft … oder unter raiffeisen.ch/fonds»);
  dessen eigene Lizenzbedingungen wurden hier **nicht** geprüft, dürften aber nicht großzügiger
  ausfallen als das Factsheet.
- **Übertragbarkeit:** UBS ETF konnte nicht gleichwertig geprüft werden – der Zugang ist dort
  zusätzlich hinter ein Anlegerprofil-/Domizil-Gate gelegt (nicht durchlaufen, siehe unten).
  Das stützt eher eine noch restriktivere Haltung als eine offenere.
- Prüfdatum: 11.11.2026

### UBS ETF – Fondsseiten · Ergebnis: **nicht abschliessend geprüft (Zugriffsgate)**

- `ubs.com/ch/de/assetmanagement/funds/etf...` verlangt vor Inhalten eine explizite Bestätigung
  von Domizil **und** Anlegerrolle («Qualifizierter Anleger» o. Ä.) – dieser Schritt wurde
  bewusst **nicht** durchklickt (keine Anleger-Selbstdeklaration durch ein Werkzeug).
  Lizenzfrage bleibt offen, bis Jonas das manuell prüft oder eine andere Fundstelle vorliegt.
- Prüfdatum: 11.11.2026

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
- Kostenlose lokale Downloads freigegebener Quellen sind durch den Auftrag 08.11.2026 erlaubt.
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
