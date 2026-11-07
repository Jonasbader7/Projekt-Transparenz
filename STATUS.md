# STATUS

**Stand:** 07.11.2026 (Session 2) · **Phase:** 0 Klarheit → Übergang zu 1 Gespräche
(parallel: technisches Fundament für Phase 2 steht)

## Auf einen Blick

| | |
|---|---|
| Projektordner | `C:\Users\Bader\OneDrive\Desktop\Projekt Transparenz` |
| GitHub | https://github.com/Jonasbader7/Projekt-Transparenz (**öffentlich**, Branch `main`, keine Lizenz) |
| Website lokal | `site\index.html` doppelklicken |
| Website online | **https://jonasbader7.github.io/Projekt-Transparenz/** – live seit 07.11.2026, Stand Commit `f33bc46` (Workflow «Website veröffentlichen» nach jeder Website-Änderung manuell starten) |
| Tests | 110 grün lokal und auf GitHub Actions (Commit `f33bc46`) |
| Daten | ausschliesslich fiktiv |
| Zielgruppe | Privatanleger:innen (D-020) |
| Besuchszählung | aktiv (D-024): BORS/Portfolio-Worker, Seite `transparenz`; auswerten mit `Portfoliopage\analytics\backend\dashboard-windows.ps1` |

## Fortschritt

Das MVP-Fundament läuft **mit fiktiven Daten** End-to-End: CSV-Import → Validierung →
versionierte Datenbank → Screening nach Belegmodell → **statische Website** (Hauptoberfläche),
dazu Streamlit-App (lokal) und Bericht als Markdown/CSV.

### Funktioniert (getestet)

| Funktion | Nachweis |
|---|---|
| Positionsliste als CSV importieren (Komma/Semikolon, Dezimalkomma) | `tests/test_parsing.py`, End-to-End-Test |
| Validierung: Pflichtfelder, ISIN/LEI-Prüfziffern, Gewichtssumme, Zukunftsdaten, Kriterien | `tests/test_parsing.py` |
| Duplikate: exakt (entfernt), widersprüchlich (abgelehnt), inhaltlich (Warnung) | `tests/test_parsing.py` |
| Zuordnung Wertpapier → Unternehmen mit Vertrauen; LEI-Konflikt blockiert Fehlzuordnung | `tests/test_identifiers_and_resolution.py` |
| Belegstatus nach Beweisstatus (keine starre Quellenanzahl), Trennung Vorwurf/Behörde/Gericht | `tests/test_screening.py` |
| Datenlücken als «unbekannt»; «keine Hinweise» nur mit Abdeckung | `tests/test_screening.py` |
| Konzern: nur verifizierte Mutter überträgt Belege | `tests/test_screening.py` |
| Fehlgeschlagenes Update verändert den gültigen Datenbestand nicht | `tests/test_update_manager.py`, End-to-End-Test |
| Wiederholungen bei vorübergehenden Fehlern, begrenzt; Intervalle; Hash/ETag-Erkennung | `tests/test_update_manager.py` |
| Jede angezeigte Feststellung mit Quelle, Datum, Datenstand (Version, Hash, Importzeit) | End-to-End-Test, `tests/test_site.py` |
| Statische Website: 4 Seiten + Bericht/CSV, ohne externe Ressourcen, Links geprüft, Texte escaped | `tests/test_site.py`; im Browser geprüft (Desktop, Handy, hell/dunkel) |
| Streamlit: vier Seiten | End-to-End-Test (AppTest) + manuell im Browser |
| Besuchszählung: nur lokale Skripte, kein Token, zählt nur auf github.io | `tests/test_site.py`; lokal im Browser geprüft (keine Anfrage an den Worker); online geprüft: Seitenaufruf vom Worker mit 204 angenommen, keine Konsolenfehler |
| Website online (GitHub Pages) | Workflow «Website veröffentlichen» erfolgreich, Seite live geprüft |
| Windows-Setup | `scripts/setup.ps1` in Windows PowerShell 5.1 ausgeführt (Exit 0; Session 2: `.venv` im Projektordner) |
| Tests auf GitHub | Workflow `ci.yml` lief grün |

### Nur vorbereitet (nicht produktiv)

- HTTP-Abruf echter Quellen (gebaut und getestet, keine Quelle angebunden)
- Update-Workflow auf GitHub nur manuell, ohne dauerhaften Speicher
- Schwellenwerte (Platzhalter in `docs/methodik/ausschlusskriterien.md`)
- Kein echter Fonds, keine echte Belegquelle

## Nächste 3 Schritte

1. **Repo auf dem GitHub-Profil anpinnen** und den Website-Link im Portfolio/README ergänzen.
2. **3–5 Interviews mit Privatanleger:innen** (Leitfaden Teil A), die Website als
   Gesprächsgrundlage nutzen; Erkenntnisse in `docs/kundengespraeche/erkenntnisse.md`.
3. **Erste echte Datenquelle** anbinden: läuft in einer eigenen Session (Vorschlag SEC N-PORT +
   GLEIF + OFAC, nur kommerziell nutzbare Quellen; iShares und NBIM vorerst ausgeschlossen).
   Inkl. Lizenzprüfung und Messung der Zuordnungsquote. Danach Schwellenwerte festlegen.

## Offene Fragen an Jonas

- Welche echte Datenquelle zuerst? (in Bearbeitung, separate Session)
- IP-Sicherheitsprotokoll auf der Website rechtlich prüfen lassen, bevor echte Interviewpartner
  die Seite nutzen (D-024, `docs/recht/datenschutz.md`)?
- Produktname: «ImpactLens» (Vorschlag aus Feedback) übernehmen oder offen lassen?
- Lizenz (keine / MIT / AGPL; Methodik evtl. CC BY)? Repo ist bereits öffentlich.
- Commit-E-Mail öffentlich lassen oder auf GitHub-noreply-Adresse umstellen?
- Wöchentliche Status-Zusammenfassung (Sonntagabend) einrichten?
- Persönliches Beispiel aus der Bankzeit (`docs/strategie/problem-statement.md`) – ausfüllen,
  und darf es öffentlich sein?

## Hinweise für die nächste Session

- **Python-Umgebung:** liegt seit Session 2 in `.venv` im Projektordner (OneDrive synchronisiert
  sie mit). Fehlt sie: `powershell -ExecutionPolicy Bypass -File scripts\setup.ps1`.
- Lokale Vorschau für Claude: `.claude/launch.json` → «website» auf Port 8610 (nicht versioniert).
- Tracker ausschalten: `endpoint: ""` in `src/transparenz/site/static/analytics-config.js`, dann
  `build-site`.
- Nach Änderungen an Daten oder Darstellung: `python -m transparenz build-site` und `site/`
  mitcommitten.
- Push und Veröffentlichen immer nur mit ausdrücklicher Zustimmung.

## Bekannte Einschränkungen

- Nur fiktive Daten; Aussagekraft für echte Fonds noch unbelegt.
- Unabhängigkeit von Berichten wird über Herausgeber gezählt, nicht über die Recherche.
- Freisprüche/aufgehobene Urteile nicht modelliert.
- Keine DB-Migrationen; Schema wird bei Änderungen neu erzeugt.
- Nicht rechtlich geprüft (siehe `docs/recht/`).
- Die Website ist ein Schnappschuss: nach Datenänderungen `build-site` erneut ausführen.
- Projekt liegt in OneDrive; eine `.venv` dort wird mitsynchronisiert.
