# Entscheidungslog

Format: Datum · Entscheid · Begründung · Alternativen. Neueste zuoberst innerhalb einer Session.

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
