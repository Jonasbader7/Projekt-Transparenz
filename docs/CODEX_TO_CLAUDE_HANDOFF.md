# Codex → Claude Code: Schweizer Rohdatenfundament

Stand: 08.11.2026. Zuerst diese Datei und STATUS.md lesen. Keine erneute Grundrecherche nötig.

## Neuer Auftrag und SEC-Katalog (D-033)

Jonas möchte **alle weltweit börsenkotierten Aktien und ETFs**. Erster echter Teilbestand
steht lokal: `market-update` und `market-search`. Zuerst `docs/GLOBAL_MARKET_CATALOG.md` lesen;
44'085 Katalogeinträge, 4'168 durch historische Ein-Klassen-Meldung belegte ETF-Klassen,
keine Welt-Vollständigkeit. SEC-Kontakt nur lokal autorisiert in ignorierter `.env`.
Separate `markets.sqlite`/`market_sources.toml`; alte Schweizer Zahlen unten sind unverändert.
200 Tests und Offline-Audit bestanden; HTML visuell durch Browser-Dateiprotokollsperre ungeprüft.
Nicht erneut auf sechs Schweizer Rechts-/ETF-Quellen zurückstufen: weltweite Börsenabdeckung,
weitere freigegebene Länderquellen, Aktiengattung und ISIN-/Listing-Identität sind die nächsten
Schritte. FIRDS/Nasdaq/TickerInside-Upstream nicht pauschal freigeben; Rechteprüfung siehe Quellen.

## 1. Tatsächlich erledigt

Bestehende Architektur erweitert, keine neuen Frameworks, keine Webdesignänderung.
`swiss-update` verwendet DataUpdateManager mit separatem Katalog und separater SQLite-DB.
Originaldateien, Lizenzregister, Hashprüfung, Cache, Rate-Limit, Quarantäne, atomare
Versionsaktivierung, Identitätsfusion und lokale JSON-Exporte sind implementiert und gelaufen.
Ein OS-Dateilock verhindert parallele grosse Läufe. Keine Veröffentlichung, kein Push.

Ergebnis: **801'647 Rechtseinheiten**, davon **801'626 ohne Kennungskonflikt**;
**0 bestätigte Wertpapiere**, **3'254 Fondsrechtsträger**, **0 ETF-Anteilsklassen mit ISIN**,
**0 Fondspositionen**, **247 SwissPRTR-Standorte**. Registereinheiten sind nicht nur
Aktiengesellschaften. Die Fondsanzahl ist ausdrücklich kein ETF- oder Anteilsklassenkatalog.

## 2. Funktionierende Quellen

- `gleif_ch`: alle 28'495 API-Treffer des Filters Schweizer Rechtsadresse, Datenstand 08.11.2026.
  25'121 Rechtsträger + 3'254 FUND + 118 Statusausschlüsse + 2 ungültige LEIs in Quarantäne.
  Cursor-Paginierung nötig; Seitenpaginierung endet technisch bei 10'000. Snapshotdatum,
  eindeutige LEIs und API-Gesamtzahl werden geprüft.
- `zefix_lindas`: 796'684 validierte Einheiten. Amtliche Kontrollabfrage: 796'690;
  sechs Originaleinheiten sind zurückgehalten (ungültige UID oder widersprüchliche Register-IDs).
  Mehrsprachige Namen derselben Register-ID sind Varianten, keine Dubletten.
- `swissprtr`: STAC + GeoPackage, 247 Standorte zum 31.12.2024. Amtliche Asset-Checksumme
  geprüft. Original-XLSX mit Emissionen 2007–2024 (3'106'306 Bytes) normalisiert (D-032, Claude-
  Session): 22'860 Zeilen, davon 16'058 Punktquellen über die im XLSX gemeldete,
  prüfzifferngeprüfte Betriebs-UID exakt einem Rechtsträger zugeordnet; Details in STATUS.md.
- `wikidata_ch`: vorbereitet und synthetisch getestet, **nicht live funktionsfähig: HTTP 403**.
  Im Standardlauf deaktiviert mit sichtbarem Grund, manuell über `--source wikidata_ch` prüfbar.
  Kein Hostwechsel und keine Sperrumgehung. Abfragen in `data/queries/`.

## 3. Originale und abgeleitete Daten

- `data/raw/external/<source>/objects/<sha256>.<format>`: unveränderte HTTP-Antworten;
  `<datei>.metadata.json`: URL, UTC-Abrufzeit, Rechte/Prüfdatum, Grösse, Format, Hash, HTTP-Validatoren.
- `data/raw/external/<source>/cache/`: 24h-URL-Cache, später ETag/Last-Modified.
- `data/raw/external/manifests/<source>/`: aktivierte/rejektierte Manifestversionen.
  Manifest enthält Quellenstichtag, Abdeckung und Verweise auf Originale.
- `data/raw/external/license_evidence/`: offizielle CKAN-Ressourcenmetadaten.
- `data/processed/swiss.sqlite`: bestehende Tabellen und Updatehistorie, getrennt von Demo.
- `data/processed/swiss/current.json`: **massgeblicher Zeiger** auf fertige Exportgeneration.
  Dort `companies.json`, `identified_companies.json`, `funds.json`, `securities.json`,
  `facilities.json`, `quality_report.json` und die separaten Prüflisten.
- `data/processed/swiss/latest_status.json`: aktuelle Lauf-/Lizenzmeldungen; das
  `quality_report.json` einer Generation bleibt deren unveränderlicher Erstellungsstand.
- Prüflisten: 13'189 mögliche Namensdubletten-Gruppen, 10 Kennungskonflikt-Gruppen,
  776'526 Einheiten ohne LEI, 50'242 ungeklärte Mutter-/Reporting-Exception-Hinweise,
  8 Quarantäneeinträge. Ausnahmebericht ist kein Beleg einer tatsächlichen Mutter.

Alle echten Daten, temporären Dateien und DBs sind Git-ignoriert. Nur Code, synthetische
Tests, Konfiguration, Abfragen und Dokumentation dürfen ins öffentliche Repo gelangen.
Kein Starterkit im Projekt/Downloads unter einschlägigen Dateinamen gefunden; ohne fortgefahren.

## 4. Rechte

Prüfdatum 08.11.2026: GLEIF CC0, Wikidata strukturierte Daten CC0, Zefix Linked Data Query
terms_open, SwissPRTR terms_by. Interne kommerzielle Verarbeitung, Speicherung, Ableitungen
und Redistribution jeweils freigegeben. Bei OGD ist die Einordnung von Speicherung,
Ableitung und Weitergabe aus der offenen Nutzung ausdrücklich dokumentiert.
SwissPRTR verlangt BAFU + Titel + Link; Attribution wird bis in den Qualitätsbericht mitgeführt.
Offizielle Lizenz-/Bedingungs-URLs in `config/swiss_sources.toml` und `docs/DATA_SOURCES.md`.
Die Sperre läuft nach 365 Tagen ab. Kein ANNA-ISIN-Mapping unter pauschalem GLEIF-CC0 laden.

Gesperrte Kandidaten mit fünf getrennten Rechtefeldern und Grund:
`src/transparenz/config/source_reviews.json`. SIX kommerziell nicht freigegeben;
OpenSanctions erfordert kommerzielle Datenlizenz; Fondsanbieter/ANNA/SECO noch nicht ausreichend
geklärt; Climate TRACE hat Drittquellen-Ausnahmen. Unternehmensvorwürfe nicht importiert.

## 5. Noch fehlend

Kein nachgewiesenes vollständiges Schweizer Aktien-/SIX-/ETF-Universum. Keine bestätigten
ISIN→Emittent-Zuordnungen. Fondsanbieter, Index, Nachhaltigkeitslabel und Anteilsklassen fehlen.
Die SwissPRTR-Standortdatei (GeoPackage) enthält weiterhin keine UID, deshalb 0 Firmenzuordnungen
über das Standortregister selbst. Die Emissionen (normalisiert, siehe unten) tragen ihre eigene
UID und erreichen dadurch eine deutlich höhere, aber nicht vollständige Zuordnungsquote; 5'298
Punktquellen-Zeilen mit gültiger UID finden keinen passenden Rechtsträger (z. B. historische
oder nicht in GLEIF/Zefix erfasste Betriebe) und bleiben ungeklärt. Keine Emissions-/
Vorwurfsdaten automatisch einem Mutterkonzern zugerechnet.

## 6. Befehle

```powershell
cd "C:\Users\Bader\OneDrive\Desktop\Projekt Transparenz"
.venv\Scripts\python -m transparenz swiss-update
.venv\Scripts\python -m transparenz swiss-update --source gleif_ch
.venv\Scripts\python -m transparenz swiss-update --source zefix_lindas
.venv\Scripts\python -m transparenz swiss-update --source swissprtr
.venv\Scripts\python -m transparenz swiss-update --export-only
.venv\Scripts\python -m pytest -q --basetemp data/cache/pytest-claude
.venv\Scripts\python -m ruff check .
```

Standardlauf überspringt die bekannte Wikidata-Sperre mit sichtbarem Hinweis. Der explizite
Versuch `--source wikidata_ch` meldet bei HTTP 403 weiterhin Exitcode 1. Erfolgreiche Quellen
bleiben gültig. Unveränderte aktive Datenversionen verwenden den fertigen Export weiter;
keine erneute Rohdatenverarbeitung oder Kopie grosser Dateien. `--force` ignoriert das
Managerintervall, nicht den 24h-Rohdaten-Cache. `--export-only` baut ausdrücklich vollständig
ohne Netzwerk neu auf und kann mehrere Minuten dauern. Bei Änderungen an Parser-/Fusionssemantik
`EXPORT_SCHEMA_VERSION` in `swiss_foundation.py` erhöhen, damit alte Exporte neu entstehen.
Mehrere GB freien Speicher vorhalten; grosse Läufe werden per OS-Lock serialisiert.

## 7. Tests

Vor Änderung: 151 bestanden. Nach der Codex-Session: **172 bestanden (11.02s)**;
`ruff check .` bestanden. Nach der SwissPRTR-Emissionsnormalisierung (Claude-Session,
08.11.2026): **183 bestanden**, Ruff weiterhin sauber; 4 neue Tests decken die XLSX-
Normalisierung (Pflichtspalten, Punkt-/Nicht-Punktquelle, ungültige UID-Prüfziffer) und die
End-to-End-Verknüpfung Emission → Rechtsträger über die validierte Betriebs-UID ab.
Zusätzlich wird der tatsächliche Bestand mit `python scripts/audit_swiss_foundation.py`
offline geprüft (jetzt inkl. Emissionszahlen und Zuordnungsquote); Ergebnis in
`data/processed/swiss/audit_report.json`.
Bestandsaudit bestanden: **801'647 eindeutige Unternehmensschlüssel**, gültige importierte
LEI-/UID-/ISIN-Prüfziffern, **156 Originaldateien** mit korrekten Hashes/Grössen und
**22'860 geprüfte Emissionszeilen** (16'058 einem Rechtsträger zugeordnet, 1'476 diffuse
Quellen ohne Betrieb) geprüft.
Updatehistorie: 5 erfolgreiche, 10 fehlgeschlagene (weiterhin nur Wikidata-403-Versuche),
mehrere übersprungene Versuche; **0 offene laufende Versuche**.
Die Fehlerhistorie dokumentiert Erprobung/Abbrüche und den weiterhin blockierten Wikidata-Zugang.
Getestet sind u. a. fünf Lizenzrechte, Rohdatenintegrität, Quarantäne, mehrsprachige
Registeridentitäten, UID-Konflikte, ausschliessliche Kennungsfusion, Cache/403, fehlende
Paginierungsseiten, unveränderte Versionen, Fehler-Rollback und parallele Schreibsperre.
Vollständige App-Tests ausserhalb der Sandbox ausführen; der Sandbox-Lauf blieb hängen.

## 8. Fehler/Risiken

Historische fehlgeschlagene Versuche sind absichtlich protokolliert: GLEIF-Paginierung,
ungültige Originalkennungen, mehrsprachige Zefix-Namen, echte UID-Konflikte, Windows-Dateisperre
beim GeoPackage. Die Ursachen wurden behandelt; Rohdateien bleiben erhalten.
Zefix ist kein atomarer Gesamtsnapshot. Zwei gleichzeitige grosse Exporte überlasteten
den Speicher; abgebrochen und anschliessend einzeln exportiert, OS-Lock ergänzt.
Aufbewahrung/Platzbedarf ist noch nicht begrenzt. Rohdaten nicht löschen, bevor eine
Aufbewahrungspolitik feststeht. Bei Schemaerweiterungen Migrationen planen.
Die Demo-/Screeningdatenbank bleibt separat; kein `build-site` mit echten Rohdaten.

## 9. Drei nächste Aufgaben

1. Regulären Wikidata-Zugang herstellen und vorbereitete Adapter live prüfen; ein kommerziell
   offenes Referenzuniversum für Kotierungen zur Abdeckungsmessung erschliessen.
2. Die 5'298 SwissPRTR-Punktquellen-Emissionen mit validierter UID ohne passenden Rechtsträger
   stichprobenweise prüfen (historische/nicht erfasste Betriebe); amtliche Quelle für eine
   Betreiber-UID im Standortregister selbst suchen (GeoPackage hat aktuell keine UID-Spalte).
3. Konkrete Schweizer/UCITS-ETF-Metadaten und anschliessend Positionen mit vollständigen
   kommerziellen Rechten beschaffen; Anteilsklassen und Emittentenmodell ergänzen.

## 10. Fertiger Prompt

> Lies CLAUDE.md, STATUS.md und docs/CODEX_TO_CLAUDE_HANDOFF.md. Führe das lokale Schweizer
> Datenfundament weiter, ohne die bestehende Architektur oder Website neu zu entwickeln.
> Prüfe zuerst den aktuellen Qualitätsbericht über data/processed/swiss/current.json.
> Priorisiere regulären Wikidata-Zugang und ein freigegebenes Aktien-/ETF-Referenzuniversum,
> danach SwissPRTR-Normalisierung. Nutze nur nachgewiesen kommerziell nutzbare Quellen,
> fusioniere nie über Firmennamen und veröffentliche oder pushe nichts ohne meine Zustimmung.
