# STATUS

**Stand:** 07.11.2026 · **Phase:** 0 Klarheit (parallel: technisches Fundament für Phase 2)

## Fortschritt

Das MVP-Fundament läuft **mit fiktiven Daten** End-to-End: CSV-Import → Validierung →
versionierte Datenbank → Screening nach Belegmodell → Streamlit-Anzeige und Bericht.
84 Tests bestehen (zuletzt ausgeführt am 07.11.2026), ruff ohne Befund.

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
| Fehlgeschlagenes Update verändert den gültigen Datenbestand nicht (Validierungsfehler, Abbruch beim Schreiben) | `tests/test_update_manager.py`, End-to-End-Test |
| Wiederholungen bei vorübergehenden Fehlern, begrenzt; Intervalle; Hash/ETag-Erkennung | `tests/test_update_manager.py` |
| Jede angezeigte Feststellung mit Quelle, Datum, Datenstand (Version, Hash, Importzeit) | End-to-End-Test |
| Streamlit: vier Seiten, Fondsanalyse zeigt importierte CSV-Daten | End-to-End-Test (AppTest) + manuell im Browser |
| Windows-Setup und Start | `scripts/setup.ps1` in Windows PowerShell 5.1 ausgeführt (Exit 0), App unter localhost:8501 geöffnet |

### Nur vorbereitet (nicht produktiv)

- HTTP-Abruf echter Quellen (gebaut und mit simulierten Antworten getestet, keine Quelle angebunden)
- GitHub Actions: Test-Workflow bereit; Update-Workflow nur manuell, ohne dauerhaften Speicher
  (noch nie auf GitHub gelaufen – Repo ist nicht veröffentlicht)
- Schwellenwerte (Platzhalter in `docs/methodik/ausschlusskriterien.md`)
- Kein echter Fonds, keine echte Belegquelle

## Nächste 3 Schritte

1. **Erste Zielgruppe entscheiden** und 3–5 Interviews mit dem Leitfaden führen (Phase 1).
2. **Erste echte Datenquelle** anbinden (Vorschlag: eine echte ETF-Positionsliste lokal + GLEIF
   für die Zuordnung), inkl. Lizenzprüfung und Messung der Zuordnungsquote.
3. **Schwellenwerte und Definitionen** für die fünf Kriterien festlegen.

## Offene Fragen an Jonas

- Erste Zielgruppe: Privatanleger:innen oder Berater:innen?
- Welche echte Datenquelle zuerst?
- Produktname: «ImpactLens» (Vorschlag aus Feedback) übernehmen oder weiter offen lassen?
- Lizenz für Code und Methodik (z. B. MIT/AGPL bzw. CC BY), bevor das Repo öffentlich wird?
- Wöchentliche Status-Zusammenfassung (Sonntagabend) einrichten, sobald das Projekt in einem
  dauerhaften Ordner liegt?

## Bekannte Einschränkungen

- Nur fiktive Daten; Aussagekraft für echte Fonds noch unbelegt.
- Unabhängigkeit von Berichten wird über Herausgeber gezählt, nicht über die Recherche.
- Freisprüche/aufgehobene Urteile nicht modelliert.
- Keine DB-Migrationen; Schema wird bei Änderungen neu erzeugt.
- Nicht rechtlich geprüft (siehe `docs/recht/`).
