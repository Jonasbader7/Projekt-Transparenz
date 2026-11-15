# Automatische Datenpflege

Stand 11.11.2026: **Zeitplan aktiv.** Task `ProjektTransparenz-DailyDataUpdate` registriert
(täglich 09:00 + bei Anmeldung); der frühere CIM-Zugriffsfehler bei der Registrierung trat in
dieser Sitzung nicht mehr auf. Realer Testlauf erfolgreich, inkl. der global/CVM-Downloads, die
zuvor an DNS gescheitert waren (siehe STATUS.md für die aktuellen Zahlen).

## Einmalig auf dem PC ausführen

```powershell
Set-Location 'C:\Users\Bader\OneDrive\Desktop\Projekt Transparenz'
& .\scripts\install_autonomous_update.ps1
& .\.venv\Scripts\python.exe .\scripts\autonomous_update.py
```

Die erste Zeile wählt das Projekt. Der Installer registriert einen Task für täglich 09:00
Schweizer Ortszeit auf diesem PC sowie beim Anmelden. Er läuft mit Benutzerrechten ohne
Passwortspeicherung und ohne sichtbares Konsolenfenster. Der PC muss laufen und der Benutzer
angemeldet sein; verpasste Läufe werden nach Möglichkeit nachgeholt. Kein Serverbetrieb bei
ausgeschaltetem PC. Zwei Wiederholungen im Abstand von 30 Minuten bei Fehlern.

## Was der Lauf macht

Nacheinander, mit Prozesssperre gegen doppelte Automatikläufe:

1. Globale Wikidata-Börsen-/Ticker-Kandidaten (CC0, wöchentlich) und CVM-Firmenregister
   (ODbL, täglich) als separate, validierte Recherche-Schnappschüsse herunterladen.
2. `market-update`: bestehende SEC-Ticker-/Fondsklassen täglich, N-CEN gemäss Quellenintervall.
3. `swiss-update`: Schweizer Register/Wikidata wöchentlich, SwissPRTR monatlich gemäss
   vorhandener Konfiguration. Unveränderte Exporte werden wiederverwendet.

SEC-/Schweizer Aktualisierungen verwenden die bestehende Validierung, Quarantäne,
Versionsaktivierung und Exportlogik. Neue gültige Quelleneinträge werden beim Quellenlauf
automatisch berücksichtigt, keine handgepflegte Firmen-Whitelist. Ungültige Updates ersetzen
den letzten gültigen Quellenstand nicht. Änderungen/Entfernungen richten sich nach den
Quellen; keine eigenständige Bestätigung von Delistings.

Globale Wikidata-/CVM-Downloads bleiben **Recherchebestände**, noch nicht im `market-search`,
`swiss-search` oder Screening eingebaut. Sie enthalten keine vollständige bestätigte
Welt-Aktienliste. Wikidata kann veraltete/fehlerhafte Börsenangaben enthalten; CVM-Registrierung
ist kein Kotierungsnachweis. Die nächste Integration muss diese Identitäten separat erhalten.
Weder automatische Veröffentlichung noch Push oder kostenpflichtige APIs.

Status: `data/processed/automation/latest.json`, Downloadstatus: `download_status.json` im
gleichen Ordner; datierte Protokolle pro Teiljob. Jeder Teiljob wird trotz Fehlern anderer
Jobs versucht. Maximal drei Stunden je Job. Rohdateien mit Hash-/Lizenz-/Zeit-Metadaten:
`data/raw/external/wikidata_global/` und `cvm_companies/`. Alte Snapshots bleiben erhalten;
Speicherplatz/Aufbewahrung ist weiterhin zu beobachten, noch keine automatische Löschung.

## Quellen und direkte Abrufziele

| Quelle | Abruf / Bedingungen |
|---|---|
| Wikidata weltweit | [SPARQL-Endpunkt](https://query.wikidata.org/sparql), feste Query in `scripts/download_global_candidates.py`; [strukturierte Daten CC0](https://www.wikidata.org/wiki/Wikidata:Licensing). P414 mit zugehörigem P249-Ticker, ohne bekanntes Enddatum, nicht veralteter Rang. Fehlendes Enddatum garantiert keine aktuelle Kotierung. |
| CVM börsenoffene Firmen | [CSV](https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/DADOS/cad_cia_aberta.csv); [Ressource mit ODbL-Lizenz](https://dados.cvm.gov.br/dataset/cia_aberta-cad/resource/2391143f-1423-48a5-9f6a-423245aca362). Nur separater Roh-/Recherchebestand, Weitergabepflichten vor Produktintegration umsetzen. |
| SEC Firmen-/Börsenticker | [JSON](https://www.sec.gov/files/company_tickers_exchange.json), bereits integriert. |
| SEC Fonds-/Anteilsklassen | [JSON](https://www.sec.gov/files/company_tickers_mf.json), bereits integriert; nicht jede Klasse ein ETF. |
| SEC N-CEN | [Datensätze](https://www.sec.gov/data-research/sec-markets-data/form-n-cen-data-sets), bereits integriert. |
| Schweizer Quellen | GLEIF, Zefix/LINDAS, Wikidata CH und SwissPRTR: exakte URLs/Lizenzen in `src/transparenz/config/swiss_sources.toml` und `docs/DATA_SOURCES.md`. |

JPX, B3 und weitere Börsenverzeichnisse wurden nicht pauschal als kommerziell frei
heruntergeladen. Für diese gilt die dokumentierte Rechteprüfung.

Task prüfen: `Get-ScheduledTask -TaskName 'ProjektTransparenz-DailyDataUpdate'`.
Anhalten: `Disable-ScheduledTask -TaskName 'ProjektTransparenz-DailyDataUpdate'`.
