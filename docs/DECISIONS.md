# Entscheidungslog

## 16.11.2026 – Phase 2: Wertpapierstamm ISIN → LEI aus N-PORT (Claude, Auftrag Jonas)

### D-058 Freigabe der Namenssuche an der N-PORT-Referenz, je Region
- **Entscheid (Jonas: «Ja, umstellen»):** Mit `--security-master` (Pilotskript) gilt als
  Referenz der Namenssuche: menschlicher Entscheid, sonst der N-PORT-Konsens (D-056). Die
  Wikidata-Kennung ist dann keine Referenz mehr; an N-PORT gemessen ist sie selbst nur
  96.24 % (untere Grenze) genau (D-057). Ohne Wertpapierstamm bleibt die frühere Referenz.
  Eigener Speicher `mapping_reference_cases_nport.json`, damit die zwei Referenzen nie
  gemischt werden.
- **Je Region (D-046 umgesetzt):** Region = vom Fonds gemeldetes Emittentenland, sonst
  ISIN-Land (`entity_matching.position_region`): Nordamerika, Europa, Asien-Pazifik, übrige,
  unbekannt. Die Namenssuche wirkt nur für Positionen in Regionen, deren unabhängige Fälle
  die unveränderte Regel erfüllen (≥ 100 Fälle mit Ergebnis, untere 95-%-Grenze ≥ 97 %).
  Die Unabhängigkeitsregeln (Testfonds, keine ISIN aus Entwicklungsfonds) bleiben.
- **Grenze:** Die Referenz umfasst nur Titel, die US-Fonds halten (grosse, liquide Titel).
  Für kleine Titel ohne US-Fondsbesitz ist die Präzision nicht gemessen; die Freigabe wird
  dort trotzdem angewandt, weil die Region und nicht die Grösse die Freigabeeinheit ist.
  Das steht im Bericht.
- **Ein Name wirkt nie gegen eine Kennung:** Nennt die Namenssuche für eine Position einen
  anderen LEI als den bestätigten N-PORT-Konsens, wirkt sie dort nicht (Status bleibt
  Vorschlag, `auto_match.name_contradicts_reference`). Anlass: Im ersten Lauf ordnete die
  Freigabe 6 Papiere (7 Positionen) einer Tochter- oder Schwestergesellschaft zu.
- **Vergleichslauf (D-051):** Ausgangsstand frisch mit dem letzten Commit gerechnet. Neuer Code
  ohne Wertpapierstamm: 33 von 33 JSON-Dateien gleich (ohne die neuen Felder und den
  Ordnernamen in den Herkunftspfaden). Mit Wertpapierstamm, zwei Durchgänge: unabhängig 645 von
  649 richtig (untere Grenze 98.60 %); freigegeben in Europa (270/272, 97.70 %) und
  Asien-Pazifik (243/244, 98.07 %); nicht in Nordamerika (60/60, < 100 Fälle) und übrige
  (72/73). Wirkung über sechs Fonds: 689 Positionen neu über den Namen, 30 neu durch
  Übereinstimmung zweier Wege, 10 Vorschläge wegen Widerspruch gesperrt, danach 0 Zuordnungen
  gegen den Konsens. Von den 689 bestätigt N-PORT 645 mit demselben LEI; 44 Positionen
  (5 % des neu zugeordneten Gewichts) liegen ausserhalb der Referenz. Bestätigte Abdeckung je
  Fonds vorher 44–81 %, nachher 70–86 % des Fondsgewichts.

### D-056 Wertpapierstamm aus dem Konsens unabhängiger Fondsgesellschaften
- **Entscheid (Auftrag Jonas: «Starte Phase 2»):** `security-master-build` erzeugt aus dem
  aktiven N-PORT-Stand `processed/security_master.sqlite` (je ISIN Status, LEI, Zahl der
  Meldenden; je gemeldetem LEI eine Zeile `claims`) und einen Qualitätsbericht. Die
  N-PORT-Datenbank wird nur lesend geöffnet. Regelversion `RULE_VERSION` in
  `services/security_master.py`; jede Regeländerung = neue Version, neuer Aufbau.
- **Umfang:** nur Meldungen «current», nur gültige ISIN, ohne Derivate (`DCO`, `DCR`, `DE`,
  `DFE`, `DIR`, `DO`): Dort nennt der LEI oft Gegenpartei oder Börse.
- **Bestätigt** = mindestens zwei *unabhängige* Fondsgesellschaften melden denselben LEI,
  niemand nennt einen anderen, und der LEI steht bei GLEIF, ist nicht annulliert und kein
  Duplikat ohne Nachfolger. Inaktive Rechtsträger bleiben bestätigt (Emittent zum Stichtag);
  der GLEIF-Status steht daneben.
- **Unabhängig (Abweichung vom Plan «verschiedene CIK»):** Grosse Anbieter melden über
  Dutzende Trusts mit denselben Stammdaten; verschiedene CIK sind deshalb nicht unabhängig.
  Zwei Fonds gehören zur selben Gruppe, wenn sie dieselbe CIK haben oder einen gemeinsamen
  Anlageberater laut N-CEN (gleicher LEI, gleiche oberste Mutter laut GLEIF-Beziehungsdatei,
  gleiche SEC-Nummer «801-…» oder CRD-Nummer). Nur Berater vom Typ «Advisor»; Unterberater
  würden fremde Familien verbinden. Nur Kennungen, nie Namen. Wirkung im Stand 2026q3:
  15'045 ISIN wären unter der CIK-Regel bestätigt, unter der Beraterregel nicht.
- **Normalisierung nur über Kennungen:** GLEIF-Duplikat mit Nachfolger → Nachfolger (505
  Meldungen); Trust-LEI und Serien-LEI desselben Trusts (laut N-PORT-Meldung des Trusts)
  zählen für die Serie (474 Meldungen). Jede Ersetzung steht in `claims.normalization`.
- **Widerspruch** = nach der Normalisierung mehr als ein LEI, auch gegen eine klare Mehrheit.
  Die Art wird beschrieben (Nachfolger, Mutter/Tochter, gleiche Gruppe, Fondsstruktur,
  inaktiv, übrige), aber nicht aufgelöst. Stichprobe der «übrigen»: echte Fehlmeldungen
  einzelner Fonds (z. B. falsche Hypothekenagentur, Schwesterfonds).
- **Grenze:** Gemeinsame Datenlieferanten der Fondsgesellschaften sind nicht erkennbar; ein
  Konsens kann deshalb einen übernommenen Fehler bestätigen (ein Fall in der Gegenprüfung).
  Nur Papiere, die US-registrierte Fonds halten.

### D-057 Gegenprüfung der Pilotverfahren an der N-PORT-Referenz (Messung, keine Freigabe)
- **Entscheid:** `security-master-compare` misst Wikidata, Registernummer und GLEIF-
  Namenssuche des Pilots an den bestätigten ISIN, je ISIN einmal, gesamt und je Region
  (seit D-058 wie die Freigabe: gemeldetes Emittentenland der Position, sonst ISIN-Land). Für
  Registernummer und Name zählen wie in D-046 nur ISIN aus Testfonds, die in keinem
  Entwicklungsfonds vorkommen. Ergebnis lokal in `processed/security_master/
  pilot_comparison.json`.
- **Ergebnis 16.11.2026:** Namenssuche 675 von 679 richtig, untere 95-%-Grenze 98.66 %
  (Europa 270/272, 97.70 %; Asien-Pazifik 265/266, 98.23 %; Nordamerika 60/60 und übrige
  80/81 unter 100 Fällen). Registernummer 115/116 (95.98 %). Wikidata 626/642 (96.24 %).
  Einzeln geprüft: In 19 von 21 Abweichungen nennt N-PORT die börsenkotierte Gesellschaft und
  das andere Verfahren eine Tochter, Vorgängerin oder einen fremden Rechtsträger; in einem
  Fall ist die N-PORT-Referenz selbst fraglich.
- **Folge:** Die Freigabe in `entity_matching.py` bleibt unverändert, bis die N-PORT-
  Referenz dort als Referenz eingebaut ist (eigener Schritt mit Vergleichslauf, D-051). Die
  Referenz ist auf grosse, von US-Fonds gehaltene Titel verzerrt; das wird bei der Freigabe
  je Region ausgewiesen.

## 16.11.2026 – Phase 1: gemeldete LEI gegen GLEIF prüfen (Claude, Auftrag Jonas)

### D-055 GLEIF-Liste Level 1 als lokale Prüfquelle für gemeldete LEI
- **Entscheid (Jonas: «Ja, GLEIF laden»):** Golden Copy Level 1 vom 15.11.2026 16:00
  (509'687'964 Bytes, 3'494'789 Datensätze, CC0) liegt unverändert in
  `raw/external/gleif_lei2_golden_copy/2026-11-15/` mit Begleitdatei. `ingestion/
  gleif_level1.py` liest sie direkt aus dem ZIP und behält nur die gesuchten LEI.
- **Definitionen:** «vorhanden» = LEI steht in der Liste; «aktiv» = `Entity.EntityStatus =
  ACTIVE` (Rechtsträger besteht); «gepflegt» = `Registration.RegistrationStatus = ISSUED`.
  `LAPSED` (Verlängerung überfällig) heisst nicht, dass der Rechtsträger erloschen ist, nur
  dass die Angaben veraltet sein können. Beides wird getrennt ausgewiesen, je LEI und
  gewichtet mit der Zahl der Positionen.
- **Zeitpunkt:** GLEIF-Stand 15.11.2026, N-PORT-Stichtage Mai–Juli 2026. Ein seither
  erloschener Rechtsträger zählt als nicht aktiv; das wird im Bericht genannt, nicht
  korrigiert.
- **Zwischenspeicher:** Ergebnis je Paar (GLEIF-Prüfsumme, N-PORT-Datenstand) in
  `processed/nport/gleif_check_*.json`; neue GLEIF-Datei oder neuer Stand = neue Messung.
- **Noch keine Bereinigung:** Duplikate (`DUPLICATE`) und Nachfolger werden gezählt, aber
  nicht ersetzt. Das gehört zum Wertpapierstamm (Phase 2).

## 15.11.2026 – Phase 1: SEC N-PORT importieren (Claude, Auftrag Jonas)

### D-054 N-PORT als eigener, geprüfter Bestand im Update-System
- **Entscheid (Jonas: Zustimmung zum Download, «starte Phase 1»):** `2026q3_nport.zip`
  (462'371'568 Bytes, sec.gov) liegt unverändert in
  `raw/external/sec_nport/2026q3/` mit Begleitdatei (SHA-256). Das Update-System
  (`nport-update`, eigene Datenbank `processed/nport.sqlite`) ruft nichts ab, sondern liest
  die lokal geladenen Quartalsarchive. Neue Quartale lädt nur `nport-download <Quartal>
  --confirm`; ohne `--confirm` nennt der Befehl Datei, Quelle und Grösse.
- **Lesen:** direkt aus dem ZIP, nichts entpackt. Jede Zeile wird mit Pydantic geprüft
  (`entities/nport.py`). Ungültige Zeilen (falsche Spaltenzahl, unlesbare Zahl oder
  Datumsangabe, ungültige Accession-Nummer, Position zu unbekannter Meldung) werden
  abgelehnt und je Grund mit Beispielzeilen gezählt (`nport_load_stats`, Warnungen im
  `update_runs`-Eintrag). Über 1 % abgelehnte Zeilen in einer Tabelle (unsere Setzung) oder
  ein verletzter Primärschlüssel der SEC-Readme → ganzer Datenstand abgelehnt, alter Stand
  bleibt aktiv.
- **Zwei Durchgänge:** Erst prüfen (nichts gespeichert), dann schreiben in der Transaktion der
  Aktivierung; weichen die Zählungen des zweiten Durchgangs ab, Rollback. Grund: 5.6 Mio.
  Positionen je Quartal passen nicht als Objekte in den Speicher, und die Prüfung muss vor
  dem Schreiben feststehen.
- **Kennungen:** Gemeldeter Wert bleibt unverändert (`*_reported`); die geprüfte Kennung
  steht nur bei gültiger Prüfziffer daneben, sonst ein Status (`missing`, `not_applicable`,
  `invalid_format`, `invalid_checksum`). Eine Position erhält eine ISIN nur, wenn ihre
  Kennungszeilen genau eine gültige ISIN nennen; mehrere verschiedene = `multiple`, offen.
- **Fondsschlüssel:** Serien-ID; ohne Serie die CIK des Registranten, aber nur wenn derselbe
  Registrant nirgends mit Serie meldet. Anlass: Im ersten Lauf (Regel «ohne Serie keine
  Zuordnung») fielen 737 Meldungen von 709 Registranten mit 1.17 Mio. Positionen (21 %)
  aus der Auswahl; keiner dieser Registranten meldet auch mit Serie. Regelversion
  `2026-11-15.2` (`RULE_VERSION`, steht im Manifest: Regeländerung = neuer Datenstand).
- **Auswahl je Fonds (unsere Regel, nicht von der SEC):** Je Fonds und Stichtag gilt
  die zuletzt eingereichte Meldung (Berichtigungen ersetzen das Original); gleiches
  spätestes Einreichdatum = unentschieden, keine Wahl nach Nummernfolge. Je Fonds ist der
  jüngste Stichtag «current». Ob eine Berichtigung immer die ganze Meldung ersetzt, steht
  nicht in der Readme und ist nicht verifiziert.
- **Messwerte** im Qualitätsbericht (`processed/nport/quality_report.json`), alle per SQL aus
  dem aktiven Stand, Zähler und Nenner zusammen. «LEI aktiv bei GLEIF» seit 16.11.2026
  gemessen (D-055).
- **Lizenz:** wie die übrigen SEC-Quellen (öffentliche Information, Weiterverbreitung ohne
  Erlaubnis; gewerbliche Nutzung nicht wörtlich genannt). Interne Messung; Veröffentlichung
  erst nach schriftlicher Bestätigung (Roadmap Phase 5).

## 15.11.2026 – Phase 0: Fundament für den weltweiten Bestand (Claude, Auftrag Jonas)

### D-053 Echte Pilotergebnisse nie in versionierte Dateien
- **Entscheid (Jonas, vor dem ersten Push der Pilotarbeit):** Ergebnisse mit Fonds- oder
  Firmennamen bleiben lokal (`C:\TransparenzDaten\notizen\`). Die öffentliche Dokumentation
  nennt Methode und Messwerte ohne Namen. Die bis dahin lokalen Commits wurden vor dem Push zu
  einem Commit zusammengefasst, damit die Namen nie auf GitHub lagen; die vollständigen
  Fassungen sind lokal gesichert.
- **Begründung:** Lizenzen von FI und EU-Emissionshandel sind für eine Veröffentlichung nicht
  bestätigt (D-041), und die Bewertung «Konflikt mit Profil» über reale Fonds und Unternehmen
  wird nicht ungeprüft publiziert. Fondsnamen als Konfiguration im Code (Entwicklungs- und
  Testfonds) bleiben, weil sie ohne Ergebnis nichts aussagen.

### D-052 Herkunft jeder Eingabedatei wird bei jedem Lauf geprüft
- **Entscheid:** Vor der Verwendung wird jede Rohdatei neu gehasht und mit der Prüfsumme in
  ihrer Begleitdatei (`*.metadata.json`, `source.metadata.json`) verglichen; entpackte Dateien
  über CRC-32 des Archiveintrags. Abweichung = Abbruch. Ohne Begleitdatei steht «nicht erfasst»,
  nichts wird ergänzt. Der Bericht führt jede Eingabe mit Pfad, Grösse, SHA-256, Lizenzangabe
  und Abrufdatum (`services/provenance.py`).
- **Begründung:** Für ein Produkt muss jede Aussage bis zur Originaldatei zurückverfolgbar sein,
  und veränderte Rohdaten dürfen nie still in ein Ergebnis einfliessen.

### D-051 Pilot als Paketmodule; Umbau nur mit Vergleichslauf
- **Entscheid:** Die Logik des Pilot-Skripts liegt in Paketmodulen (Quellen in `ingestion/`,
  Kette und Messung in `services/`, Bericht in `reports/`, Anzeigetexte in
  `entities/labels.py`). Das Skript ist nur noch Befehlszeile. Jeder Umbau der Kette wird mit
  `scripts/pilot_regression.py` geprüft: sechs Fonds offline vom eingefrorenen Eingang,
  vorher/nachher ohne Abweichung.
- **Begründung:** N-PORT und weitere Fondsquellen brauchen dieselbe Kette; ein 2'700-Zeilen-
  Skript ist dafür weder testbar noch wiederverwendbar.
- **Alternative:** neu schreiben – verworfen, weil das Ergebnisse unbemerkt verändern kann.
  Die Funktionen wurden unverändert verschoben (maschinell, mit Abhängigkeitsprüfung).

### D-050 Datenordner ausserhalb OneDrive
- **Entscheid (Jonas):** Grosse Daten liegen in `C:\TransparenzDaten` (`TRANSPARENZ_DATA_DIR`
  in `.env`); versionierte Beispiel- und Abfragedateien bleiben im Projekt. 14 alte Schweizer
  Exportstände gelöscht (neueste zwei behalten), rund 6 GB frei.
- **Umsetzung:** einzige Stelle `settings.local_data_dir()`; alte Pfadangaben (`data\…`,
  absolute Pfade in Datenbanken) findet `resolve_data_path()`. Tests leiten den Datenordner
  immer in einen Wegwerfordner um.

### D-049 Keine Einzelfallarbeit für Jonas; Referenz aus unabhängigen Kennungen
- **Entscheid (Jonas):** Jonas beantwortet keine Zuordnungsfälle und keine langen Listen von
  Detailregeln. Referenzen für die Präzisionsmessung kommen aus unabhängigen Kennungsquellen
  (geplant: vom Fonds gemeldete Emittenten-LEI in SEC N-PORT, Konsens mehrerer Meldender).
  Bewertungsregeln setzen wir mit begründetem Standard als unsere Bewertungsentscheidung.
  Jonas entscheidet Grundsätzliches: Kosten, Lizenzen, Downloads, Veröffentlichung.
- **Folge:** Die Frageliste der acht Abweichungen (`mapping_disputes.json`) ist keine Aufgabe
  mehr für Jonas; sie bleibt als Prüfmaterial. Plan: `docs/ROADMAP.md`.

## 14.11.2026 – Beziehungstypen, automatische Zuordnung, Kategorien (Claude, Auftrag Jonas)

### D-048 Korruption: Wirkungsdauer mit Beginn, Folgen und Abhilfe (Vorschlag)
- **Regel (criteria.toml, `expiry_reason`):** Beginn mit dem Abschluss des Verfahrens
  (Veröffentlichung des Entscheids) oder dem späteren Ende der Tat (`event_date`). Dauer fünf
  Jahre. Fortbestehende Folgen (`consequences_until`: Auflagen, Aufsicht, Sperre) verlängern
  bis zu ihrem Ende. Eine von Gericht oder Behörde bestätigte Abhilfe (Beleg der Art
  «abhilfe») verkürzt auf mindestens drei Jahre, nie vor das Abhilfedatum oder das Ende der
  Folgen. Vom Unternehmen selbst gemeldete Abhilfe verkürzt nichts.
- **Begründung der fünf Jahre:** Das EU-Vergaberecht schliesst ein rechtskräftig wegen
  Bestechung verurteiltes Unternehmen höchstens fünf Jahre ab der Verurteilung von
  öffentlichen Aufträgen aus und lässt bei nachgewiesener Selbstreinigung früher wieder zu
  (Richtlinie 2014/24/EU, Art. 57). Der Wortlaut war automatisch nicht abrufbar (EUR-Lex lieferte
  eine leere Antwort) und ist vor einer Veröffentlichung am Original nachzulesen. Die drei Jahre
  bei Abhilfe sind unsere Setzung, keine Übernahme einer Quelle.
- **Grenze:** Abhilfebelege sind nicht mit einem bestimmten Fall verknüpft; jede bestätigte
  Abhilfe zum selben Kriterium nach Beginn der Wirkung zählt. Vorschlag, von Jonas zu bestätigen.

### D-047 Kategorien je Beleg in der Engine; additive Spalten statt Migrationen
- **Entscheid:** Ein Beleg trägt eine Kategorie (`category`, Schlüssel aus criteria.toml).
  Hat ein Kriterium Kategorien mit unterschiedlicher Wirkung, löst nur eine Kategorie mit
  `effect = "conflict"` einen Konflikt aus; ohne Kategorie bleibt die Wirkung offen (kein
  Konflikt, Hinweis). Die Engine prüft alle sicher zugeordneten Belege, nicht nur den
  stärksten, damit ein Dual-Use-Beleg keinen Kernwaffen-Beleg verdeckt.
- **Waffen:** zwei neue Kategorien mit Wirkung «gesondert»: Handel mit zivilen Schusswaffen
  (Vorschlag) und Dual-Use ohne belegte Waffenbestimmung (bisher schon als Abgrenzung
  entschieden).
- **Schema:** zwei neue, leer erlaubte Spalten (`category`, `consequences_until`).
  `init_db` trägt fehlende leer erlaubte Spalten in bestehenden Datenbanken nach
  (`add_missing_columns`); nicht leer erlaubte neue Spalten brechen ab. Ersetzt für additive
  Änderungen die Regel «keine Schemaänderung ohne Migrationen» (D-004). Fiktive Beispielbelege
  tragen jetzt Kategorien (BEL-016 bewusst ohne, als Beispiel).
- **Überblick:** Der Pilotbericht zeigt je Kriterium getrennt: Regel definiert,
  implementiert, getestet (mit fiktiven Daten), mit freigegebenen Daten verbunden, am Fonds
  geprüft. `data_status` je Kriterium in criteria.toml.

### D-046 Automatische Zuordnung ohne Einzelfallfreigabe, mit gemessener Präzision
- **Entscheid (Auftrag Jonas):** Hohe nachgewiesene Zuverlässigkeit ohne verpflichtende
  manuelle Freigabe im normalen Betrieb. Der Entscheid-Speicher bleibt für Korrekturen und
  Referenzfälle.
- **Verfahren:** (1) ISIN → Wikidata → LEI → GLEIF (bisher). (2) Registernummer: Wikidata nennt
  OpenCorporates-Nummer, australische ACN/ABN, japanische Unternehmensnummer oder
  neuseeländische NZBN; GLEIF führt genau einen aktiven Rechtsträger mit dieser Nummer in
  derselben Rechtsordnung → automatisch (Kennung). (3) GLEIF-Namenssuche mit Sitzland:
  normalisierter Name gleich (nicht ähnlich), Sitz im Land der ISIN oder laut Fondsmeldung,
  aktiv, kein Fonds und keine Zweigniederlassung, eindeutig; bei Gleichnamigen nur die
  GLEIF-Mutter der übrigen. (4) Zwei unabhängige Wege mit demselben LEI lösen Mehrdeutigkeit
  und Namensabweichung auf.
- **Freigabe der Namenssuche:** nur wenn an **unabhängigen** Referenzfällen (Positionen, deren
  LEI über Wikidata-Kennung oder menschlichen Entscheid feststeht; nie über die Namenssuche
  selbst) mindestens 100 Ergebnisse vorliegen und die untere einseitige 95-%-Grenze der
  Präzision (Clopper-Pearson) mindestens 97 % beträgt. Unabhängig heisst: aus einem Fonds, an
  dessen Fehlern die Regeln nicht angepasst wurden, und mit einer ISIN, die in keinem
  Entwicklungsfonds vorkommt (`DEVELOPMENT_FUNDS`, `RULE_VERSION` in entity_matching.py).
  Jede Regeländerung erhöht die Version und macht den betroffenen Fonds zum Entwicklungsfonds.
- **Vorgehen und Ergebnis am 14.11.:** Die Regeln wurden an den Fehlern der zwei
  Entwicklungsfonds verbessert (Rechtsformen «Public Limited Company», «S.p.A.», «A/S»,
  Kurzformen in Klammern, Länderprüfung bei Registernummern). Erst danach, ohne weitere
  Anpassung, lief ein dritter Fonds als Test. Ergebnis dort: 60 von 61 richtig, untere
  Grenze 92.5 %, weniger als 100 Fälle → **nicht freigegeben**. Die Namensvorschläge bleiben
  offen und stehen in der freiwilligen Frageliste. Zahlen im LOG 14.11.2026.
- **Weitere Testfonds (Auftrag Jonas «Ja, weitere Fonds», 14.11.):** Messregel vorher ergänzt
  (dieselbe ISIN zählt in Testfonds nur einmal), dann ohne Regeländerung drei weitere
  Testfonds gerechnet (Schwellenländer, Asien, Nordeuropa).
  Unabhängig zusammen mit dem ersten Testfonds: 196 von 201 richtig (97.5 %), untere Grenze 94.8 % →
  **weiterhin nicht freigegeben**. Bei mindestens drei der fünf Abweichungen liegt die
  Namenssuche richtig und die Wikidata-Referenz falsch (LEI einer Tochter, einer
  Landesgesellschaft bzw. der alten Gesellschaft); offen sind zwei Fälle (Referenz-LEI bei
  GLEIF nicht gefunden; zwei gleichnamige GLEIF-Einträge).
- **Korrektur der Referenz nur durch einen Menschen:** Alle Abweichungen stehen mit beiden
  Kandidaten in `mapping_disputes.json` (`review_mapping.py --queue …`). Antworten werden
  Referenzfälle der Quelle «Entscheid»; die Messung rechnet sich beim nächsten Lauf neu. Wir
  zählen unsere eigene Einschätzung nie als Referenz. Rechnerisch: Mit drei korrigierten
  Referenzen läge die untere Grenze knapp unter, mit vier knapp über 97 %.
- **Registernummern:** GLEIF sucht exakt; deshalb werden die Schreibweisen der Register
  mitgesucht (australische ACN in Dreiergruppen, japanische Nummer zwölfstellig mit
  Bindestrichen). Registernummern wirken wie der LEI ohne Freigabe; ihre gemessene Präzision
  wird trotzdem ausgewiesen (Wikidata kann eine falsche Nummer tragen, z. B. die einer Tochter).
- **Präzision ≠ Abdeckung:** Die bisherige Angabe «80.42 %» ist Abdeckung (Fondsgewicht mit
  Zuordnung), keine Genauigkeit. Beide werden getrennt ausgewiesen.
- **Ehrliche Grenze:** Die Referenz ist selbst nicht von Hand geprüft (Wikidata-Kennung plus
  GLEIF-Namenskontrolle). Abweichungen werden je Fall gezeigt. Menschliche Entscheide gehen
  allem vor und verbessern die Referenz.
- **Ersetzt** in D-042 die Regel «Name gültig erst durch menschlichen Entscheid».

### D-045 Beziehungstypen statt «jede Beteiligung»
- **Befund:** Die vielen Kohle- und Expansionstreffer bei Banken und Vermögensverwaltern
  stammen aus GEM-Besitzketten über Verwahrbanken und Nominee-Gesellschaften, Fonds- und
  Pensionsverwalter (Infrastrukturfonds, Pensionskassen) und gemeldete Aktienbestände von
  unter 10 % an kotierten Versorgern. GEM zählt nach eigener Methodik solche Bestände als Beteiligung, sagt aber
  nicht, auf wessen Rechnung.
- **Entscheid:** Jede Kette wird genau einem Beziehungstyp zugeordnet (services/ownership.py):
  Verwahrung → Vermögensverwaltung → Finanzbeteiligung eines Finanzinstituts mit ungeklärter
  Rechnung (unter 20 % an einer laut GEM kotierten Gesellschaft; Finanzinstitut laut
  Wikidata-Branche) → sonst Eigentum auf eigene Rechnung. Nur Eigentum auf eigene Rechnung
  mit belegtem Anteil löst bei Kohle und fossiler Expansion einen Konflikt aus. Finanzierung,
  Betrieb und Lieferverträge sind eigene Typen mit eigener (offener) Regel und entstehen nie
  aus einer Besitzkette. Profil 1.1.
- **Kategorien angewendet:** Kohle (Förderung/Verstromung) und Expansion
  (Förderung/Transport/LNG/Kraftwerke) werten die Wirkung der Kategorie aus criteria.toml aus.
- **Schwelle:** bleibt 0 % («jede belegte Beteiligung auf eigene Rechnung»). Der Bericht zeigt
  die Wirkung von 5, 10, 20 und 50 % zur Entscheidung; angewendet wird keine.
- **Notstrom und Eigenbedarf:** zählen als neue Kraftwerkskapazität, werden aber ausgewiesen
  (offene Frage im Kriterienmodell). Anlass im Pilot: Bei einem Technologiekonzern sind laut
  GEM-Anlagenliste die neuen Einheiten überwiegend Dieselaggregate (teils ausdrücklich
  Notstrom) und ein Gaskraftwerk, alle zur Eigenversorgung von Rechenzentren.
- **Grenze:** Verwahrung und Vermögensverwaltung werden an Begriffen im Namen eines
  Kettenglieds erkannt (nur Einordnung bereits über Kennungen zugeordneter Ketten). Branche
  unbekannt → keine Annahme zu Gunsten des Unternehmens. Zwei Fehlgriffe der Muster wurden am
  zweiten Fonds gefunden und behoben («Pte Ltd» ist die Rechtsform in Singapur; kotierte
  «… Infrastructure Partners LP» sind keine Verwalter). Ketten über Vermögensverwalter ohne
  erkennbaren Namen bleiben «eigene Rechnung»: Bei einer Depotbank hängt ein verbleibender
  Kohlekonflikt an einer solchen Kette (über zwei Vermögensverwalter, durchgerechnet 0.07 %). Die Schwellentabelle zeigt, dass ab 5 % kein solcher Fall
  mehr zählt.

## 13.11.2026 – Kriterienmodell, Lizenzmassstab, Entscheid-Speicher (Claude, Auftrag Jonas)

### D-044 Fondsseite unabhängig von der Zahl der Kriterien
- **Entscheid:** Die Übersicht zeigt Kriterien als Zeilen (nach Thema gruppiert) und
  Belegstatus als Spalten; die Positionstabelle zeigt je Position nur die Kriterien mit Beleg
  und zählt den Rest («geprüft ohne Hinweise», «unbekannt»).
- **Grund:** Mit zwölf Kriterien als Spalten war die Seite nicht mehr lesbar.
- **Geprüft:** im Browser bei 1024 px und 375 px, dunkel; Seite läuft nicht über, breite
  Tabellen scrollen im Rahmen, Kriterienspalte bleibt stehen.

### D-043 Kriterienmodell Schema 2 mit Startprofil «streng» 1.0
- **Entscheid (Jonas):** `criteria.toml` ist die zentrale, versionierte Grundlage. Zwölf aktive
  Kriterien: Kohle, fossile Expansion, Waffen, Zwangs-/Kinderarbeit, Entwaldung, Korruption,
  Biodiversität und Ökosysteme, Wasser und Meeresressourcen, Umweltverschmutzung und
  gefährliche Stoffe, Ressourcen/Abfall/Kreislaufwirtschaft, Arbeitsrechte und Arbeitsschutz,
  Menschenrechte und Landrechte. Emissionen sind Kennzahlen ohne Ausschlusswert. Sanktionen
  sind Belege mit Sanktionsgrund, kein Kriterium.
- **Startprofil (ausdrücklich unsere Bewertungsentscheidung):** Kohle: jede bestätigte
  Eigentumsbeteiligung an aktiver Förderung oder Verstromung ist ein Konflikt; stillgelegte
  Anlagen gesondert. Fossile Expansion: neue Förder-, Transport-, LNG- und
  Kraftwerkskapazität; Ankündigung, Genehmigung, Bau und Betrieb getrennt; Instandhaltung
  gesondert. Verhaltenskriterien: nur bestätigte Feststellungen sind Konflikt.
- **Umsetzung:** Tätigkeitskriterien (Kohle, Expansion, Waffen) zählen «dokumentiert» und
  «festgestellt», Verhaltenskriterien nur «festgestellt». Die Engine setzt je Kriterium
  `profile_conflict`; bei Korruption endet die Wirkung fünf Jahre nach dem Beleg (Vorschlag).
  Schlüssel umbenannt: `oel_gas_expansion` → `fossile_expansion`, `geaechtete_waffen` →
  `waffen` (geächtete Waffen sind jetzt eine Kategorie). Fiktive Beispieldaten neu erzeugt.
- **Als Vorschlag markiert, nicht entschieden:** Ausschlüsse je Waffenkategorie (alle vier als
  Konflikt, Handel mit zivilen Schusswaffen gesondert), Konfliktregeln der sechs neueren
  Kriterien, Wirkungsdauer Korruption, vier Zusatzkriterien (inaktiv).
- **Auslegung, die Jonas prüfen soll:** «Bestätigte Beteiligung» = Stufen Kontrolle, bedeutend
  und klein laut GEM. Unbekannter Anteil und Treuhand zählen nicht. Kohleprojekte im Ausbau
  zählen als aktive Kohle. Folge am Pilotfonds: Banken und Vermögensverwalter mit kleinen
  Portfolio-Anteilen sind Konflikte.
- **Nicht umgesetzt:** Kategorie je Beleg in der Engine (braucht ein Feld im Belegschema und
  damit Migrationen, D-004); eine API gibt es nicht.
- **Verhältnis zu früher:** ersetzt D-011 (Schwellenwerte offen) für Kohle und beantwortet
  die offene Definition von «Expansion» aus D-040. Die Mission «keine Urteile» wird
  präzisiert: Belege bleiben quellenbasiert, die Bewertung ist getrennt und benannt.

### D-042 Namen nur als Vorschlag; menschliche Entscheide werden gespeichert und wiederverwendet
- **Entscheid (Jonas):** Ziel ist ein weitgehend automatisches Werkzeug. Bei unsicheren
  Zuordnungen entscheidet ein Mensch einmal Ja oder Nein; danach läuft es automatisch weiter.
- **Umsetzung:** `data/review/mapping_decisions.csv` (ISIN, LEI, ja/nein, Datum, Signal).
  Nur ergänzend; der jüngste Entscheid je Paar gilt; zwei «ja» für eine ISIN werden
  abgelehnt. «Ja» löst Mehrdeutigkeit und Namensabweichung auf und kann ein Unternehmen
  liefern, das Wikidata nicht kennt. «Nein» streicht den Kandidaten. Ein Entscheid kann
  keinen LEI gültig machen, den GLEIF nicht führt.
- **«Lernen» ohne Blackbox:** Die Statistik je Signal zählt Ja und Nein. Eine automatische
  Regel entsteht erst, wenn ein Signal oft genug und immer gleich entschieden wurde, und dann
  als ausdrücklicher Entscheid in dieser Datei. Kein statistisches Modell.
- **Ersetzt** die absolute Regel «keine Namensfusion» (D-013): Namen bleiben nie ein
  automatischer Schlüssel, dürfen aber Vorschläge erzeugen. Das öffnet Quellen, die
  Unternehmen nur mit Namen nennen (US-Behördendaten).
- **Ehrliche Grenze:** «100 % richtig ohne Prüfung» gibt es nicht. Automatisch bestätigt wird
  nur, wo Kennungen übereinstimmen; der Rest ist eine kurze Frageliste.

### D-041 Lizenzmassstab: nur ausdrücklich gewerblich freigegebene Quellen
- **Entscheid (Jonas):** Es wird nur verwendet, was nachweislich gewerblich genutzt werden
  darf, damit ein späterer Verkauf keine Rechtsprobleme auslöst.
- **Massstab:** benannte Lizenz oder ausdrückliche Gemeinfreiheit an der Originalseite, die
  gewerbliche Nutzung, Speicherung, Ableitung und Weitergabe erlaubt. Auslegungen genügen
  nicht.
- **Folge für bestehende Pilotquellen (nicht geändert, aber zu klären):** FI Schweden nennt
  «kommerziell» nicht wörtlich; beim EU-Emissionshandel ist die CC-BY-Regel der Kommission
  eine Auslegung. Beide vor einer Veröffentlichung schriftlich bestätigen lassen.
- **Recherche:** rund 40 Quellen, Ergebnis in `docs/DATA_SOURCES.md` (oben).

## 12.11.2026 – GEM-Beteiligungen im Pilot (Claude, Auftrag Jonas)

### D-040 Beteiligungen gestuft zeigen, auch indirekte; Kohle als erstes Kriterium mit Quelle
- **Entscheid (Jonas):** Auch kleine und indirekte Beteiligungen sind wichtig und werden
  gezeigt. Umsetzung: Jede Beteiligung an einer Anlage steht in einer Stufe nach dem von GEM
  durchgerechneten Anteil: Kontrolle (≥ 50 %), bedeutende Beteiligung (20–50 %), kleine
  Beteiligung (< 20 %), Anteil unbekannt, treuhänderisch gehalten. Stufen werden nie
  zusammengezählt; jede Angabe zeigt die Besitzkette mit Prozenten.
- **Treuhand:** Ketten über Verwahr- oder Nominee-Gesellschaften («Nominees», «Custody»,
  «Securities Clearing», «Depository») gelten nicht als Beteiligung. GEM hat dafür kein Feld;
  die Namensregel dient nur der Beschriftung, nie der Zuordnung. Stichprobe 12.11.2026: Die
  ausgelösten Namen sind echte Verwahrstellen (Nominee-Gesellschaften von Banken und
  Zentralverwahrer).
- **Zuordnung:** Fondsposition → LEI (widerspruchsfrei, D-039) → GEM-Entität nur über die
  LEI-Spalte von GEM selbst (CC BY 4.0). Die GLEIF-GEM-Datei (Lizenz unbenannt) wird nicht
  verwendet. GEMs Besitzketten gelten als Quelle («laut GEM»), unabhängig von der
  GLEIF-Bestätigungsregel (D-012), weil GEM jede Beteiligung mit Quellen-URL recherchiert.
- **Kriterium Kohle:** «Belegt laut GEM (Teilabdeckung)» je Position mit der stärksten Stufe
  an aktiven Kohleanlagen (in Betrieb oder im Ausbau; Kraftwerke ab 30 MW, Minen). Fehlt die
  Firma bei GEM, heisst das «keine Hinweise in GEM», nur für widerspruchsfrei zugeordnete
  Positionen; sonst «unbekannt» (D-014). Schwellenwert weiterhin offen (D-011).
- **Öl-/Gas-Expansion:** bleibt «unbekannt», weil GEM Eigentümer von Öl-/Gasfeldern nur mit
  Namen nennt. Gaskraftwerke, LNG-Terminals und Pipelines erscheinen als Fakten im Bericht,
  nicht als Kriterienbeleg, bis Jonas die Definition von «Expansion» festlegt.
- **Alternativen:** nur Mehrheitsbesitz zeigen (verworfen: Jonas will indirekte Beteiligungen
  sehen); alle Anteile ungestuft (verworfen: Banken erschienen als Kohlebetreiber).

## 11.11.2026 – Verständlicher Pilotbericht (Claude, Auftrag Jonas)

### D-039 Bestätigte Abdeckung, separate Fälle und zeitliche Zurechnung im Pilotbericht
- **Zuordnungsstufen:** «Bestätigte Abdeckung» heisst: genau ein Wikidata-Eintrag, genau ein
  LEI, LEI bei GLEIF vorhanden und der Positionsname teilt mit dem GLEIF-Rechtsnamen oder
  einem bei GLEIF geführten früheren, anderssprachigen oder transliterierten Namen ein
  nicht allgemeines Wort. LEI nicht erneuert (LAPSED) bleibt bestätigt, wird aber angezeigt.
  Keine Zuordnung ist von Hand geprüft; das steht im Bericht.
- **Identitätskonflikte separat:** Passen Kontoinhaber im Register und GLEIF-Namen des LEI
  nicht zusammen, zählt der Beleg nicht und steht in einem eigenen Abschnitt.
  Gleiches gilt für Belege von Positionen, deren Zuordnung ein Prüffall ist.
- **Zeitliche Zurechnung:** Emissionen einer Tochter zählen nur für Kalenderjahre, in denen
  die Beziehung laut GLEIF («RELATIONSHIP_PERIOD») das ganze Jahr bestand, und nur, wenn sie
  am Fondsstichtag gültig war. Fällt der gemeldete Beginn auf den Tag der LEI-Registrierung,
  wird das angezeigt, aber nicht zu Gunsten einer Zurechnung ausgelegt.
- **Ausschlusskriterien getrennt:** Alle Kriterien aus `criteria.toml` erscheinen mit Status
  «Unbekannt (keine Datenabdeckung)» (D-014). Emissionsmengen sind ausdrücklich kein Beleg
  für ein Kriterium.
- **Bericht:** HTML für Laien (`scripts/templates/pilot_report.html.j2`, Gestaltung der
  Website übernommen) plus technische Markdown-Fassung. Lokal, Git-ignoriert, nicht publiziert.
- **Alternativen:** Namensabweichungen ohne GLEIF-Altnamen als Konflikt werten (verworfen:
  hätte Umbenennungen wie Anthem → Elevance als Fehler gezeigt); Zurechnung ab dem Jahr des
  Beginns statt ab dem ersten vollen Jahr (verworfen: rechnet Teiljahre zu).

## 11.11.2026 – Zweite Belegquelle im Pilot (Claude, Auftrag Jonas «Mach eigenständig weiter»)

### D-038 EU-Emissionshandelsregister als zweite Belegquelle, nur über LEI
- **Entscheid:** Das Pilot-Skript liest die öffentlichen Tagesauszüge der Union Registry
  (`--ets-dir`) und die GLEIF-Beziehungsdatei (`--gleif-rr`) lokal. Verknüpfung allein über
  den prüfzifferngültigen LEI des Kontoinhabers; Tochterbelege nur über aktiv, veröffentlicht
  und vollständig bestätigte Beziehungen (D-012). Ein Beleg entsteht nur bei mindestens einem
  verifizierten Jahreswert. Sachverhaltsart `emission_trading_verified_not_violation`.
- **Namensvergleich nur als Warnung:** Teilen Kontoinhabername und GLEIF-Rechtsname kein Wort,
  wird der Beleg als «Sichtprüfung nötig» markiert, aber weder entfernt noch umgeordnet (keine
  Namensfusion, D-013).
- **Begründung:** Einzige geprüfte Belegquelle ausserhalb der Schweiz mit harter
  Unternehmenskennung. EEA-Industrieemissionen nennen Unternehmen nur als Namen.
- **Bewusst offen:** Lizenz ist eine Auslegung (CC BY 4.0 der Kommissionsseite, keine Angabe
  an den Dateien). Daher nur lokal; vor jeder Veröffentlichung klären. Registernummer-Brücke
  (98 % der Zeilen) nicht gebaut. Nicht im Update-System, nicht im Screening.
- **Alternativen:** EEA-Industrieemissionen über ETS-Kennung als Brücke (später möglich);
  Namensabgleich (verworfen, D-013); GLEIF-API für jede Beziehung (zu viele Abfragen für
  3'141 Register-LEIs, daher lokale Golden Copy).

## 11.11.2026 – Datenversorgung und erster echter Fonds (Claude, Auftrag Jonas)

### D-037 Erster echter Fonds als lokales Pilot-Skript mit FI-Positionen
- **Entscheid (Umsetzung Claude, Produktentscheid Jonas offen):** Die Kette Position →
  Unternehmen → Beleg wird zuerst als eigenständiges Skript `scripts/pilot_fund_chain.py`
  geprüft, nicht im Screening und nicht auf der Website. Positionen aus dem Register
  «Fondinnehav» der schwedischen Finanzaufsicht FI; Zuordnung nur über exakte ISIN; Belege
  über LEI/UID. Belege von Tochterfirmen zählen nur bei einer von GLEIF als aktiv,
  veröffentlicht und vollständig bestätigt geführten Beziehung (dieselbe Regel wie D-012/D-026).
- **Begründung:** FI ist die einzige gefundene EU-Quelle mit vollständigen UCITS-Positionen
  und ausdrücklicher Freigabe zur Weiterverwendung. Ein Skript beweist die Kette, ohne das
  Screening-Schema (keine Migrationen) oder die Lizenzsperre vorschnell zu erweitern.
- **Bewusst offen:** FI steht noch nicht in `sources.toml`; vor einer Aufnahme muss Jonas
  entscheiden, ob schwedische Fonds im Produkt erscheinen sollen und ob die Freigabe ohne
  wörtliches «kommerziell» genügt. Produkteinstieg für Schweizer Fonds (Nutzer-Upload) ist
  ein Vorschlag, kein Entscheid.
- **Alternativen:** SEC N-PORT als Pilot (D-027, von Jonas vorerst abgelehnt);
  Jahresberichte von Schweizer Anbietern extrahieren (Rechte ungeklärt, Swiss Fund Data
  verlangt schriftliche Zustimmung); kommerzielle API (Anzeige nach aussen erst ab
  Enterprise-Vertrag bzw. gar nicht erlaubt).

## 11.11.2026 – Globalen Wikidata-Rohbestand durchsuchbar machen (Claude, Auftrag Jonas)

### D-036 Eigenes, drittes Modul statt Einbau in Swiss- oder Market-Katalog
- **Entscheid:** `services/global_candidates.py` + `reports/global_candidates.py` als eigenes
  Modul, eigener Ordner `data/processed/global_candidates/`, eigene CLI-Befehle
  (`global-candidates-build`/`-search`) statt Einbau in `swiss_foundation.py`/`swiss.sqlite`
  oder `market_catalog.py`/`markets.sqlite`.
- **Begründung:** `swiss.sqlite` ist laut CLAUDE.md explizit das Schweizer Fundament
  (Länderbezug im Namen/Architektur); `markets.sqlite`/`MarketObservation` ist fest auf das
  SEC-Datenschema (CIK/Series/Class) zugeschnitten. Der globale Wikidata-Bestand hat ein
  eigenes, einfacheres Schema (Item/Name/Börse/Ticker, kein ISIN, kein Fondsschema) und eine
  andere Vertrauensstufe (ein Wikidata-Statement pro Zeile) – passt in keines der beiden
  bestehenden Schemata, ohne sie zu verbiegen.
- **Börsenlabel-Cache bleibt real und damit git-ignoriert**, nicht im Repo committet: laut
  `.gitignore`-Kommentar «nur fiktive Beispieldaten gehören ins Repo»; `data/processed/*` ist
  bereits ignoriert, also passt `data/processed/global_candidates/exchange_labels.json` ohne
  Ausnahmeregel dorthin. Ursprünglich unter `data/reference/` angelegt (würde committet) –
  verworfen und nach `data/processed/` verschoben.
- **Keine Fusion über Namen/Ticker, keine ISIN-Ergänzung:** explizite Vorgabe von Jonas,
  passt zum bestehenden Grundsatz im Schweizer Fundament (`resolve_companies`: nur exakte
  Kennungen verschmelzen, Namensgleichheit nur als Prüfhinweis). Gleicher Mechanismus
  (`normalize_company_name`) für die «mögliche Dubletten»-Liste wiederverwendet statt neu
  erfunden.
- **Alternativen:** Börsen-Land live bei jeder Suche von Wikidata nachschlagen – verworfen,
  würde die Suche online-abhängig machen (Vorgabe: lokal durchsuchbar); stattdessen einmaliger
  Cache, nur fehlende/erzwungene IDs werden nachgeladen. CVM-Brasilien direkt mit einbauen –
  verworfen, Jonas wollte es vorerst getrennt halten.

## 08.11.2026 – Firmenabdeckung empirisch prüfen (Codex, Auftrag Jonas)

### D-035 Firmenhinweis, Heimatlisting und bestätigtes Wertpapier getrennt zählen
- 100 Zufallsziehungen aus explizitem, kuratiertem 120er-Pool in zehn Märkten, Seed 20261108.
  Explorativ, keine repräsentative Weltquote. Ergebnis: 57 Firmenhinweise / 43 ohne Treffer;
  50 SEC, 10 Schweizer Kandidaten, 3 Überschneidungen.
- Tochter-/Namensfirmen manuell verworfen; Daimler/Mercedes-Benz-Umbenennung mit Emittentenbeleg
  berücksichtigt. Namensvarianten nur im Audit, keine automatische Produktfusion.
- Alle 10'419 SEC-Originaltupel gegen Export geprüft: exakt gleich. Fehlende Quellenabdeckung,
  kein hier belegter Importverlust. Keine neuen Produktionsquellen aktiviert.
- Einzelbefunde, Grenzen und Ausbauwege: `COVERAGE_AUDIT_100.md`; reproduzierbarer Abgleich:
  `scripts/company_coverage_probe.py`. Prüfdaten lokal unter `data/processed/coverage_audit/`.

Format: Datum · Entscheid · Begründung · Alternativen. Neueste zuoberst innerhalb einer Session.

## 11.11.2026 – KI-Transparenz auf GitHub (Auftrag Jonas)

### D-035b KI-Beiträge, Skills und Werkzeuge mit Belegstatus dokumentieren
- **Hinweis (15.11.2026):** Die Nummer D-035 wurde auf zwei Ständen parallel vergeben; dieser
  Entscheid heisst deshalb D-035b. Inhalt unverändert.
- **Entscheid:** Sichtbare Übersicht im README, Details in `docs/AI_USAGE.md`.
  Künftige Sessions erfassen tatsächlich verwendete Skills und wesentliche Tools im Sessionlog.
- **Begründung:** Verwendete Assistenten und Arbeitsweisen sollen nachvollziehbar sein.
  Verfügbare Skills sind kein Nutzungsnachweis; fehlende historische Angaben bleiben offen.
- **Alternative:** Alle verfügbaren Skills auflisten – verworfen, da dies tatsächliche Nutzung
  vortäuschen könnte. Keine automatische Telemetrie oder neue Laufzeitabhängigkeit.

## 08.11.2026 – Wikidata-Wertpapierkandidaten reparieren (Claude, Auftrag Jonas)

### D-034 wikidata_ch-Bugs beheben statt als dauerhaft gesperrt dokumentieren
- **Befund:** Der dokumentierte «HTTP 403» war kein anhaltender Zugangsfehler, sondern drei
  eigene Bugs in `data/queries/wikidata_ch.sparql`/`wikidata_funds.sparql` und im globalen
  HTTP-User-Agent: (1) Q12569 (SIX Swiss Exchange in der Abfrage) ist tatsächlich der Fluss
  Loire; (2) Q927783/Q756898 (Fondsklassen) sind eine historische Person und ein Dorf; (3) die
  Abfrage scannte transitiv (`wdt:P31/wdt:P279*`) über ganz Wikidata mit `P17=Schweiz`, was den
  Abfragedienst regelmässig in Zeitüberschreitung/Bot-Policy-Sperre laufen liess; (4) der
  generische HTTP-User-Agent ohne Kontaktangabe verletzte Wikimedias Bot-Policy und wurde
  gelegentlich mit 403 beantwortet, unabhängig von der Abfrage selbst (live reproduziert: `curl`
  mit beschreibendem User-Agent erfolgreich, `httpx` mit dem alten generischen UA 403).
- **Entscheid:** Abfrage auf «SIX-notiert (korrekte QID Q661834) oder CH-ansässig mit ISIN»
  eingrenzen statt auf «alle Schweizer Unternehmen»; das hält die Abfrage bei 1–3 Sekunden statt
  Minuten/Timeout. Fondsklassen-QIDs auf Q845477 (ETF)/Q4201895 (Investmentfonds) korrigiert,
  nur direktes `P31` (kein Transitivabschluss) – im Schweizer/SIX-Zuschnitt dadurch 0 Fondstreffer
  (weltweit 19), ehrlich dokumentiert statt verschwiegen. Ticker-Symbol wird in Wikidata oft als
  *Qualifier* der Börsenangabe geführt, nicht als eigene Aussage (z. B. Roche: `P414=SIX` mit
  Qualifier `P249=ROG`, kein eigenständiges `P249`); zusätzliche `pq:P249`-Abfrage ergänzt.
  HTTP-User-Agent projektweit (GLEIF/Zefix/Wikidata) auf
  `ProjektTransparenz/0.1 (+https://github.com/Jonasbader7/Projekt-Transparenz)` umgestellt –
  die öffentliche Repo-URL, keine private Kontaktadresse, keine neue Nutzerfreigabe nötig.
  `wikidata_ch` läuft seit diesem Fix standardmässig (nicht mehr `enabled = false`).
- **Neuer Fund beim Echtlauf:** Zwei Wikidata-Items können dieselbe LEI tragen (live:
  Q292291 «AGEN Holding» und Q120635425 «Aevis Victoria SA»). Die bestehende generische
  LEI-Eindeutigkeitsprüfung (`check_entities`) hätte sonst den *gesamten* Quellenlauf verworfen.
  Nach Zefix/GLEIF-Vorbild unter Quarantäne gestellt (`identifier_conflicts`,
  `lei_shared_by_multiple_wikidata_items`), nicht die ganze Quelle abgelehnt und nicht über den
  Namen fusioniert. Ergebnis: 287 Datensätze, 293 Wertpapierkandidaten, 3 neue Konfliktgruppen.
- **Suchbarkeit:** Neuer CLI-Befehl `swiss-search` und eine eigene lokale `security_candidates.html`
  (gleiches Muster wie `reports/market_catalog.py`, aber separate Datei/Quelle) – bewusst nicht in
  den SEC-Marktkatalog oder die Screening-Website gemischt: andere Lizenzquelle, andere
  Vertrauensstufe (unverifizierter Firmenclaim statt SEC-Meldung), bestehende Architektur
  (`swiss.sqlite` getrennt von `markets.sqlite`/Demo) bleibt unverändert.
- **Alternativen:** Melting-Format (`?item ?property ?value` mit `VALUES ?property {...}`)
  beibehalten und nur die QIDs korrigieren – verworfen, da dieses Muster selbst bei bereits auf
  ~300 Posten eingegrenztem Subjekt in mehreren Live-Tests regelmässig in Zeitüberschreitung lief
  (unbound-predicate-Join scheint vom Abfrageoptimierer nicht auf die vorgefilterte
  Subjektmenge heruntergebrochen zu werden); stattdessen feste Spalten pro Eigenschaft.
  Shared-LEI-Fälle einfach verwerfen (wie ungültige Prüfziffern) – verworfen: beide Einträge
  tragen eine gültige LEI, das ist ein Quellendatenfehler, keine ungültige Kennung; Quarantäne
  mit eigenem Grund ist ehrlicher. Security-Kandidaten in den SEC-Marktkatalog einmischen –
  verworfen: andere Lizenz/Vertrauensstufe, hätte `markets.sqlite` und dessen Tests angefasst,
  ohne dass der Auftrag eine Zusammenführung der Kataloge verlangt.

## 08.11.2026 – Weltweiter Aktien-/ETF-Auftrag (Codex)

### D-033 SEC-Teilbestand als ausführbarer Katalog, Weltabdeckung offen
- Nutzer bestätigt «alle weltweit börsenkotierten Aktien und ETFs» und erlaubt die lokale
  Kontakt-E-Mail im SEC-HTTP-User-Agent. Keine Kosten, Veröffentlichung oder Push autorisiert.
- Drei separat geprüfte SEC-Quellen über den vorhandenen DataUpdateManager; neue Beobachtungstabelle
  in separater `markets.sqlite`. Öffentliches Demo-Screening bleibt beim vorhandenen Datensatz.
- Ticker-/Börsenliste liefert keine sichere Wertpapiergattung. CIK identifiziert den Registranten;
  Serien und Klassen bleiben getrennt. Keine Namen-/Tickerfusion und keine erfundenen ISINs.
- N-CEN-ETF-Flag nur als Klassenbeleg bei genau einer gemeldeten Klasse derselben Serie/Meldung.
  Mehrklassenserien bleiben offen; jüngster Bericht, danach jüngste Einreichung, Gleichstand offen.
  Historischer Bericht ist kein Beweis heutiger Handelbarkeit. Vier letzte Quartale; SEC warnt
  vor fehlenden Schema-3.1-Meldungen. Rohdaten und Konflikte bleiben nachvollziehbar.
- Lokale HTML-Suche macht den Bestand prüfbar. Keine Weltquote ohne Referenzuniversum. Neue
  Quellen erst nach konkreter Freigabe. NasdaqTrader ausgeschlossen; TickerInside-CC-BY deckt
  Drittanbieterrechte nicht pauschal. FIRDS-Rechte weiter ungeklärt.
- Alternative «alle öffentlichen Tickerlisten zusammenkopieren» verworfen: Nutzungsrechte,
  Identitäten, Instrumenttypen und Vollständigkeit wären nicht belastbar. Bezahlten Weltfeed
  ohne konkretes Angebot und Zustimmung beauftragen ebenfalls verworfen.

## 08.11.2026 – SwissPRTR-Emissionen normalisiert (Claude, Auftrag Jonas)

### D-032 Emissions-XLSX mit stdlib gelesen, Verknüpfung nur über die eigene Betriebs-UID
- **Entscheid (Auftrag Jonas):** Das bereits archivierte Original-XLSX (2007–2024) tatsächlich
  normalisieren statt nur zu archivieren. Standort-ID, Berichtsjahr, Schadstoff/Schadstoffgruppe,
  CAS, Menge, Einheit und Umweltmedium werden je Zeile erfasst, soweit vorhanden.
- **Lesung ohne neues Framework:** OOXML (ZIP + XML) wird mit `zipfile`/`xml.etree` (Stdlib)
  gelesen, nicht mit `openpyxl`/`pandas.read_excel` (nicht installiert, hätte eine neue
  Abhängigkeit erfordert) – dieselbe Logik wie beim bestehenden GeoPackage-Adapter (SQLite-
  Stdlib statt GIS-Framework). Das Datenblatt wird über seinen Namen («Daten…») gefunden, die
  Spalten über ihre englischen Kopfzeilen, nicht über feste Spaltenbuchstaben.
- **Verknüpfung ausschliesslich über die im XLSX gemeldete, prüfzifferngeprüfte Betriebs-UID**
  (Spalte «UID of facility»), nie über den Betriebs-/Firmennamen. Das SwissPRTR-Standortregister
  (GeoPackage) selbst hat keine UID-Spalte und bleibt wie bisher ohne Firmenzuordnung; die
  Emissionszeilen tragen ihre Zuordnung direkt und sind davon unabhängig.
  Ergebnis: 22'860 Zeilen, 16'058 Punktquellen eindeutig zugeordnet, 5'298 Punktquellen mit
  gültiger UID ohne passenden Rechtsträger (ausdrücklich `unresolved`), 28 Punktquellen ohne
  verwertbare UID, 1'476 Nicht-Punktquellen (diffuse Quellen wie Verkehr/Haushalte) ausdrücklich
  ohne Betrieb (`diffuse_source_no_facility`). Ungültige UID-Prüfziffern verwerfen nicht die
  ganze Zeile (Mengenangabe bleibt erhalten), sondern lassen nur die Zuordnung offen.
- **Emissionen sind kein Nachweis eines Rechtsverstosses:** `evidence_category:
  "emission_register_not_violation"`, zusätzlicher Hinweis im Qualitätsbericht
  (`coverage_notes`). Eine amtlich gemeldete Jahresmenge ist keine Feststellung von
  Fehlverhalten und kein Gerichtsurteil (vgl. D-016/D-017).
- **Exportschema:** `EXPORT_SCHEMA_VERSION` 1 → 2 (neues Feld `emissions`), damit die
  bestehende Exportgeneration automatisch neu aufgebaut wird statt stillschweigend veraltete
  Daten weiterzuverwenden.
- **Alternativen:** `openpyxl`/`pandas.read_excel` installieren (abgelehnt: neue Abhängigkeit,
  CLAUDE.md verlangt «keine neuen Frameworks», Stdlib reicht); Zuordnung zusätzlich über die
  Standort-ID aus dem GeoPackage versuchen (abgelehnt: Standortregister ist nur ein
  Jahresschnappschuss 2024 ohne UID, die XLSX-eigene UID ist die belastbarere, jahresunabhängige
  Kennung); fehlende/ungültige UID der ganzen Zeile zur Quarantäne hinzufügen (abgelehnt: das ist
  kein Identitätskonflikt wie bei GLEIF/Zefix, sondern nur eine offene Verknüpfung einer bereits
  gültigen Emissionsmeldung).

## 08.11.2026 – Schweizer Rohdatenfundament (Auftrag an Codex)

### D-031 Standardlauf bei bekannter Sperre und unveränderten Daten verkürzen
- Nach dem gemeldeten PowerShell-Lauf: Wikidata wegen reproduziertem HTTP 403 standardmässig
  deaktivieren und den Grund anzeigen. Expliziter Aufruf `--source wikidata_ch` darf den
  regulären Zugang weiterhin prüfen; echte Fehler bleiben sichtbar und liefern Exitcode 1.
- Vollständige Exportgeneration bei identischen aktiven Datenversionen und gleicher
  Exportschemaversion wiederverwenden. Aktuelle Diagnose in `latest_status.json`, keine
  Änderung an der historischen Generation. Fehlende Dateien/neue Versionen/Schemaversion
  lösen Neuaufbau aus. `--export-only` erzwingt den bisherigen vollständigen Neuaufbau.
- Der schnelle Standardlauf ist keine erneute Vollintegritätsprüfung; dafür Offline-Audit
  oder expliziten Neuaufbau verwenden. `EXPORT_SCHEMA_VERSION` bei semantischen Änderungen erhöhen.

### D-028 Schweizer Rohdaten lokal und separat vom öffentlichen Demo-Screening
- **Entscheid (Auftrag Jonas):** kostenlose, nachweisbar kommerziell nutzbare Originaldaten
  tatsächlich laden; dafür keine erneute Einzelrückfrage. Kein Push/Publizieren und keine
  kostenpflichtigen APIs. Diese Freigabe ersetzt die ältere Einzel-Download-Rückfrageregel
  für diesen Auftrag; D-027 zu konkretem US-Fonds und Sanktionsbewertung bleibt offen.
- Derselbe DataUpdateManager, separater Katalog `swiss_sources.toml` und `swiss.sqlite`.
  Originale in `data/raw/external/`, aktivierte Manifeste versioniert, Exporte lokal.
  Keine Framework-/Webdesignänderung; echte Rohdaten werden nicht in die Website gerendert.
- Lizenzsperre um Speicherung, Ableitungen und offizielle Lizenz-URL ergänzt; vier Rechte
  plus kommerzielle Verarbeitung und Auflagen getrennt dokumentiert. Abgelaufene oder
  unklare Freigabe verhindert den Abruf. Kandidaten ohne Rechte bleiben ohne Downloadadapter.

### D-029 Identitäten und Quarantäne statt ungesicherter Fusion
- Fusion nur über eindeutige LEI/UID. Mehrere LEIs zu einer UID oder mehrere Register-IDs
  zu derselben UID sind Konflikte; kein willkürlicher erster Treffer. Namensähnlichkeit
  produziert ausschliesslich Prüflisten. Mehrsprachige Namen derselben Register-ID sind Aliase.
- Ungültige Originalprüfziffern werden mit Herkunft separiert und nie repariert/importiert.
  Mehr als 1% Quarantäne (mindestens ein Eintrag toleriert) lehnt den Gesamtstand ab;
  Struktur-/Hashfehler lehnen unabhängig davon ab. Auch ausgeschlossene Registrierungsstatus
  bleiben nachvollziehbar in der Originaldatei und separater Liste erhalten.
- GLEIF FUND separat; keine ETF-/Anteilsklassen-/Positionsbehauptung. Wikidata-ISIN am
  Unternehmensitem wäre nur Kandidat, keine bestätigte Emittentenzuordnung.
- Mutterlinks/Reporting Exceptions werden nicht als verifizierte Konzernbeziehungen übernommen.
  SwissPRTR-Standorte ohne sichere UID bleiben unzugeordnet; kein Namens- oder Muttertransfer.

### D-030 Originaldateien und reproduzierbare lokale Aktualisierung
- SHA-256-adressierte Originalantworten mit Lizenz-/Download-Sidecars; Manifest verweist auf
  diese Dateien. GLEIF Cursor-Paginierung mit Gesamtzahl-/Snapshotprüfung, Zefix Keyset-Seiten
  über vollständige Registeridentitäten und zusätzliche Kontrollzählung; Zefix bleibt zeitversetzt.
- Mindestens 1.1s zwischen HTTP-Anfragen, begrenzte Wiederholungen und 24h-Cache;
  403/401 werden nicht umgangen. SwissPRTR-Asset gegen STAC-Prüfsumme geprüft.
- Stammdaten in 2'000er Blöcken innerhalb derselben Transaktion schreiben. Fertige
  Exportgeneration erst anschliessend per `current.json` aktivieren. OS-Lock verhindert
  parallele grosse Läufe; JSON wird gestreamt, um zusätzliche Vollkopien im Speicher zu vermeiden.
- Keine Vollständigkeitsbehauptung für Schweizer Firmen/Aktien/ETFs aus Quellen-Teilabdeckung.
  Nachweisbare vollständige API-/Registerabfrage und vollständiger Markt sind verschiedene Dinge.

## 08.11.2026 – Session 2, Teil 2 (erste echte Datenquelle, parallele Session)

### D-027 Offen gelassen: US-Fonds (N-PORT) als erster echter Fonds, OFAC im Belegmodell
- **Entscheid (Jonas):** beide Fragen **später entscheiden**. Lizenzrechtlich sind SEC N-PORT
  und OFAC SDN geeignet (`docs/DATA_SOURCES.md`); es wird nichts heruntergeladen.
- **Abzuwägen bei N-PORT:** nur US-registrierte Fonds, Zielgruppe hält meist UCITS-ETFs (D-020);
  dafür liefern die Fonds je Position ISIN und Emittenten-LEI selbst (ideal für die
  Zuordnungsquote). SEC verlangt einen User-Agent mit E-Mail-Adresse.
- **Vorschlag für OFAC (nicht entschieden):** eigener Sachverhaltstyp «Sanktionslistung»,
  Herausgeber Behörde, höchstens «dokumentiert», nie «festgestellt»; Anzeige von Programm-Kürzel
  und amtlicher Bezeichnung (z. B. «GLOMAG – Executive Order 13818 – Global Magnitsky»);
  einem Kriterium nur über eine von Jonas festgelegte Zuordnung Programm → Kriterium zugeordnet.

### D-026 GLEIF als erste echte Quelle, vorerst deaktiviert
- **Entscheid:** GLEIF (CC0 1.0) über die API anbinden, nicht über die Golden Copy (mehrere GB);
  abgefragt werden nur die LEIs aus `data/gleif/abfrageliste.txt`. Quelle bleibt `enabled = false`,
  bis ein echter Fonds LEIs liefert; die Liste enthält bis dahin nur den LEI von GLEIF selbst
  (Funktionsprobe, Entscheid Jonas: kein Unternehmen auswählen).
- **Übersetzungsregeln (Vorschlag, umgesetzt):** Schlüssel `lei:<LEI>`; Registrierungsstatus
  ANNULLED/CANCELLED/DUPLICATE wird nicht übernommen, LAPSED u. Ä. mit Warnung; eine
  Konzernbeziehung ist nur **verifiziert** (überträgt Belege, D-012), wenn sie aktiv,
  PUBLISHED und FULLY_CORROBORATED ist – sonst nur Hinweis. Kein ISIN-LEI-Mapping (Lizenz
  ungeklärt), deshalb liefert GLEIF keine Zuordnung Wertpapier → Unternehmen.
- **Zuordnungsquote:** `python -m transparenz mapping --fund ISIN` misst stufenweise nach Anzahl
  und Gewicht (Aktien/Anleihen → mit ISIN → Emittent zugeordnet → mit LEI → LEI bei GLEIF).
- **Alternativen:** Golden Copy (zu gross für wenige LEIs); GLEIF-ISIN-Abfrage (ausgeschlossen);
  N-PORT zuerst (fachlich offen, D-027).

### D-025 Lizenzregister je Quelle mit automatischer Sperre
- **Entscheid (Jonas):** Jede Quelle in `sources.toml` führt Lizenz, Lizenz-URL, Originalseite
  der Bedingungen, Prüfdatum, kommerzielle Nutzung, Weiterveröffentlichung und Quellenangabe.
  Echte Quellen ohne vollständige, höchstens 365 Tage alte Prüfung mit «ja» bei kommerzieller
  Nutzung **und** Weiterveröffentlichung werden **gesperrt** (kein Abruf, Status «gesperrt»).
- **Begründung:** Grundsatz «nur ausdrücklich kommerziell nutzbare oder klar öffentlich
  freigegebene Daten» soll technisch durchgesetzt werden, nicht nur dokumentiert. Bedingungen
  ändern sich (jährliche Wiederholung).
- **Alternativen:** nur Warnung im Protokoll (nicht gewählt); separates Lizenzregister neben
  den Quellen (mehr Doppelpflege).

## 07.11.2026 – Session 2 (Website online, Besuchszählung)

### D-024 Website zählt Besuche mit dem BORS/Portfolio-Tracker, inkl. IP-Sicherheitsprotokoll
- **Entscheid (Jonas):** Den Tracker von BORS auch auf dieser Website einsetzen, mit gleicher
  Erfassung wie BORS (zusammengefasste Zähler **und** Sicherheitsprotokoll mit voller IP, 14 Tage).
  Website und Tracker gehen zusammen online.
- **Umsetzung:** `src/transparenz/site/static/analytics-{config,client}.js` werden von `build-site`
  nach `site/` kopiert und in jeder Seite eingebunden (`data-analytics-site="transparenz"`);
  Datenschutz-Link im Fuss. Gegenüber BORS zählt der Client **nur auf
  `https://jonasbader7.github.io`** (lokal, Doppelklick, Tests: nichts gesendet). Worker
  (`Portfoliopage/analytics/backend/src/worker.js`) akzeptiert `site: "transparenz"`;
  Datenschutzseite im Portfolio nennt das Projekt.
- **Abweichung von D-021:** Die Seiten laden jetzt zwei lokale Skripte und senden Zähldaten an
  einen externen Dienst (Cloudflare). Anzeige und Inhalte bleiben ohne JavaScript vollständig.
  Test prüft: nur diese zwei lokalen Skripte, kein Token in der Konfiguration.
- **Grenzen:** keine Unterscheidung nach Unterseite (Worker nimmt bei Seitenaufrufen kein Detail
  an); Zahlen sind Ereignisse, keine Personen. IP-Protokoll = Personendaten, nicht rechtlich
  geprüft (`docs/recht/datenschutz.md`).
- **Alternativen:** nur Zähler ohne IP-Protokoll (vorgeschlagen, nicht gewählt); kein Tracking;
  Drittanbieter (GoatCounter, Plausible) – nicht nötig, eigener Worker existiert.

## 07.11.2026 – Session 1 (Projektaufbau)

### D-023 Ein öffentliches GitHub-Repo, vorerst ohne Lizenz
- **Entscheid (Jonas):** ein einziges, öffentliches Repo `Jonasbader7/Projekt-Transparenz`.
- **Begründung:** kostenlose GitHub Pages, sichtbar im Profil, offene Methodik passt zum
  Kernversprechen. Inhalte sind fiktiv; Strategie-Dokumente sind als Annahmen markiert.
- **Lizenz:** bewusst noch keine (= alle Rechte vorbehalten); später MIT oder AGPL prüfen.
- **Alternativen:** privates Repo + separates öffentliches Demo-Repo nur mit `site/`
  (mehr Aufwand, Strategie bliebe privat) – nicht gewählt.
- **Grenze:** Interviewnotizen, Kontakte und echte Fondsanalysen nie ungeprüft ins Repo.

### D-022 Projektordner: `OneDrive\Desktop\Projekt Transparenz`
- **Entscheid (Jonas):** dauerhafter Ort des Projekts. Git-Verlauf wurde mitübernommen.
- **Hinweis:** OneDrive synchronisiert auch eine lokale `.venv`; bei Problemen die Umgebung
  ausserhalb anlegen (`scripts\setup.ps1 -VenvPath …`).

### D-021 Vorerst eine statische Website statt lokaler App als Hauptoberfläche
- **Entscheid (Jonas):** Das Projekt soll vorerst eine Website sein.
- **Umsetzung:** Python erzeugt aus dem aktiven Datenstand fertige HTML-Seiten in `site/`
  (`python -m transparenz build-site`). Die Seiten sind eigenständig (CSS inline, keine externen
  Skripte), per Doppelklick lokal nutzbar und unverändert auf GitHub Pages veröffentlichbar.
  Alle Berechnungen bleiben in Python; die Website zeigt nur an. `site/` wird versioniert, damit
  geprüft werden kann, was veröffentlicht würde.
- **Begründung:** Die lokale Streamlit-App setzt PowerShell, Python und eine Installation voraus
  – zu viele Hürden für die Nutzung und für Interviews. Eine statische Seite entspricht dem
  bewährten BORS-Ansatz (GitHub Pages).
- **Alternativen:** Streamlit Community Cloud (braucht Push und externen Dienst, Server-Abhängigkeit);
  JavaScript-App mit Logik im Browser (Methodik doppelt implementiert – verworfen).
  Die Streamlit-App bleibt für lokale Arbeit (manuelle Updates) erhalten.

### D-020 Erste Zielgruppe: Privatanleger:innen
- **Entscheid (Jonas):** Die ersten Interviews, Texte und Berichte richten sich an
  Privatanleger:innen in der Schweiz.
- **Folgen:** Interviews primär mit Teil A des Leitfadens; Sprache in App und Bericht für Laien
  prüfen (Nutzertest); FIDLEG-Abgrenzung wird wichtiger, weil Laien Analysen leichter als
  Empfehlung lesen (R1 in offene-rechtsfragen.md bleibt hohe Priorität); Zahlungsbereitschaft B2C
  ist die grösste offene Annahme.
- **Alternativen:** Berater:innen (B2B) – nicht verworfen, Teil B des Leitfadens für 2–3
  Kontrollgespräche nutzbar.

### D-019 Musterstrategie, eigener Index und Fonds zurückgestellt
- **Begründung:** Eine eigene Anlagestrategie neben unabhängigen Fondsanalysen erzeugt einen
  Interessenkonflikt und schwächt die Glaubwürdigkeit (externes Feedback). Fokus: Analyseplattform.
- **Alternativen:** Musterportfolio als Phase 4 (ursprünglicher Plan) – verworfen bis Phase 6.

### D-018 Problemdefinition präzisiert
- **Begründung:** Die pauschale Aussage «ESG-Ratings bewerten Bemühungen statt Wirkung, Berater
  haben keine Werkzeuge» ist angreifbar (es gibt wirkungsorientierte Ratings und Software).
  Neue Fassung: verteilte, uneinheitliche, schwer verständliche Informationen; wir verbinden
  Positionen mit Quellen. Behauptungen sind als Annahmen markiert.

### D-017 Beweisstatus statt Zwei-Quellen-Regel
- **Entscheid:** Der Belegstatus richtet sich nach Art, Herausgeber und Verfahrensstatus des
  stärksten sicher zugeordneten Belegs (festgestellt · Prüfung ausstehend · Verfahren laufend ·
  dokumentiert · Medienbericht · Zuordnung unsicher · keine Hinweise · unbekannt).
- **Begründung:** Ein rechtskräftiges Urteil genügt allein; zwei Artikel mit demselben unbelegten
  Vorwurf genügen nicht. Die Anzahl Quellen sagt wenig über Unabhängigkeit aus (externes Feedback).
- **Alternativen:** Zwei-Quellen-Regel (ursprünglich, in derselben Session implementiert und
  ersetzt); Punktesystem (verworfen: Blackbox).

### D-016 «Festgestellt» nur nach menschlicher Dokumentprüfung
- **Begründung:** Automatisierung darf nie ungeprüfte Daten als festgestellte Verstösse zeigen.
  Ein als abgeschlossen gemeldeter Entscheid ohne Prüfung → «Prüfung ausstehend».

### D-015 Positionsliste als CSV (Austauschformat v1)
- **Begründung:** Anbieter liefern Positionen typischerweise als CSV/Excel; CSV ist für Jonas in
  Excel prüfbar. Fondsangaben stehen in jeder Zeile und müssen identisch sein (eine Datei = ein Fonds).
- **Alternativen:** JSON mit Fonds-Kopf (zuerst gebaut, ersetzt); Metadaten in Konfiguration (verworfen:
  Stichtag gehört zum Datenstand).

### D-014 Abdeckung als eigene Datenart
- **Begründung:** «Keine Hinweise» darf nur erscheinen, wenn eine Quelle das Unternehmen geprüft
  hat. Fehlende Abdeckung → «unbekannt». Abdeckung, die nur über den Namen zugeordnet ist, zählt nicht.

### D-013 Zuordnung: LEI > ISIN > Name; LEI-Konflikt blockiert
- **Begründung:** Schutz vor Fehlzuordnungen. Namensabgleich hat Vertrauen «tief» und bestimmt nie
  den Status. Gleicher Name mit anderem LEI = anderer Rechtsträger → keine Zuordnung.

### D-012 Konzern: nur verifizierte Beziehungen übertragen Belege
- **Begründung:** Unverifizierte Beteiligungen könnten Unternehmen zu Unrecht belasten. Sie werden
  als Hinweis gezeigt, Belege aber nicht übernommen.

### D-011 Schwellenwerte offen lassen
- **Begründung:** Festlegung ist eine inhaltliche Entscheidung von Jonas. Bis dahin werden
  Kennzahlen angezeigt und mit Hinweis als Beleg behandelt; Schwellenwert gilt «ab» (≥).

### D-010 Neuer Sachverhaltstyp «Ausschlussentscheid»
- **Begründung:** Ausschlüsse institutioneller Anleger (z. B. NBIM) sind weder Vorwurf noch Urteil.
  Eingeordnet als Stufe 2 (Institution) → «dokumentiert».

### D-009 Versionierung pro Quelle, Aktivierung in einer Transaktion
- **Begründung:** Erfüllt «fehlerhafte Daten überschreiben nie den letzten gültigen Stand».
  Validierung vollständig vor dem Schreiben; ein Fehler lehnt die Datei ab; Rohdaten werden
  (auch abgelehnte) als Schnappschuss aufbewahrt.
- **Alternativen:** Upsert in Stammtabellen (verworfen: keine Historie, Teilimporte möglich).

### D-008 Fiktive Kennungen eindeutig unterscheidbar
- **Entscheid:** ISIN-Präfix `ZZ` (ISO-3166 user-assigned), LEI-Präfix `FIKT00`, Links auf
  `example.org`, Namen mit «Beispiel»/«Muster», Fonds mit «(fiktiv)».

### D-007 Nur lokale Quellen aktiv; HTTP-Abruf gebaut und getestet, nicht angebunden
- **Begründung:** Echte Quellen erst nach Lizenzprüfung. `HttpFetcher` (ETag/304, Wiederholungen)
  ist mit simulierten Antworten getestet.

### D-006 GitHub Actions: Tests aktiv, Update-Workflow nur manuell
- **Begründung:** Runner sind temporär; ohne dauerhaften Speicher wäre ein geplanter Update-Lauf
  wirkungslos. Ergebnis nur als 7-Tage-Artefakt. Dauerhafter Speicher verursacht Kosten → Rücksprache.

### D-005 Statusfarben
- **Entscheid:** «Unbekannt» und «Zuordnung unsicher» gelb (Lücken sichtbar), «Keine Hinweise»
  grau statt grün (kein Nachhaltigkeitsnachweis).

### D-004 Kein Alembic im ersten Meilenstein
- **Begründung:** Nur fiktive Daten, Schema kann neu erzeugt werden. Migrationen vor dem ersten
  dauerhaften echten Datenbestand.

### D-003 Abweichungen von der vorgeschlagenen Ordnerstruktur
- `entities/` enthält Domänenmodelle, Kennungen und Zuordnung (statt separatem `models/`).
- `app/views/` statt `app/pages/` (Streamlit-Navigation mit `st.navigation`; ein Ordner
  namens `pages/` würde die alte automatische Seitenerkennung auslösen).
- Kommandozeile `python -m transparenz …` statt einzelner Skripte für DB-Init, Import, Update,
  Validierung; `scripts/` enthält Setup/Start (PowerShell, Bash) und den Beispieldaten-Generator.

### D-002 Anzeigename an genau einer Stelle
- `DEFAULT_DISPLAY_NAME` in `src/transparenz/config/settings.py`, überschreibbar mit
  `TRANSPARENZ_DISPLAY_NAME`. Paketname neutral: `transparenz`.

### D-001 Technischer Rahmen
- Python 3.12, src-Layout, pandas, Pydantic v2, SQLAlchemy 2 + SQLite, httpx, Streamlit, pytest,
  ruff. Modularer Monolith. Keine kostenpflichtige KI-API.
