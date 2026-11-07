# STATUS

**Stand:** 07.11.2026 (Ende Session 1) · **Phase:** 0 Klarheit → Übergang zu 1 Gespräche
(parallel: technisches Fundament für Phase 2 steht)

## Auf einen Blick

| | |
|---|---|
| Projektordner | `C:\Users\Bader\OneDrive\Desktop\Projekt Transparenz` |
| GitHub | https://github.com/Jonasbader7/Projekt-Transparenz (**öffentlich**, Branch `main`, keine Lizenz) |
| Website lokal | `site\index.html` doppelklicken |
| Website online | geplant: https://jonasbader7.github.io/Projekt-Transparenz/ – **noch nicht aktiv** (Pages einschalten, siehe unten) |
| Tests | 109 grün lokal; GitHub Actions «Tests» grün (Lauf vom 07.11.2026) |
| Daten | ausschliesslich fiktiv |
| Zielgruppe | Privatanleger:innen (D-020) |

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
| Windows-Setup | `scripts/setup.ps1` in Windows PowerShell 5.1 ausgeführt (Exit 0) |
| Tests auf GitHub | Workflow `ci.yml` lief grün |

### Nur vorbereitet (nicht produktiv)

- **GitHub Pages:** Workflow `pages.yml` vorhanden, aber Pages ist im Repo noch nicht
  eingeschaltet (Jonas: Settings → Pages → Source «GitHub Actions», dann Workflow
  «Website veröffentlichen» manuell starten)
- HTTP-Abruf echter Quellen (gebaut und getestet, keine Quelle angebunden)
- Update-Workflow auf GitHub nur manuell, ohne dauerhaften Speicher
- Schwellenwerte (Platzhalter in `docs/methodik/ausschlusskriterien.md`)
- Kein echter Fonds, keine echte Belegquelle

## Nächste 3 Schritte

1. **Website online bringen** (Pages einschalten, Workflow starten, Seite online prüfen) und
   Repo auf dem Profil anpinnen.
2. **3–5 Interviews mit Privatanleger:innen** (Leitfaden Teil A), die Website als
   Gesprächsgrundlage nutzen; Erkenntnisse in `docs/kundengespraeche/erkenntnisse.md`.
3. **Erste echte Datenquelle** anbinden (Vorschlag: echte ETF-Positionsliste lokal + GLEIF),
   inkl. Lizenzprüfung und Messung der Zuordnungsquote. Danach Schwellenwerte festlegen.

## Offene Fragen an Jonas

- Welche echte Datenquelle zuerst?
- Produktname: «ImpactLens» (Vorschlag aus Feedback) übernehmen oder offen lassen?
- Lizenz (keine / MIT / AGPL; Methodik evtl. CC BY)? Repo ist bereits öffentlich.
- Commit-E-Mail öffentlich lassen oder auf GitHub-noreply-Adresse umstellen?
- Wöchentliche Status-Zusammenfassung (Sonntagabend) einrichten?
- Persönliches Beispiel aus der Bankzeit (`docs/strategie/problem-statement.md`) – ausfüllen,
  und darf es öffentlich sein?

## Hinweise für die nächste Session

- **Python-Umgebung neu einrichten:** Die bisherige Umgebung lag in einem temporären Ordner der
  ersten Session und existiert nicht mehr. Im Projektordner:
  `powershell -ExecutionPolicy Bypass -File scripts\setup.ps1` (oder mit `-VenvPath`
  ausserhalb von OneDrive). Danach Tests laufen lassen.
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
