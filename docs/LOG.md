# Sessionlog

Neueste Einträge oben.

## 16.11.2026 – Claude (Opus 5.5): gemeldete LEI gegen GLEIF prüfen (D-055)

- Auftrag Jonas: «Ja, GLEIF laden».
- **Download:** GLEIF-Metadaten erneut gelesen (unverändert: Stand 15.11.2026 16:00,
  486.08 MB), dann `gleif-goldencopy-lei2.csv.zip` geladen (509'687'964 Bytes, 43 s),
  Archiv geprüft, Begleitdatei mit SHA-256 geschrieben.
- **Neu:** `ingestion/gleif_level1.py` (Herkunftsprüfung, nur gesuchte LEI, doppelte LEI =
  Fehler); im N-PORT-Bericht Abschnitt `gleif_check` (je LEI und gewichtet nach Positionen,
  Zwischenspeicher je Paar aus GLEIF-Datei und N-PORT-Stand). Berichtschema 2.
- **Ergebnis (28'586 Emittenten-LEI im gültigen Stand):** vorhanden 99.97 % (10 fehlen),
  aktiv 98.66 %, inaktiv 316, Duplikat/annulliert 57; gepflegt 72.41 %, überfällig 26.24 %.
  Gewichtet nach Positionen: aktiv 99.58 %, aktiv und gepflegt 80.69 %. Serien-LEI der
  Fonds: 13'821, alle vorhanden, aktiv 99.35 %. Laufzeit 249 s.
- **Geprüft:** pytest 364 bestanden (3 neu, fiktiv), Ruff sauber. Pilot und Website nicht
  betroffen.
- Skills: keine verwendet. Werkzeuge: Shell (Git Bash, PowerShell), Dateiwerkzeuge,
  Hintergrundläufe mit Überwachung, curl (GLEIF-Metadaten und Download). Kein Push.

## 15.11.2026 – Claude (Opus 5.5): Phase 1 – SEC N-PORT importieren (D-054)

- Auftrag Jonas: «Ich stimme dem N-PORT-Download zu, starte Phase 1.»
- **Download:** SEC-Übersichtsseite gelesen (2026q3, 440.95 MB bestätigt), dann
  `2026q3_nport.zip` geladen (462'371'568 Bytes, 54 s, Kontakt nur im User-Agent).
  Alle 32 Archiveinträge geprüft; Begleitdatei mit SHA-256 geschrieben. Readme und Metadaten
  liegen im ZIP, kein weiterer Download nötig.
- **Neu:** `entities/nport.py` (Pydantic je Zeile), `ingestion/sec_nport.py` (direkt aus dem
  ZIP, Herkunftsprüfung, zwei Durchgänge prüfen/schreiben, Ablehnung je Grund, Auswahl je
  Fonds und Stichtag, `nport-download` mit `--confirm`), vier Tabellen in `nport.sqlite`,
  `services/nport_catalog.py` (Qualitätsbericht per SQL), Befehle `nport-download` und
  `nport-update`, `config/nport_sources.toml`. Lizenzsperre gilt wie bei den SEC-Quellen.
- **Erster Lauf (Regel «ohne Serie kein Fonds»):** erfolgreich, 0 abgelehnte Zeilen, aber
  21 % der Positionen (737 Meldungen ohne Serien-ID von 709 Registranten) fielen aus der
  Auswahl. Geprüft: Keiner dieser Registranten meldet auch mit Serie, alle haben eine CIK.
  Regel geändert (Registrant = Fonds, wenn er nie mit Serie meldet), Regelversion ins
  Manifest, neu gerechnet (Datenstand 2). Danach unentschieden: 7 Meldungen von 2
  Registranten ohne Serie, am selben Tag mit gleichem Nettovermögen (wohl Doppelmeldungen),
  bleiben bewusst ohne Wahl.
- **Messwerte (Datenstand 2):** siehe STATUS.md. Kernzahlen: 13'908 Fonds, 4'626'854
  Positionen im gültigen Stand, ISIN gültig 90.18 %, Emittenten-LEI gültig 72.79 %, beides
  68.29 %; bei Aktien 80.68 %. 399'511 verschiedene ISIN, 28'586 verschiedene LEI.
  Öffentlich ist laut Messung nur der dritte Monat je Geschäftsquartal (100 % der Meldungen).
  `PERCENTAGE` ist in Prozent (Median der Summe je Meldung 100.00 %).
- **Nebenbefund:** Die gemeinsame Sperre meldete bei N-PORT «Schweizer Import läuft»; Text
  allgemein formuliert. Ein zweiter Lauf ohne `--force` wurde korrekt als «noch nicht fällig»
  übersprungen und protokolliert.
- **Nicht gemessen:** «LEI aktiv bei GLEIF» – braucht die GLEIF-Liste Level 1 (486.08 MB,
  Zustimmung offen). Pilot-Vergleichslauf nicht ausgeführt, weil die Fondskette nicht
  verändert wurde. Website nicht neu erzeugt (keine Daten- oder Darstellungsänderung).
- **Geprüft:** pytest 361 bestanden (16 neu, alle fiktiv: ZZ-ISIN, FIKT00-LEI), Ruff sauber.
- Skills: keine verwendet. Werkzeuge: Shell (Git Bash, PowerShell), Dateiwerkzeuge,
  Hintergrundläufe mit Überwachung, curl (SEC-Seite, Download, GLEIF-Metadaten). Keine
  Unteragenten. Kein Push.

## 15.11.2026 – Claude (Opus 5.5): Phase 0 – Fundament für den weltweiten Bestand

- Auftrag Jonas: kein Einzelfallentscheiden mehr; «alle Aktien, alle Fonds weltweit» erfassen
  und zuordnen; «wirklich korrekt und richtig», damit daraus eine Firma werden kann. Plan in
  fünf Phasen vorgelegt und als `docs/ROADMAP.md` festgehalten; Jonas: «Ja, Phase 0».
- **Git:** vier Commits von GitHub (KI-Transparenz, Analytics-Client) mit dem lokalen Stand
  zusammengeführt; Konflikte in STATUS, LOG und `analytics-client.js` von Hand gelöst
  (Opt-out beibehalten, neue Zählung übernommen); doppelte Nummer D-035 → D-035b. `main`
  vorgespult. Nicht gepusht.
- **Speicher (Entscheid Jonas):** 14 alte Schweizer Exportstände gelöscht (neueste zwei
  behalten, rund 6 GB). Grosse Daten nach `C:\TransparenzDaten` verschoben
  (`TRANSPARENZ_DATA_DIR`, D-050); alle aktiven Datenstände gefunden, Schweizer und
  SEC-Prüfung bestanden, Suche (Roche, Apple) funktioniert.
- **Vorfall und Behebung:** Ein bestehender Test schrieb nach der Umstellung in den echten
  Wikidata-Ordner und überschrieb `current.json` mit einem fiktiven Datensatz. Aus der
  Begleitdatei wiederhergestellt (15'624 Zeilen, Prüfsumme bestätigt), Testobjekt entfernt.
  Neu: Sicherheitsnetz in `conftest.py`, das jeden Test in einen Wegwerf-Datenordner lenkt.
- **Pilot zerlegt (D-051):** 142 Definitionen maschinell und unverändert in neun Module
  verschoben (Abhängigkeitsprüfung ohne Kreise); Skript 305 statt 2'700 Zeilen.
  Vergleichslauf (`scripts/pilot_regression.py`): zweimal vorher 45/45 Dateien gleich
  (deterministisch), vorher gegen nachher 45/45 gleich.
- **Herkunft (D-052):** `services/provenance.py`; jede Eingabedatei wird bei jedem Lauf gegen
  ihre Begleitdatei geprüft (Abbruch bei Abweichung). Alle vier Rohquellen bestätigt, drei
  GEM-Dateien über das geprüfte Archiv. Bericht mit Abschnitt «Herkunft der Eingabedateien».
  Vergleich: ohne den neuen Abschnitt alle 33 JSON-Dateien unverändert.
- **Geprüft:** pytest 345 bestanden, Ruff sauber; Bericht im Browser der App auf 1024 und
  375 px (keine Seitenbreite über dem Fenster, Tabelle scrollt im Rahmen).
- Skills: keine verwendet. Werkzeuge: Shell (Git Bash, PowerShell), Dateiwerkzeuge,
  Rückfrage an Jonas, Hintergrundläufe mit Überwachung, Browser der App. Keine Unteragenten.
- **Vor dem Push bereinigt (Entscheid Jonas, D-053):** Die 18 lokalen Commits enthielten in
  STATUS, LOG, DECISIONS und DATA_SOURCES echte Pilotergebnisse mit Fonds- und Firmennamen.
  Vollständige Fassungen lokal gesichert (`C:\TransparenzDaten\notizen\`), öffentliche
  Fassungen ohne Namen und ohne Konfliktzahlen je Fonds; Kontrolle mit erweiterter Namensliste
  über alle versionierten Dateien. Die Commits seit dem GitHub-Stand zu einem Commit
  zusammengefasst, damit die Namen nie auf GitHub lagen.
- **Website:** fiktive Demodaten neu eingelesen (unverändert), Seite neu erzeugt (Methodik
  mit Kategorien, Beziehungstypen, Wirkungsdauer). Die Beispielquelle zeigt korrekt
  «veraltet» (Stichtag der Beispieldaten 46 Tage alt, erlaubt 45).
- Offen: N-PORT-Download (Zustimmung), Ordner `analytics-dashboard-update/`.

## 14.11.2026 – Claude (Opus 5.5): weitere Testfonds für die Namenssuche

- Auftrag Jonas: «Ja, weitere Fonds» (Freigabe der Namenssuche nachweisen oder verwerfen).
- Messregel vorher ergänzt und getestet: dieselbe ISIN zählt in Testfonds nur einmal.
- Gerechnet ohne Regeländerung (Version 2026-11-14.3): drei weitere schwedische Testfonds
  (Schwellenländer, Asien, Nordeuropa; 432, 408 und 567 Positionen; ein Versuch brach an einem
  Wikidata-Fehler 502 ab und wurde wiederholt). Abrufe nur GLEIF und Wikidata.
- **Ergebnis:** unabhängig 196 von 201 richtig (97.5 %), untere Grenze 94.8 % → nicht
  freigegeben. Einzeln geprüft: In drei Fällen nennt Wikidata den LEI einer Tochter bzw. der
  alten Gesellschaft, die Namenssuche liegt richtig; zwei Fälle unklar. Registernummer
  unabhängig 102 von 103.
- **Neu:** `mapping_disputes.json` mit allen acht Abweichungen (Entwicklungs- und Testfonds,
  Name und Registernummer), je mit beiden Kandidaten; beantwortbar mit
  `review_mapping.py --queue …`. Die Antworten werden Referenzfälle. Unsere eigene
  Einschätzung zählt nie als Referenz.
- Abdeckung der neuen Fonds tief (44–53 % Fondsgewicht): Wikidata kennt für viele nordische,
  asiatische und Schwellenländer-Titel keinen LEI; 165–257 Namensvorschläge je Fonds warten auf
  die Freigabe.
- Alle sechs Fonds auf gemeinsamen Stand gerechnet. Tests: 2 neue, **329 bestanden**, Ruff
  sauber. Kein Push.

## 14.11.2026 – Claude (Fable 5.2, ab Mitte Opus 5.5): Beziehungstypen, automatische Zuordnung, Kategorien (D-045–D-048)

- Auftrag Jonas (fünf Punkte): Eigentums- und Beteiligungslogik prüfen (Belegketten für
  einen Vermögensverwalter, eine Bank, einen Technologiekonzern); Automatisierung ohne Einzelfallfreigabe mit
  gemessener Präzision, 116 Positionen ohne Unternehmen bearbeiten; Quellenlage je Quelle in
  Stufen; Unterkategorien technisch auswerten, Umsetzungsstand je Kriterium, Korruptionsdauer
  begründen; Differenz zwischen beteiligten Positionen und Konflikten erklären; Pilotbericht
  und zweiter Fonds.
- **Erklärung der alten Differenz** (Regel «jede bestätigte Beteiligung», Profil 1.0): Die
  beteiligten Positionen ohne Konflikt hatten nur Ketten mit unbekanntem Anteil. Fehlender
  Beleg jeweils: die Beteiligungsquote bei GEM.
- **Beziehungstypen** (services/ownership.py, criteria.toml `relationship_type`): Verwahrung,
  Vermögensverwaltung, Finanzbeteiligung mit ungeklärter Rechnung, Eigentum auf eigene
  Rechnung; Finanzierung, Betrieb, Lieferverträge als eigene Typen ohne Datenanbindung.
  Branche je Unternehmen aus Wikidata (Finanzinstitut ja/nein), Börsenkotierung und
  Quellen-URL je Kettenglied aus GEM, Brennstoff/Eigenbedarf/Notstrom/Inbetriebnahme aus den
  GEM-Anlagenlisten (GOGPT, Kohlekraftwerke).
- **Ergebnis im ersten Entwicklungsfonds:** Konflikte bei Kohle und Expansion sanken
  deutlich. Bei Banken liefen die Ketten über Verwahrgesellschaften, Fonds und Treuhand oder
  über Aktienbestände unter 10 % an kotierten Versorgern – keine Eigentumsbeteiligung belegt.
  Bei einem Technologiekonzern sind die neuen Einheiten Dieselaggregate (teils Notstrom) und
  ein Gaskraftwerk für Rechenzentren. Einzelergebnisse mit Namen sind lokal unter `C:\TransparenzDaten\notizen\` dokumentiert, nicht veröffentlicht.
- **Zuordnung:** Registernummer (OpenCorporates, ACN/ABN, japanische Unternehmensnummer,
  NZBN) und GLEIF-Namenssuche mit Sitzland gebaut; Messung mit Clopper-Pearson-Grenze.
  Erst gemeinsam gemessen (299 Ergebnisse, 3 falsch, freigegeben), dann erkannt: Die Regeln
  wurden an genau diesen Fonds verbessert → zu optimistisch. Umgestellt auf unabhängige
  Messung (zwei Entwicklungsfonds, ein Testfonds ohne Anpassung danach): 60 von 61 richtig, untere Grenze 92.5 %, < 100 Fälle → **nicht freigegeben**.
  Gefundene und behobene Ursachen: Rechtsformen «Public Limited Company», «S.p.A.», «A/S»,
  Kurzform in Klammern, Länderprüfung bei Registernummern (Registerland statt Hauptsitz),
  GLEIF-Schreibweisen der Registernummern (ACN mit Leerzeichen, japanische Nummer
  zwölfstellig). Verbleibende Abweichungen: vier Fälle (Tochter gewählt; zwei gleichnamige
  GLEIF-Einträge; Referenz falsch; Wikidata-Registernummer einer Tochter).
- **116 Positionen ohne Kennungsweg (erster Entwicklungsfonds):** 4 über Registernummer zugeordnet, 78 mit
  eindeutigem Namensvorschlag (offen, in der freiwilligen Frageliste), 17 ohne passenden
  GLEIF-Rechtsträger, 12 mit mehreren gleichnamigen, 5 mit zu allgemeinem Namen. Je Position
  begründet im Bericht, Abschnitt 2.
- **Kategorien und Dauer:** Belegschema um `category` und `consequences_until`; Engine prüft
  Kategoriewirkung und Wirkungsdauer (Beginn, Folgen, behördlich bestätigte Abhilfe);
  `add_missing_columns` ergänzt die Spalten in bestehenden Datenbanken. Waffen: Kategorien
  «Handel zivile Schusswaffen» und «Dual-Use» (gesondert). Fiktive Beispielbelege mit
  Kategorien neu erzeugt, Demo-Datenbank und Website neu gebaut.
- **Quellen:** ATF-Seiten 403 (ungeprüft); IDB-Datensatzseite CC BY 4.0, keine Kennung;
  DOL-WHD-Katalog Public-Domain-Label, Spalten nicht lesbar (JavaScript); UMD/GLAD CC BY 4.0,
  kein Unternehmensbezug; EUR-Lex leer (Art. 57 nicht im Original gelesen). Tabelle mit allen
  Quellen nach Stufen oben in `docs/DATA_SOURCES.md`.
- **Parallele Änderung bemerkt:** Die Analytics-Dateien und `tests/test_site.py` wurden
  während dieser Session ausserhalb geändert und als eigener Commit abgelegt (`da7a9c5`,
  Opt-out über `?analytics=off`). Hier nicht angefasst.
- **Geprüft:** Pilotberichte im Browser der App (1024 px, 375 px): keine Seitenbreite über dem
  Fenster, breite Tabellen scrollen im Rahmen; Fallbeispiele mit vollständiger Belegkette. Bildschirmfotos
  scheiterten teils (Fenster im Hintergrund), deshalb Prüfung über Seiteninhalt und Masse.
- Tests: 45 neue, **327 bestanden**, Ruff sauber. Kein Push, nichts veröffentlicht. Abrufe nur
  bei GLEIF und Wikidata (frei, CC0), keine Downloads.

## 13.11.2026 – Claude (Fable 5.2): Kriterienmodell, Quellensuche, Entscheid-Speicher (D-041–D-044)

- Aufträge Jonas (drei Nachrichten): Stand ansehen; Quellen für Waffen, Zwangs-/Kinderarbeit,
  Entwaldung, Korruption und mehr Emissionsdaten suchen; nur ausdrücklich gewerblich
  Freigegebenes verwenden; Zuordnung möglichst automatisch mit Ja/Nein bei Unsicherheit;
  aufräumen; Kriterienmodell neu aufbauen (sechs, dann zwölf Kriterien, Startprofil).
- **Recherche:** rund 20 Suchen, danach rund 40 Originalseiten in fünf Leseaufträgen geprüft.
  Ergebnis in `docs/DATA_SOURCES.md`. Etwa ein Viertel der Seiten war automatisch nicht
  lesbar (403/404/leere Seite) und ist als «nicht gelesen» geführt. Nichts heruntergeladen.
- **Entscheid-Speicher:** `services/review_decisions.py`, `scripts/review_mapping.py`, Pilot
  liest die Entscheide und schreibt die offene Fragenliste. Am echten Fonds: 18 offene Fälle.
- **Kriterienmodell:** `criteria.toml` Schema 2, `catalog.py` mit Prüfung, Engine mit
  `profile_conflict`, Pilot mit Konflikt bei Kohle und neu belegter fossiler Expansion,
  Website-Vorlagen umgebaut, Methodikdokument neu.
- **Pilot neu gerechnet:** erstmals Konflikte bei Kohle und fossiler Expansion, vor allem
  kleine Beteiligungen von Banken (Zahlen lokal unter `C:\TransparenzDaten\notizen\` dokumentiert, nicht veröffentlicht).
- **Aufgeräumt:** STATUS.md auf den aktuellen Stand gekürzt (Verlauf bleibt hier und in Git),
  CLAUDE.md von veralteten Aussagen befreit (Wikidata-Sperre, Testzahl, Handoff) und um
  D-041/D-042 ergänzt, Handoff als historisch markiert, `.gitignore` ergänzt.
- **Visuell geprüft:** Fondsseite und Methodikseite, 1024 px und 375 px, dunkel. Hell nicht
  erneut geprüft. Pilotbericht (HTML) nach dem Umbau der Kriterientabelle nur über den
  Seiteninhalt geprüft (zwölf Kriterienzeilen, Seite läuft nicht über, Tabelle scrollt bei
  1024 px leicht im Rahmen); ein Bildschirmfoto kam nicht zustande.
- **Fehler unterwegs:** ein Suchbefehl über den ganzen Ordner lief ins Zeitlimit (abgebrochen,
  durch gezielte Suche ersetzt); ein bestehender Pilot-Test erwartete das alte Kohle-Ergebnis
  und wurde angepasst.
- Tests: 29 neue, **282 bestanden**, Ruff sauber. Kein Push, nichts veröffentlicht.

## 12.11.2026 – Claude (Opus 5.5): GEM-Beteiligungen im Pilotbericht (D-040)

- Auftrag Jonas: auch kleine und indirekte Beteiligungen sind wichtig.
- `scripts/pilot_fund_chain.py`: streamender XLSX-Leser (Standardbibliothek), `load_gem`
  (Energy Ownership Tracker, sechs fossile Besitzblätter, Zuordnung nur über GEMs LEI-Spalte),
  Beteiligungsstufen und Treuhand-Erkennung, `coal_finding`, Kriterienstatus Kohle, neuer
  Berichtsabschnitt 4 «Fossile Anlagen und Beteiligungen», Kohle-Spalte in den Tabellen.
  Neuer Schalter `--gem-dir`. Einlesen ca. 75 s.
- Prüfung am echten Fonds: Kohleanteile einer Grossbank, die zuvor als 20–50 % zählten,
  laufen über eine Verwahrgesellschaft (Verwahrung für Kunden) und sind jetzt korrekt als
  treuhänderisch markiert. Ergebnis je Stufe lokal unter `C:\TransparenzDaten\notizen\` dokumentiert, nicht veröffentlicht.
- Visuell geprüft (1280 px hell, 375 px): Karten, Abschnitt 4 mit Besitzketten,
  Kriterientabelle. Behoben: Kartentitel «auch indirekt», Treuhand in der Zusammenfassung als
  «keine Beteiligung», Aufschlüsselung als eigene Tabelle, «1 Position». Kein Überlauf der Seite.
- Tests: 17 neue (fiktive Excel-Dateien), 40 im Pilot, **253 gesamt bestanden**, Ruff sauber.
  Kein Push.

## 11.11.2026 – Claude (Opus 5.5): GEM-Daten geladen, Lizenz und Kennungen geprüft

- Jonas hat das GEM-Formular selbst ausgefüllt; mit seiner Zustimmung im Downloads-Ordner
  gesucht und `gem-data.zip` plus eine einzelne GOGPT-Datei ins Projekt kopiert (Originale
  bleiben in Downloads). Nur die Excel-Dateien entpackt.
- Excel mit eigenem, streamendem Standardbibliotheks-Leser gelesen (kein openpyxl, wie D-032);
  Leser und Auswertungen nur im Scratchpad, kein Projektcode geändert.
- Lizenz in 16 von 18 Dateien selbst belegt (CC BY 4.0); zwei Dateien ohne Vermerk.
- Kennungen: LEI-Spalte im Ownership Tracker, deckungsgleich mit der GLEIF-GEM-Datei.
  Öl-/Gasfelder nur mit Eigentümernamen.
- Messung zeigte zuerst absurde Werte (Banken als Kohlebesitzer). Ursache: Besitzketten über
  Portfolio- und Treuhandbeteiligungen. Mit Anteilsregel plausibel; Zahlen in
  `docs/DATA_SOURCES.md`. Nichts in den Bericht eingebaut, Tests unverändert. Kein Push.

## 11.11.2026 – Claude (Opus 5.5): Quellensuche für Ausschlusskriterien

- Auftrag Jonas («Quelle für Kriterien»): Belegquelle für die fünf Kriterien suchen.
- Geprüft (Originalseiten, teils im Browser der App): GEM, GLEIF-GEM-Zuordnung, Urgewald
  GCEL/GOGEL, Forest 500, Trase, Global Forest Watch, US DHS UFLPA, US CBP, NBIM/Etikkrådet.
  Nicht ladbar: Etikkrådet-Empfehlungen (404), EU-Zwangsarbeitsportal (429).
- GEM: Lizenz war über Textabruf nicht sichtbar (Seite baut sich per JavaScript auf, alte
  Lizenzseite 404, Fusszeile «All Rights Reserved»). Im Browser gefunden: Das Download-
  Formular verlinkt `/creative-commons-license` (vollständiger CC-BY-4.0-Text) und sendet
  den Lizenztext CC BY 4.0 mit. Cookie-Banner abgelehnt, Formular nur angesehen, nichts
  eingegeben oder abgeschickt.
- Geladen: nur die GLEIF-GEM-Zuordnung (100 KB, 6'860 Paare) für eine lokale Messung; keine
  Lizenz benannt, deshalb nicht im Bericht. Messung: 49 bestätigt zugeordnete Positionen
  (23.94 %) sind GEM-Rechtsträger; kein Kriterienbeleg.
- Kein Code geändert, Tests unverändert (236 beim letzten Lauf). Kein Push.

## 11.11.2026 – Claude (Opus 5.5): verständlicher Pilotbericht, visuell geprüft (D-039)

- Auftrag Jonas: bis zu einem verständlichen Pilotbericht weiter; bekannte Identitätskonflikte
  aus der bestätigten Abdeckung nehmen und separat zeigen; Emissionsdaten,
  Zuordnungssicherheit und Belege für Ausschlusskriterien getrennt ausweisen;
  Konzernbeziehungen zeitlich einordnen; visuell prüfen; beantwortbare Anlegerfragen zeigen.
  Keine neuen Quellen.
- Umgesetzt in `scripts/pilot_fund_chain.py`: Zuordnungsstufen (`mapping_confidence`),
  Belegstatus mit Sperrgründen (`identity_conflict`, `position_mapping_unconfirmed`,
  `outside_relationship_period` u. a.), zeitliche Einordnung aus der GLEIF-Beziehungsdatei
  (Beginn, Ende, Registrierungsdatum), GLEIF-Altnamen für die Namenskontrolle (vier
  API-Abfragen, keine neue Quelle), Kriterienstatus aus `criteria.toml`, HTML-Bericht.
- Ergebnis Pilotfonds: bestätigte Abdeckung 277 Positionen (80.42 %); zugeordnete
  Emissionsbelege 11 Positionen (2.02 %), alle aus dem EU-Emissionshandel; separat: ein
  Identitätskonflikt, zwei Fälle mit Emissionsjahren vor Beginn der Beziehung, 8
  Namens-Prüffälle, 10 mehrdeutige, 6 unbestätigte Konzernbezüge. Belege für
  Ausschlusskriterien: 0, alle fünf Kriterien «unbekannt». Einzelfälle mit Namen lokal.
- Visuelle Prüfung im Browser der App (lokaler Server nur auf 127.0.0.1, danach beendet):
  dunkler und heller Modus, 1280 px und 375 px. Gefunden und behoben: missverständliche
  Wegbeschreibung («Tochter … direkte Mutter»), unvollständige Zusammenfassungszeile bei
  mehreren Töchtern, «–» statt «kein Eintrag», zu breite Prüffall-Tabelle, umgebrochene
  LEIs, fehlendes Ergebnis je Konzernbeziehung, zu pauschaler Kartentext. Danach keine
  Tabelle mehr mit Überlauf bei 1280 px; bei 375 px scrollen breite Tabellen in ihrem
  Rahmen, die Seite selbst nicht.
- Tests: 9 neue (23 im Pilot), **236 bestanden**, Ruff sauber. Kein Push, Website unverändert.

## 11.11.2026 – Claude (Opus 5.5): EU-Emissionshandel als zweite Belegquelle im Pilot (D-038)

- Auftrag Jonas: «Mach eigenständig weiter». Als offener Schritt umgesetzt: das zuvor nur
  gemessene EU-Emissionshandelsregister in `scripts/pilot_fund_chain.py` eingebaut.
- Neu: `load_ets` (Union-Registry-Auszüge, LEI-Bindestriche entfernt, nur prüfziffergültige
  LEIs, «n/a» nie als 0), `summarise_ets` (Beleg nur mit verifiziertem Jahreswert),
  `load_group_links` (GLEIF-Beziehungsdatei statt API, gleiche Bestätigungsregel),
  `name_check` (reine Sichtprüf-Warnung, beeinflusst nie die Zuordnung). Bericht zeigt je
  Anlage Kennung, Tätigkeit, letztes verifiziertes Jahr, Wert und widerrufene Genehmigungen.
- Vorab die Rohdaten geprüft: 24'857 Anlagen, keine Doppelzeilen, 413'244 «n/a», keine
  negativen Werte, Jahre 2005–2025.
- Realer Lauf: 42 Beziehungen von Rechtsträgern mit Beleg zu Fondsunternehmen (34 bestätigt);
  GLEIF-API nur noch für 393 Rechtsnamen, keine Beziehungsabfragen. Ergebnis 14 Positionen
  (3.73 %) mit Beleg; alle 14 von Hand gesichtet, Auffälligkeiten in `docs/DATA_SOURCES.md`.
- Ein eigener Test scheiterte zuerst (Warntext stand auch in der Tabellenbeschriftung);
  Prüfung auf den konkreten Warnhinweis präzisiert. Danach **227 Tests bestanden**, Ruff sauber.
- Nicht erledigt: Registernummer-Brücke; Lizenzauslegung nicht extern geklärt; nichts im
  Update-System oder Screening; Website unverändert. Kein Push.

## 11.11.2026 – Claude: zweite Belegquelle geprüft (EEA-Industrieemissionen, EU-Emissionshandel)

- Auftrag Jonas («Ja, prüfen»): EU-Industrieemissionen auf Lizenz und Kennungen prüfen.
- EEA Industrial Reporting v16: Lizenz im Katalogeintrag des Datensatzes gelesen (CC BY 4.0,
  Rechteinhaberin EEA). Metadaten-PDF gelesen: Unternehmen nur als `parentCompanyName`
  (Freitext), kein LEI, keine Registernummer; je Anlage eine EU-ETS-Kennung. Keine Daten geladen.
- Deshalb EU-Emissionshandelsregister mitgeprüft: Tagesauszüge der Union Registry Public
  Website enthalten `ACCOUNT_HOLDER_LEI` und `ACCOUNT_HOLDER_COMPANY_REGISTRATION_NUMBER`.
  Rechtshinweis der Kommission im Browser gelesen (CC BY 4.0 für EU-eigene Inhalte, Namen und
  Drittinhalte ausgenommen); ob er wörtlich für die Registerdateien gilt, ist Auslegung.
- Geladen (alle Git-ignoriert, mit Hash und Nachweisdatei): zwei Registerauszüge (1.9 MB,
  6.1 MB) und die GLEIF-Beziehungsdatei Level 2 (CC0, 23 MB).
- Einmalige Messung im Scratchpad, kein Projektcode geändert: 15 Positionen des Pilotfonds
  (4.43 %) mit EU-ETS-Anlage, 3 direkt, 12 über aktiv/veröffentlicht/vollständig bestätigte
  Tochterbeziehung; 46 Anlagen.
- Nicht erledigt: kein Einbau in den Pilot; Registernummer-Brücke nicht versucht;
  EU-Sanktionsliste weiterhin ungeprüft; Treffer nicht einzeln von Hand verifiziert.
  Tests unverändert (222 bestanden beim letzten Lauf, kein Code geändert). Kein Push.

## 11.11.2026 – Claude: weltweiten ISIN-Abgleich in den Pilot eingebaut

- Auftrag Jonas («Ja, einbauen»): den zuvor nur gemessenen exakten ISIN-Abgleich gegen ganz
  Wikidata fest in `scripts/pilot_fund_chain.py` aufnehmen.
- Neu: `--fetch-wikidata` (SPARQL über P946, je 200 ISINs, nur prüfzifferngültige ISINs gehen
  in die Abfrage), Antwort als `<Fonds>_wikidata_isin.json` gespeichert; lokale und abgefragte
  Kandidaten werden über die Wikidata-ID zusammengeführt, nie über Namen. GLEIF-Gegenprobe:
  Ein LEI, den GLEIF nicht führt, blockiert die Belegübertragung
  (`candidate_lei_not_in_gleif`). Bericht neu gegliedert: Belege im Detail, übrige
  Zuordnungen als Tabelle mit GLEIF-Rechtsname und LEI-Registrierungsstatus, Unbekannte als Liste.
- Realer Lauf: 1 Wikidata-Abfragerunde (3 Abfragen, 346 Antwortzeilen), GLEIF 369 Rechtsnamen
  und 136 Beziehungsabfragen. Ergebnis: 336 Positionen mit Hinweis (90.71 %), 285 mit genau
  einem LEI (81.56 %), 10 mehrdeutig, 75 unbekannt, weiterhin 1 Position mit Beleg.
- Stichprobe von Hand: 50 Namensabweichungen durchgesehen; meist Originalschrift oder
  Umbenennung, ein Fall wahrscheinlich falscher LEI in Wikidata. 36 LEIs LAPSED.
- Tests: 3 neue (9 im Pilot), **222 bestanden**, Ruff sauber. Kein Push, Website unverändert.
- Nicht erledigt: kein dauerhafter ISIN-Bestand im Update-System; keine zweite Belegquelle;
  kein Prüfweg, der Wikidata-Hinweise zu bestätigten Zuordnungen macht.

## 11.11.2026 – Claude: tragfähige Datenversorgung gesucht, erster echter Fonds im Pilot (D-037)

- Auftrag: eigenständig nach einer Kombination suchen, die eine später gewerbliche
  Fondsanalyse erlaubt; fünf Rechte je Quelle getrennt prüfen; Vergleichstabelle; Einstieg an
  einem echten Fonds lokal testen. Keine Verträge, keine Sperren umgehen, keine Anbieter
  kontaktieren. Der Übergabetext verlangte zusätzlich «zuerst fragen, welcher der drei Wege»;
  dem neueren Auftrag gefolgt und das offen gesagt.
- Gelesen (Originalseiten, 11.11.2026): FI Schweden (Register und «Öppen data», selbst im
  Browser nachgeprüft), Swiss Fund Data (Klausel selbst nachgeprüft), Bundesanzeiger, EODHD,
  Finnhub, OpenFIGI, GLEIF-ISIN-Zuordnung, NBIM, EEA, EU-Kommission, EPA, Weltbank.
  Nicht lesbar: CNMV, CMVM, Financial Modeling Prep, fundinfo, mehrere Datensatzseiten.
- Geladen: genau eine Datei, `Fondinnehav_2026Q2` von FI (6.7 MB), nach
  `data/raw/external/fi_se_fondinnehav/2026Q2/` mit Hash und Bedingungsnachweis. GLEIF-API:
  eine Namensabfrage und 136 Beziehungsabfragen für die 68 meldenden Rechtsträger mit LEI.
  Wikidata: eine SPARQL-Abfrage über die 411 ISINs des Pilotfonds (nur Messung, nicht gespeichert).
- Gebaut: `scripts/pilot_fund_chain.py` (FI-XML lesen, exakter ISIN-Abgleich, Belege direkt
  oder über von GLEIF vollständig bestätigte Konzernbeziehung, Bericht als JSON/Markdown) und
  `tests/test_pilot_fund_chain.py` (6 Tests, nur fiktive Kennungen).
- Ergebnis Pilot: 411 Positionen, 6 mit Unternehmenshinweis, 1 mit Beleg (Schweizer Konzern
  über eine von GLEIF bestätigte Tochter). Zahlen und Grenzen in `docs/DATA_SOURCES.md` und `STATUS.md`.
- Tests: 219 bestanden, Ruff sauber. Website und Screening-Schema unverändert. Kein Push.
- Nicht erledigt: FI nicht im Update-System registriert; weltweiter Wikidata-ISIN-Abgleich
  nur gemessen, nicht eingebaut; keine zweite Belegquelle; Pilotbericht nicht visuell geprüft.

## 11.11.2026 – Claude: Suche nach freier UCITS-Positionsquelle (negativer Befund)

- Auftrag: Jonas wollte zur echten Fondsanalyse zurück, lehnte SEC N-PORT als erste Quelle ab
  (Zielgruppe Schweiz passt nicht zu einem US-Fonds) und wollte zuerst eine Schweizer/EU-
  UCITS-Quelle mit vollständigen Positionen gesucht haben.
- UBS ETF (`ubs.com/ch/de/assetmanagement/funds/etf...`): Zugriff verlangt vorher eine
  Anlegerprofil-/Domizil-Selbstdeklaration («Qualifizierter Anleger» o. Ä.) – bewusst nicht
  durchgeklickt (keine Anleger-Selbstauskunft durch ein Werkzeug abgeben), Aktion wurde vom
  System auch blockiert. Lizenzfrage bleibt dadurch offen.
- Raiffeisen Futura – Global Stock A, Factsheet `GlobalStock-d.pdf` direkt von raiffeisen.ch
  geladen (öffentlich, kein Gate): enthält nur die 10 grössten Positionen (keine
  Vermögensaufstellung) und ein explizites Weiterverbreitungsverbot («darf ohne schriftliche
  Genehmigung von Raiffeisen weder auszugsweise noch vollständig vervielfältigt und/oder
  weitergegeben werden»), dazu separate Copyright-Klauseln für die ESG-Daten (Inrate/FE
  fundinfo) und MSCI-Daten («ausschliesslich für den internen Gebrauch»).
- Einordnung: Das deckt sich mit der bereits dokumentierten Vermutung «Anbieter-Urheberrecht»
  in `docs/DATA_SOURCES.md`. Die rechtlich massgebliche Vermögensaufstellung steht laut
  Factsheet im Jahres-/Halbjahresbericht, dessen eigene Lizenz noch nicht geprüft ist.
- Befund in `docs/DATA_SOURCES.md` (zwei neue Abschnitte) und `STATUS.md` festgehalten.
  Kein Code geändert, keine neue Quelle angebunden, nichts heruntergeladen ausser dem einen
  Factsheet (im Scratchpad, nicht im Projekt). Offene nächste Schritte mit Jonas zu klären:
  schriftliche Anfrage an einen Anbieter, Halbjahresbericht statt Factsheet prüfen, oder
  N-PORT nochmals als Thema aufgreifen.

## 11.11.2026 – Claude: globalen Wikidata-Rohbestand lokal durchsuchbar gemacht (D-036)

- Auftrag (Jonas, nach dem Live-Update-Fix): den bereits heruntergeladenen globalen
  Wikidata-Bestand (15'624 Zeilen) lokal durchsuchbar machen, vorerst **keine** weiteren
  Länder/Quellen hinzufügen, keine ISINs ergänzen, keine Zuordnung über gleiche Namen/Ticker,
  CVM-Brasilien getrennt halten, Qualitätsbericht, Parallellauf-Schutz prüfen, Tests/README/
  STATUS aktualisieren.
- Neue Module (bewusst getrennt von `swiss_foundation.py`/`swiss.sqlite` und
  `market_catalog.py`/`markets.sqlite`, da weder Länder- noch SEC-Schema passen):
  `services/global_candidates.py`, `reports/global_candidates.py`, CLI-Befehle
  `global-candidates-build [--refresh-labels]` und
  `global-candidates-search BEGRIFF [--country X] [--exchange X]`.
- Börsennamen/-länder waren im Rohbestand nur als QID vorhanden; einmalig per beschränkter
  Wikidata-`VALUES`-Abfrage über die 199 im Bestand vorkommenden Börsen-QIDs aufgelöst
  (Label + der Börse **eigenes** Sitzland, P17 – nicht automatisch das Firmensitzland, wegen
  Zweit-/Auslandskotierungen) und als reale, nicht-fiktive Daten unter
  `data/processed/global_candidates/exchange_labels.json` zwischengespeichert (gitignored,
  nicht committet). `global-candidates-build` fragt nur fehlende/erzwungene QIDs neu ab;
  ist der Cache vollständig, läuft die Suche komplett offline (durch Test
  `test_cache_already_covering_all_ids_never_hits_the_network` erzwungen).
- Keine Fusion über Namen/Ticker: Mehrere Zeilen desselben Wikidata-Items (z. B. Toyota mit
  Tickern `TM` an der NYSE und `7203` in Tokio) bleiben eine Firma
  (`companies_with_multiple_tickers`); gleicher Name bei verschiedenen Items (z. B. zwei
  fiktiv getestete «Zwilling AG») wird nur als **mögliche Dublette** gelistet
  (`possible_duplicates`, dieselbe Normalisierung wie im Schweizer Fundament), nie
  automatisch zusammengeführt.
- Suchranking verbessert: reine Teilstring-Suche hätte bei «Roche» zuerst zufällige Treffer
  wie «…petrochemical…» vor «Roche Holding» gezeigt (die Buchstabenfolge «roche» steckt
  wörtlich in «petrochemical»); jetzt werden Namens-Präfix-/Wort-Treffer vor einem
  eingebetteten Teilstring-Zufallstreffer einsortiert. Akzent-insensitive Suche ergänzt
  («Nestle» findet auch «Nestlé»).
- Reale Stichprobe (alle vier anschliessend auch per `--country`/`--exchange`-Filter
  geprüft): Siemens (Deutschland, Börse Frankfurt), Toyota (Japan + USA), Nestlé (Schweiz,
  plus Nestlé Lanka/Nestle Malaysia Berhad als eigene Firmen), Roche Holding (Schweiz, zwei
  Tickerklassen RO/ROG). 88 Länder (Börsen-Sitz), 199 Börsen, 14'367 eindeutige Unternehmen,
  112 mögliche Namensdubletten, 21 Zeilen ohne bekanntes Börsen-Sitzland – alles im
  Qualitätsbericht (`quality_report.json`, auch in der HTML-Ansicht) offen ausgewiesen.
- Parallellauf-Schutz geprüft, nicht neu gebaut: Windows-Task `MultipleInstances=IgnoreNew`
  (verhindert zwei Instanzen des Tages-Tasks) plus derselbe Datei-Lock-Mechanismus wie
  `swiss-update`/`market-update` (`global_candidates_lock()`, eigener Ordner, keine
  Kollision); Fehler/Status bleiben wie bisher in datierten Logs unter
  `data/processed/automation/`.
- 9 neue Tests (`tests/test_global_candidates.py`, ausschliesslich fiktive QIDs/Namen,
  Börsenlabel-Cache offline vorbelegt) + bestehende Suite: **213 Tests bestanden**, Ruff
  sauber. README.md um den neuen Befehl ergänzt, STATUS.md und CLAUDE.md (Pfadtabelle)
  aktualisiert.
- Nicht erledigt/offen: CVM-Brasilien-Bestand bewusst nicht angefasst; kein Einbau in
  `swiss-search`/`market-search`/Screening; keine neue Quelle/kein neues Land hinzugefügt.
  Keine Produktionsdaten/Website geändert, kein Push.

## 11.11.2026 – Claude: autonomen Tages-Update-Task aktiviert, globaler Download erfolgreich

- Auftrag: Jonas wollte "viel mehr Informationen" (alle investierbaren Firmen weltweit) und
  vorher den Live-Update-Status der Schweiz geklärt haben. Status war laut STATUS.md: Task
  nicht aktiv (Windows-CIM-Fehler bei der Registrierung), globale Wikidata-/CVM-Downloads an
  DNS gescheitert.
- `scripts\install_autonomous_update.ps1` in dieser Sitzung erneut ausgeführt: Task
  `ProjektTransparenz-DailyDataUpdate` erfolgreich registriert (täglich 09:00 + bei Anmeldung,
  nächster Lauf 12.11.2026 09:00). Der zuvor dokumentierte CIM-Zugriffsfehler trat nicht mehr
  auf; vermutlich sitzungs-/umgebungsabhängig, nicht weiter untersucht.
- Echten Testlauf von `scripts\autonomous_update.py` ausgeführt (alle drei Teiljobs
  `returncode 0`, kein Fehler):
  - `global_candidates`: lief diesmal durch. Wikidata weltweit **15'624** Firmen-/Ticker-/
    Börsen-Kandidaten (CC0, Query auf P414-Statement mit P249-Ticker-Qualifier, kein Enddatum,
    kein deprecated Rank) und CVM Brasilien **2'679** Firmenregistereinträge (ODbL) als neue
    Rohdaten-Snapshots unter `data/raw/external/wikidata_global/` bzw. `cvm_companies/`
    gespeichert. Beide bleiben **unintegrierte Recherchebestände**
    (`status: unverified_research_snapshot`, `complete_world: false`); keine Suchfunktion,
    kein Screening-Zugriff. Nächste Integration muss Identitäten separat erhalten
    (Wikidata-Item ≠ bestätigtes Wertpapier; CVM-Registrierung ≠ Kotierungsnachweis).
  - `market`: SEC-Ticker/Fondsklassen turnusgemäss neu geladen (10'414 / 28'641 Datensätze,
    unverändert zum bisherigen Bestand).
  - `swiss`: alle vier Quellen noch nicht fällig (Intervall), bestehender Export
    weiterverwendet, 293 Wertpapierkandidaten unverändert.
- Zusätzlich live gegen `query.wikidata.org` verifiziert (reine Leseabfragen, keine
  Codeänderung): für Deutschland/Frankreich/Niederlande liefert dasselbe VALUES-pro-Börse-
  Muster wie bei der Schweiz (korrekte QIDs geprüft: Börse Frankfurt Q151139, Euronext Paris
  Q2385849, Amsterdamer Börse Q478720) **811 / 363 / 170** ungeprüfte Firmenkandidaten in
  Sekunden – Beleg, dass sich der Schweizer Ansatz auf weitere Märkte übertragen lässt.
  Noch keine Konfiguration/Code dafür angelegt; Speicherort (weder `swiss.sqlite` noch
  `markets.sqlite` passt schemabedingt) mit Jonas noch zu klären.
- Keine Produktionsdaten/Website geändert, kein Push. STATUS.md und
  `docs/AUTONOMOUS_UPDATES.md` aktualisiert.

## 11.11.2026 – Codex: KI-Nutzung, Skills und Werkzeuge auf GitHub sichtbar machen

- Auftrag von Jonas: Im GitHub-Projekt anzeigen, welche Skills und weiteren Werkzeuge
  verwendet werden. Dieser Auftrag autorisiert die Veröffentlichung dieser Dokumentation.
- README um eine sichtbare Übersicht ergänzt; `docs/AI_USAGE.md` dokumentiert belegte
  Claude-/Codex-Beiträge, Skills, technische Werkzeuge, Quellen und Grenzen.
- Verwendeter Skill: `cloud-environment:cloud-environment-runtime` einschliesslich
  Netzwerk-/Paketinstallationshinweisen; Quelle in `docs/AI_USAGE.md` verlinkt.
- Werkzeuge: Git und Shell/Python zum Lesen, Bearbeiten und Prüfen; GitHub-Connector
  zum Bereitstellen der Änderung. Keine Unteragenten eingesetzt.
- Frühere konkrete Skill-Aufrufe und Modellversionen sind nicht erfasst; keine nachträgliche
  Zuschreibung aus der blossen Verfügbarkeit eines Skills.
- `CLAUDE.md` um Pflegepflicht für Skills/Tools im Sessionlog ergänzt; STATUS aktualisiert.
- Prüfung: lokale Dokumentationslinks auf vorhandene Ziele geprüft; `git diff --check`
  bestanden. pytest/Ruff hier nicht ausgeführt: Module in dieser Cloud-Umgebung fehlen.
  Ausschliesslich Markdown geändert, keine App-, Daten- oder Website-Änderung.
- Veröffentlichung betrifft die Repository-Dokumentation; kein Pages-Deployment ausgelöst.

## 08.11.2026 – Folgeauftrag Codex: automatische Pflege und Downloadversuche

- Tages-Orchestrierung mit Einzeljob-Protokollen, Sperre, Fehlerstatus; vorhandene
  Quellenintervalle und letzte gültige Snapshots bleiben massgeblich. Task-Installer
  für 09:00/Anmeldung mit Benutzerrechten und unsichtbarem Python-Prozess.
- Zusätzliche feste Downloads: Wikidata global (CC0) wöchentlich, CVM-Unternehmensregister
  (ODbL) täglich; ausschliesslich separate Recherche-Snapshots, kein Such-/Screeningimport.
- Beide echten Downloadversuche scheiterten an DNS (Errno 11001). Registrierung der
  Windows-Aufgabe scheiterte am CIM-Zugriff. Zeitplan nicht installiert/aktiv bestätigt.
- Anleitung und Quellenlinks: `AUTONOMOUS_UPDATES.md`. Kein Push.
- Audit: 100 eindeutige Zeilen, Summen 57/43 und 10'419 SEC-Originaltupel nachgeprüft.
  194 bestehende Tests ohne End-to-End bestanden. Vollsuite an Temp-Rechten gescheitert;
  Versuch mit lokalem Temp blieb bei Streamlit hängen und wurde abgebrochen.

## 08.11.2026 – Codex: 100 weltweite Firmen auf Katalogabdeckung geprüft

- Zehn Märkte, je zehn Zufallsziehungen aus dokumentiertem 120er-Pool (Seed 20261108).
  Ergebnis: 57 Firmenhinweise, 43 ohne Treffer; 50 SEC, 10 Schweizer Kandidaten, 3 Überlappungen.
- Namensfallen (Tencent Music, Siemens Energy/Healthineers, CSL Vifor usw.) verworfen;
  UBS-/Bradesco-Namensvarianten und Daimler/Mercedes-Benz-Umbenennung berücksichtigt.
- Alle 10'419 SEC-Originaltupel CIK/Ticker/Börse exakt im Export enthalten, Originalhash geprüft.
- `docs/COVERAGE_AUDIT_100.md`: 100 Einzelbefunde, Ursachen, Quellen und Beschaffungswege.
  `scripts/company_coverage_probe.py`: Nur-Lese-Abgleich und lokale Prüfdaten.
- Offizielle Quellen recherchiert: globales Wikidata CC0 als Kandidatenweg; JPX/B3 nicht
  pauschal kommerziell frei; CVM-ODbL-Register ersetzt keine Instrumentliste.
- Direkter SPARQL-Versuch scheiterte an Umgebungs-DNS; keine neuen Importzahlen behauptet.
  Recherche über verfügbaren Webzugang. Keine Produktionsdaten/Website geändert, kein Push.

## 08.11.2026 – Claude: Wikidata-Wertpapierkandidaten reparieren und durchsuchbar machen

- Auftrag: Jonas meldete, Roche/Nestlé fehlten in der lokalen Suche; geprüft, ob das fehlende
  Daten oder ein Suchfehler sind. Befund: `wikidata_ch` war technisch kaputt, nicht nur durch
  einen anhaltenden HTTP 403 blockiert (D-034 im Detail).
- Drei Bugs in `data/queries/wikidata_ch.sparql`/`wikidata_funds.sparql` gefunden und live
  gegen `query.wikidata.org` verifiziert: falsche SIX-Swiss-Exchange-ID (Q12569 = Fluss Loire,
  richtig Q661834), falsche Fondsklassen-IDs (Q927783/Q756898 = Person/Dorf, richtig
  Q845477/Q4201895), und eine zu teure, transitiv über ganz Wikidata laufende Abfrage. Abfrage
  auf «SIX-notiert oder CH-ansässig mit ISIN» eingegrenzt → Antwortzeit 1–3 s statt Timeout.
- Vierter Bug: generischer HTTP-User-Agent ohne Kontaktangabe verletzte Wikimedias Bot-Policy
  und wurde gelegentlich mit 403 beantwortet. `http_user_agent` in
  `src/transparenz/config/settings.py` projektweit (GLEIF/Zefix/Wikidata gemeinsam) auf
  `ProjektTransparenz/0.1 (+https://github.com/Jonasbader7/Projekt-Transparenz)` umgestellt.
- `_wikidata()` in `src/transparenz/ingestion/external.py` von melted `?property ?value`-Zeilen
  auf feste Spalten umgebaut (das melted Muster lief beim Live-Test selbst auf der bereits
  eingegrenzten Subjektmenge wiederholt in Zeitüberschreitung); zusätzlich Ticker-Qualifier
  (`pq:P249` auf der Börsenangabe) ergänzt, da z. B. Roches Ticker nur als Qualifier, nicht als
  eigene Aussage vorliegt.
- Neuer Fund beim echten Lauf: zwei Wikidata-Items können dieselbe LEI tragen (live:
  «AGEN Holding» / «Aevis Victoria SA»). Neue Quarantänelogik (`lei_shared_by_multiple_
  wikidata_items`) verhindert, dass das den ganzen Quellenlauf verwirft oder beide über den
  Namen fusioniert werden.
- `wikidata_ch` läuft seit diesem Fix im Standardlauf mit (`enabled = false` entfernt).
  Echtlauf: **287 Datensätze → 293 Wertpapierkandidaten** (u. a. Roche, Nestlé, Novartis, UBS,
  ABB, Swatch, Credit Suisse, Lindt & Sprüngli), 3 neue LEI-Konfliktgruppen unter Quarantäne.
  Fonds-/ETF-Teilabfrage lieferte im Schweizer/SIX-Zuschnitt 0 Treffer (weltweit 19) – ehrlich
  dokumentiert, nicht verschwiegen.
- Neu durchsuchbar: CLI-Befehl `swiss-search <Begriff>` (`src/transparenz/cli.py`,
  `search_foundation()`/`security_candidate_rows()` in `swiss_foundation.py`) und eine lokale
  `security_candidates.html` je Exportgeneration (`src/transparenz/reports/
  swiss_security_candidates.py`, gleiches Muster wie `reports/market_catalog.py`, aber bewusst
  getrennt vom SEC-Marktkatalog: andere Lizenzquelle/Vertrauensstufe). Im Browser geprüft:
  293 Einträge rendern, Suche nach «roche» filtert korrekt auf die zwei Roche-ISINs.
- Vorher/Nachher per `market-search` dokumentiert: Roche/ABB fanden vorher nur Scheintreffer
  («Rochester»-Fonds, Ticker `PABBX`); Nestlé 0 Treffer; Novartis/UBS fanden nur US-ADR-Ticker.
  SEC-Katalog selbst unverändert (44'085 Einträge, D-033 bleibt gültig).
- Neuer Unit-Test `test_wikidata_security_candidate_and_shared_lei_quarantine` (fiktive QIDs/
  ISINs/LEIs) deckt Ticker-Qualifier-Extraktion und LEI-Konflikt-Quarantäne ab.
  **201 Tests bestanden** (200 + 1 neu), Ruff sauber, Offline-Audit bestanden.
- Keine neuen Abhängigkeiten, keine Änderung an Screening-Engine/Webdesign, nichts
  veröffentlicht oder gepusht. STATUS/DECISIONS/DATA_SOURCES aktualisiert.

## 08.11.2026 – Codex: lokaler Aktien-/Fonds-Katalog aus SEC-Originalen

- Auftrag auf alle weltweit börsenkotierten Aktien und ETFs erweitert; nicht vollständig erfüllt.
  Geprüfter kostenloser SEC-Teilbestand tatsächlich geladen; keine globale Vollständigkeit behauptet.
- 10'419 SEC-Ticker-/Börsenzuordnungen, 28'647 aktuelle Fonds-Ticker-/Class-Zuordnungen und
  45'456 N-CEN-Beobachtungen aus 2025Q4–2026Q3 aktiviert. Sieben Originaldateien mit Sidecars.
- `market-update`, `market-search`, separate DB/Tabelle, lokale HTML-Suche/JSON und Qualitätsbericht.
  44'085 Einträge: 4'168 ETF-Ein-Klassen-Nachweise, 212 Klassen von ETF-Mehrklassenserien offen,
  29'284 sonstige Fondsklassen, zwei Identitätskonflikte, 10'419 unklassifizierte Tickerclaims.
- Nichtstandardisierte SEC-Serienkennung und Class-ID-Platzhalter im realen N-CEN-Bestand
  erhalten, ohne sie als gültige Identitäten zu verwenden. Frühere fehlgeschlagene Versuche
  bleiben im Updateprotokoll; letzte gültige Version wird geschützt.
- SEC-Kontakt mit Zustimmung nur in ignorierter `.env`; keine Adresse in Code/Metadaten/Git.
  NasdaqTrader, TickerInside-Upstream und FIRDS nicht produktiv freigegeben. Weitere Weltmärkte offen.
- 200 Tests bestanden (183 + 17), Ruff sauber. Gesamtsuite im eingeschränkten Streamlit-Lauf
  ohne Fortschritt abgebrochen. Ein späterer Lauf im OneDrive-Testordner hatte WinError 5 beim
  atomaren Dateiersatz; abschliessend im normalen temporären Testordner 200/200 bestanden.
  Offline-Audit bestätigt sieben Originalhashes und alle 4'168 ETF-Nachweise;
  JS-Syntax `node --check` sauber.
  Visuelle Prüfung im Browser durch dessen `file:`-URL-Sperre verhindert; keine Umgehung.
- Anleitung und Ausbau: `docs/GLOBAL_MARKET_CATALOG.md`; STATUS/Quellen/Entscheide/Handoff gepflegt.
  Keine neuen Abhängigkeiten, keine Änderung am öffentlichen Webdesign, kein Push.

## 08.11.2026 – Claude: SwissPRTR-Emissionen 2007–2024 normalisiert

- Auftrag: das bereits archivierte Original-XLSX tatsächlich in die bestehende Importarchitektur
  normalisieren (nicht nur archiviert lassen). Gelesen mit Stdlib (`zipfile`/`xml.etree`), kein
  neues Framework; dieselbe No-Dependency-Logik wie beim GeoPackage-Adapter.
- Neue Funktionen `_xlsx_header_and_rows`/`_swissprtr_emissions` in
  `src/transparenz/ingestion/external.py`; neuer `emissions`-Export-Bucket mit Verknüpfung in
  `src/transparenz/services/swiss_foundation.py`. `EXPORT_SCHEMA_VERSION` 1 → 2.
- Verknüpfung zu Rechtsträgern ausschliesslich über die im XLSX gemeldete, prüfzifferngeprüfte
  Betriebs-UID (nie über den Namen); das Standortregister selbst hat keine UID und bleibt wie
  bisher ohne Firmenzuordnung.
- Tatsächlicher Lauf (`swiss-update --source swissprtr`, danach vollständiger Re-Export):
  22'860 Emissionszeilen, davon 16'058 Punktquellen einem Rechtsträger zugeordnet, 5'298
  Punktquellen mit gültiger UID ohne passenden Rechtsträger, 28 ohne verwertbare UID, 1'476
  Nicht-Punktquellen ausdrücklich ohne Betrieb/Zuordnung. Emissionen sind kein Nachweis eines
  Rechtsverstosses (eigene `evidence_category`, Hinweis im Qualitätsbericht).
- 4 neue Tests (Pflichtspalten, Punkt-/Nicht-Punktquelle, ungültige UID-Prüfziffer, End-to-End-
  Verknüpfung über `export_foundation`); Gesamtsuite **183 bestanden**, Ruff sauber.
  `scripts/audit_swiss_foundation.py` um Emissionsprüfungen (Prüfziffern, Jahr, Zuordnungsquote)
  erweitert und erfolgreich gegen den tatsächlichen Bestand ausgeführt.
- STATUS.md, docs/DECISIONS.md (D-032) und docs/CODEX_TO_CLAUDE_HANDOFF.md aktualisiert.
  Kein Push, keine kostenpflichtigen Dienste; nur lokaler Commit.

## 08.11.2026 – Nachbesserung nach PowerShell-Standardlauf

- Der gemeldete 403 war die bekannte Wikidata-Zugangssperre; die übrigen Quellen waren aktuell.
  Wikidata nun mit sichtbarem Grund im Standardlauf deaktiviert. Explizite Einzelabfrage
  bleibt möglich und meldet Zugangsfehler weiterhin mit Exitcode 1.
- Unveränderte Datenversionen verwenden den fertigen Export weiter, ohne erneut Hunderttausende
  Datensätze zu parsen und grosse Exportdateien zu schreiben. Aktuelle Diagnosen separat in
  `latest_status.json`; historische Generationen bleiben unverändert.
- Korrigierten Standardlauf am tatsächlichen Bestand ausgeführt: Exitcode 0,
  801'647 Rechtseinheiten, vorhandene Exportgeneration wiederverwendet; keine Netzwerkabfrage.
- Gezielte Regressionstests für Wiederverwendung, neue Versionen, fehlende Dateien,
  Schemawechsel, expliziten Neuaufbau sowie Standard-/manuelle Quellenauswahl ergänzt.

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
