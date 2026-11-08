# STATUS

**Stand: 08.11.2026 · lokales Schweizer Rohdatenfundament umgesetzt, Export-Wiederverwendung
ergänzt (D-031).** Die bestehende Website bleibt eine fiktive Demo. Echte Daten wurden
ausschliesslich lokal importiert; nichts veröffentlicht oder gepusht.
Übergabe: `docs/CODEX_TO_CLAUDE_HANDOFF.md`.

## Tatsächlicher Datenbestand

| Bestand | Anzahl / Aussage |
|---|---|
| Zusammengeführte Rechtseinheiten | 801'647, davon 801'626 ohne Kennungskonflikt |
| GLEIF CH | 28'495 Originaldatensätze = 25'121 Rechtsträger + 3'254 Fondsrechtsträger + 118 Statusausschlüsse + 2 ungültige LEIs |
| Zefix/LINDAS | 796'690 Originaleinheiten, 796'684 validiert; sechs Einheiten in Quarantäne |
| Bestätigte Wertpapiere / ETF-Anteilsklassen mit ISIN / Fondspositionen | 0 / 0 / 0 |
| SwissPRTR | 247 Standorte, keine sichere Firmenzuordnung; Original-Emissions-XLSX 2007–2024 archiviert |
| Prüflisten | 13'189 mögliche Namensdubletten-Gruppen; 10 Kennungskonflikt-Gruppen; 776'526 Einheiten ohne LEI; insgesamt 8 Quarantäneeinträge |

Registereinheiten umfassen verschiedene Rechtsformen; die Zahl bezeichnet nicht ausschliesslich
operative Aktiengesellschaften. GLEIF FUND ist kein Nachweis für einen börsengehandelten ETF.
Keine vollständige Schweizer Aktien-/ETF-Abdeckung nachgewiesen.

## Betrieb

```powershell
cd "C:\Users\Bader\OneDrive\Desktop\Projekt Transparenz"
.venv\Scripts\python -m transparenz swiss-update
```

Einzelne Quelle: `--source gleif_ch`, `--source zefix_lindas`, `--source swissprtr`.
`--export-only` baut den Export vollständig ohne Netzwerk neu auf (mehrere Minuten);
`--force` ignoriert das Importintervall,
der 24h-HTTP-Cache bleibt wirksam. Nach Cacheablauf bedingte Requests, soweit unterstützt.
Ein OS-Dateilock verhindert gleichzeitige Schweizer Import-/Exportläufe.
Wikidata ist im Standardlauf mit sichtbarem Grund deaktiviert; manuell mit
`--source wikidata_ch` weiterhin prüfbar (HTTP 403 bleibt ein Fehler mit Exitcode 1).
Unveränderte Daten verwenden die fertige Exportgeneration weiter. Aktuelle Lauf- und
Lizenzmeldungen: `data/processed/swiss/latest_status.json`. Generation und Daten bleiben dabei
unverändert; neue Versionen, fehlende Exportdateien oder eine neue Exportschemaversion
lösen den vollständigen Neuaufbau aus.

- Originaldateien und Lizenz-Sidecars: `data/raw/external/<quelle>/objects/`.
- Aktivierte Manifeste: `data/raw/external/manifests/<quelle>/`.
- Separate versionierte DB: `data/processed/swiss.sqlite`.
- Fertiger Export: `data/processed/swiss/current.json` → `generations/<id>/`.
- Qualitätsbericht und Prüflisten liegen in derselben Generation. Alle echten Daten Git-ignoriert.
- Rohdaten, Caches und Exportgenerationen benötigen mehrere GB; Aufbewahrungspolitik noch offen.

## Quellen und Prüfungen

Funktionsfähig: GLEIF CC0, Zefix terms_open, SwissPRTR terms_by (Quellenangabe verpflichtend).
Wikidata CC0 rechtlich freigegeben, technisch HTTP 403. SIX, ANNA-ISIN-Mapping, Anbieterpositionen,
OpenSanctions sowie nicht konkret freigegebene Wirkungsdaten werden nicht produktiv geladen.
Details: `docs/DATA_SOURCES.md`, `src/transparenz/config/source_reviews.json`.
Die Lizenzsperre prüft jetzt auch Speicherung, Ableitungen und offizielle Lizenz-URL.

Tests: **172 bestanden**, Ruff sauber; bestehende 151 Tests waren vor Änderung ebenfalls grün.
Offline-Bestandsaudit: `scripts/audit_swiss_foundation.py` → `data/processed/swiss/audit_report.json`.
Keine neuen Frameworks und keine Änderung am Webdesign.

## Nächste drei Aufgaben

1. Regulären Wikidata-Zugang herstellen und die vorbereiteten Abfragen/Adapter live prüfen;
   keine Umgehung des HTTP 403. Eine freigegebene Referenzliste für Schweizer Kotierungen finden.
2. SwissPRTR-XLSX fachlich normalisieren und Betreiber-UIDs mit Herkunft erschliessen;
   keine Zuordnung über ähnliche Namen oder ungeprüfte Mutterbeziehungen.
3. Einen konkreten Schweizer/UCITS-ETF-Datensatz inkl. Redistribution freigeben und ISIN,
   Anteilsklasse, Domizil, Kotierung und Fondspositionen sauber modellieren.

## Weiterhin offen

Kein bestätigter Aktien-/ETF-Katalog; keine echte Belegquelle im Screening. GLEIF-Mutterlinks
liegen als ungeklärte Hinweise vor, nicht als verifizierte Beziehungen. Keine DB-Migrationen;
vor Integration neuer Attribute ins Screening Migrationen planen. Quellenrechte technisch anhand
offizieller Bedingungen geprüft, keine externe juristische Prüfung. Persönliche Interviews und
Produkt-/Lizenzentscheidungen aus den bisherigen Strategieunterlagen bleiben offen.
Die Online-Demoseite wird nur nach ausdrücklicher Zustimmung aktualisiert. Der neue lokale
Datenbestand wird bewusst nicht in die öffentliche Website eingebaut.
