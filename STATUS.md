# STATUS

## Dokumentationsstand 11.11.2026

KI-Beiträge, Skills und Werkzeuge sind im [README](README.md#ki-unterstützung-skills-und-werkzeuge)
und in [docs/AI_USAGE.md](docs/AI_USAGE.md) sichtbar. Historische Skill-Aufrufe bleiben als
nicht erfasst gekennzeichnet. Künftige Sessions ergänzen die Übersicht gemäss `CLAUDE.md`.
Fachlicher Projektstand und offene Entwicklungsschritte stehen unverändert unten.


**Stand: 08.11.2026 · Wikidata-Wertpapierkandidaten reparieren und durchsuchbar machen (D-034).**
Jonas meldete: Roche und Nestlé fehlen in der lokalen Suche; einige Schweizer Unternehmen
erscheinen nur über US-Kotierungen. Ursache war **kein** anhaltender HTTP 403, sondern drei
Bugs in der bislang deaktivierten `wikidata_ch`-Quelle: eine falsche Wikidata-ID für die SIX
Swiss Exchange (Q12569 ist der Fluss Loire, nicht die Börse; richtig: Q661834), zwei ebenso
falsche Fondsklassen-IDs (Q927783/Q756898 sind eine historische Person und ein Dorf; richtig:
Q845477/Q4201895) und eine zu teure SPARQL-Abfrage (Transitivabschluss über ganz Wikidata),
die den Abfragedienst in Zeitüberschreitungen bzw. Bot-Policy-Sperren (403) laufen liess.
Reparierte, auf SIX-notierte bzw. CH-ansässige Posten mit ISIN eingegrenzte Abfrage antwortet
in 1–3 Sekunden. Zusätzlich ein zu generischer HTTP-User-Agent ohne Kontaktangabe behoben
(Wikimedia-Bot-Policy); betrifft auch GLEIF/Zefix (positiver Nebeneffekt).
`wikidata_ch` läuft jetzt **standardmässig** (nicht mehr deaktiviert) und lieferte real
**287 Datensätze** → **293 Wertpapierkandidaten** (Roche, Nestlé, Novartis, UBS, ABB, Swatch,
Sika, Zurich Insurance u. a. mit echter ISIN/LEI/Ticker), 3 neue LEI-Konfliktgruppen
(zwei Wikidata-Einträge mit identischer LEI; sauber unter Quarantäne, nicht verworfen).
Jede Angabe bleibt ein **unverifizierter unternehmensbezogener Quellenhinweis** (`claims`),
kein bestätigtes Emittentenmapping; Fonds-ETF-Abfrage lieferte im Schweizer/SIX-Zuschnitt 0
Treffer (weltweit 19, siehe `docs/DATA_SOURCES.md`). Neu durchsuchbar:
`.venv\Scripts\python -m transparenz swiss-search Roche`; lokale HTML-Ansicht
`security_candidates.html` in der aktuellen Exportgeneration (Pfad über
`swiss-update`-Ausgabe oder `data/processed/swiss/current.json`). Kein SIX-Vollständigkeits-
nachweis; **201 Tests bestanden** (200 + 1 neu für LEI-Konflikt/Ticker-Qualifier), Ruff sauber,
Offline-Audit bestanden.

Der SEC-Teilbestand aus `market-update`/`market-search` (D-033) bleibt unverändert bestehen:
44'085 Katalogeinträge (US-Fokus, keine Weltabdeckung); Details weiterhin in
`docs/GLOBAL_MARKET_CATALOG.md`. Separate DB `markets.sqlite`, Originale mit Hash/Lizenz-
Sidecars und lokale HTML-/JSON-Exporte. Kontakt-E-Mail nur in Git-ignorierter `.env` für den
vom Nutzer autorisierten SEC-User-Agent. Visuelle HTML-Prüfung des SEC-Katalogs weiterhin durch
Browser-Dateiprotokollsperre verhindert. Keine ISINs/Handelbarkeit erfunden.

SwissPRTR-Emissionen 2007–2024 sind weiterhin normalisiert (D-032). Die bestehende
Website bleibt eine fiktive Demo und ist von dieser Session unberührt. Echte Daten wurden
ausschliesslich lokal importiert; nichts veröffentlicht oder gepusht.
Übergabe (historisch, vor D-034): `docs/CODEX_TO_CLAUDE_HANDOFF.md`.

## Tatsächlicher Datenbestand

| Bestand | Anzahl / Aussage |
|---|---|
| Zusammengeführte Rechtseinheiten | 801'732, davon 801'719 ohne Kennungskonflikt |
| GLEIF CH | 28'495 Originaldatensätze = 25'121 Rechtsträger + 3'254 Fondsrechtsträger + 118 Statusausschlüsse + 2 ungültige LEIs |
| Zefix/LINDAS | 796'690 Originaleinheiten, 796'684 validiert; sechs Einheiten in Quarantäne |
| Wikidata – Wertpapierkandidaten (D-034) | 287 Datensätze, 293 ISIN-Kandidaten (Roche, Nestlé, Novartis, UBS, ABB u. a.); 3 LEI-Konfliktgruppen unter Quarantäne; unverifizierte unternehmensbezogene Angabe, kein Emittentenmapping |
| Schweizer Bestand: bestätigte Wertpapiere / ETF-Anteilsklassen mit ISIN / Fondspositionen | 0 / 0 / 0; Wikidata-Kandidaten und SEC-Katalog separat, keine bestätigte Ausprägung |
| SwissPRTR-Standorte | 247, weiterhin keine sichere Firmenzuordnung (Standortregister ohne UID-Feld) |
| SwissPRTR-Emissionen 2007–2024 | 22'860 Zeilen aus dem Original-XLSX normalisiert: 16'058 Punktquellen mit validierter Betriebs-UID eindeutig einem Rechtsträger zugeordnet, 5'298 Punktquellen mit validierter UID ohne passenden Rechtsträger, 28 Punktquellen ohne verwertbare UID, 1'476 Nicht-Punktquellen (diffuse Quellen wie Verkehr/Haushalte) ausdrücklich ohne Betrieb/Zuordnung |
| Prüflisten | 13'228 mögliche Namensdubletten-Gruppen; 13 Kennungskonflikt-Gruppen; 776'599 Einheiten ohne LEI; insgesamt 8 Quarantäneeinträge |

Emissionen sind amtlich gemeldete Jahreswerte (Schadstoff/Abfall je Standort und Jahr), kein
automatischer Nachweis eines Rechtsverstosses und keine Feststellung von Fehlverhalten. Die
Zuordnung zu einem Rechtsträger läuft ausschliesslich über die im XLSX selbst gemeldete,
prüfzifferngeprüfte Betriebs-UID – nie über Firmennamen und nicht über das (UID-lose)
Standortregister. Ungeklärte Zeilen bleiben explizit `unresolved` bzw.
`diffuse_source_no_facility`.

Registereinheiten umfassen verschiedene Rechtsformen; die Zahl bezeichnet nicht ausschliesslich
operative Aktiengesellschaften. GLEIF FUND ist kein Nachweis für einen börsengehandelten ETF.
Keine vollständige Schweizer Aktien-/ETF-Abdeckung nachgewiesen.

## Betrieb

```powershell
cd "C:\Users\Bader\OneDrive\Desktop\Projekt Transparenz"
.venv\Scripts\python -m transparenz swiss-update
```

Einzelne Quelle: `--source gleif_ch`, `--source zefix_lindas`, `--source swissprtr`,
`--source wikidata_ch` (läuft seit D-034 auch im Standardlauf mit).
`--export-only` baut den Export vollständig ohne Netzwerk neu auf (mehrere Minuten);
`--force` ignoriert das Importintervall,
der 24h-HTTP-Cache bleibt wirksam. Nach Cacheablauf bedingte Requests, soweit unterstützt.
Ein OS-Dateilock verhindert gleichzeitige Schweizer Import-/Exportläufe.
Durchsuchen: `.venv\Scripts\python -m transparenz swiss-search <Begriff>` (Name, ISIN, Ticker
oder LEI) oder die lokale `security_candidates.html` in der aktuellen Exportgeneration öffnen;
beides zeigt nur Wikidata-Kandidaten, keine bestätigten Wertpapiere.
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

Funktionsfähig: GLEIF CC0, Zefix terms_open, SwissPRTR terms_by (Quellenangabe verpflichtend),
**Wikidata CC0 seit D-034 ebenfalls funktionsfähig** (Query-Bugs behoben, siehe oben).
SIX selbst, ANNA-ISIN-Mapping, Anbieterpositionen, OpenSanctions sowie nicht konkret
freigegebene Wirkungsdaten werden weiterhin nicht produktiv geladen. Details:
`docs/DATA_SOURCES.md`, `src/transparenz/config/source_reviews.json`.
Die Lizenzsperre prüft jetzt auch Speicherung, Ableitungen und offizielle Lizenz-URL.

Tests: **201 bestanden** (200 vorher + 1 neu: Wikidata-Ticker-Qualifier und LEI-Konflikt-
Quarantäne), Ruff sauber. HTTP-User-Agent für alle externen Quellen auf eine Wikimedia-
Bot-Policy-konforme, projektbezogene Kennung umgestellt (vorher generisch/ohne Kontakt);
betrifft GLEIF/Zefix/Wikidata gemeinsam, keine quellenspezifische Ausnahme.
Offline-Bestandsaudit: `scripts/audit_swiss_foundation.py` → `data/processed/swiss/audit_report.json`.
Keine neuen Frameworks, keine Änderung am Webdesign.

## Nächste drei Aufgaben

1. Wikidata-Abfrage auf weitere Weltmärkte ausweiten (nicht nur SIX/Schweiz); je Börse eine
   eigene `VALUES`-Erweiterung statt eines erneuten Vollscans, damit die Antwortzeit niedrig
   bleibt. Ticker-Qualifier-Extraktion (`pq:P249`) bereits vorhanden und wiederverwendbar.
2. Weltweites Börsen-Referenzuniversum festlegen; konkrete Rechte und passende Instrumentdateien
   für weitere Märkte prüfen (CVM/FSMA nächste Kandidaten; SIX/FIRDS weiterhin nicht freigegeben).
3. ISIN/Anteilsklasse und MIC/Ticker/Währung/Gültigkeitszeitraum getrennt modellieren;
   ISIN-Mappingrechte und Quellen pro Markt verifizieren. Bisher kein globaler Sollbestand.
   SEC-Ticker-Klassifikation (Gattung, ETF-Mehrklassenserien, N-CEN-Schema-3.1-Lücke) bleibt
   daneben offen (unverändert aus D-033).

## Weiterhin offen

Kein vollständiger weltweiter Aktien-/ETF-Katalog; keine echte Belegquelle im Screening. GLEIF-Mutterlinks
liegen als ungeklärte Hinweise vor, nicht als verifizierte Beziehungen. Keine DB-Migrationen;
vor Integration neuer Attribute ins Screening Migrationen planen. Quellenrechte technisch anhand
offizieller Bedingungen geprüft, keine externe juristische Prüfung. Persönliche Interviews und
Produkt-/Lizenzentscheidungen aus den bisherigen Strategieunterlagen bleiben offen.
Die Online-Demoseite wird nur nach ausdrücklicher Zustimmung aktualisiert. Der neue lokale
Datenbestand wird bewusst nicht in die öffentliche Website eingebaut.

Kein nachgewiesenes vollständiges SIX-Universum: Wikidata-Abdeckung ist Community-gepflegt und
lückenhaft (z. B. keine LEI bei UBS- oder Credit-Suisse-Eintrag, obwohl real vorhanden). Fonds-/
ETF-Abfrage lieferte für den Schweizer/SIX-Zuschnitt 0 Treffer; keine Aussage, dass es keine
Schweizer ETFs gibt, nur dass Wikidata sie in diesem engen Zuschnitt nicht so modelliert.
Mehrfache ISINs je Unternehmen (z. B. Stamm- und ADR-Papier) sind bewusst alle sichtbar, nicht
auf «die eine richtige» reduziert. `swiss-search`/`security_candidates.html` sind getrennt vom
SEC-Marktkatalog (`market-search`/`catalogue.html`); noch keine gemeinsame Oberfläche.
