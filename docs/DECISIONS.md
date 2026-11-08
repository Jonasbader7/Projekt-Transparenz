# Entscheidungslog

Format: Datum · Entscheid · Begründung · Alternativen. Neueste zuoberst innerhalb einer Session.

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
