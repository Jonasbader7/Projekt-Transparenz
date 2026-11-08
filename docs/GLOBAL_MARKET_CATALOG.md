# Weltweiter Aktien- und ETF-Katalog: Bestand und Ausbau

Stand 08.11.2026. Ziel von Jonas: alle weltweit börsenkotierten Aktien und ETFs.
**Dieses Ziel ist noch nicht erreicht.** Der ausführbare lokale Katalog startet mit
freigegebenen SEC-Daten. Keine Veröffentlichung und keine kostenpflichtige Datenquelle.

## Was jetzt sichtbar ist

`market-update` erzeugt eine lokale HTML-Datei mit Suche, Typfilter, Seitenwechsel und
Originalnachweisen. Sie enthält 44'085 Katalogeinträge:

| Eintragsart | Anzahl | Bedeutung |
|---|---:|---|
| ETF, durch Ein-Klassen-Meldung belegt | 4'168 | Serie meldet `IS_ETF=Y` und genau diese eine Anteilsklasse im N-CEN-Bericht |
| Anteilsklassen einer ETF-Serie, einzeln offen | 212 | mehrere Klassen in derselben Serie; insbesondere keine pauschale Klassifikation von Vanguard-Publikumsfonds als ETFs |
| Fonds-Anteilsklasse, Typ offen | 29'284 | inklusive Publikumsfonds und historisch gemeldeter Klassen; keine Börsenkotierung garantiert |
| Identitätskonflikt | 2 | dieselbe Class-ID mit widersprüchlichem Registrant/Serie, keine willkürliche Fusion |
| SEC-Ticker-/Börsenzuordnung, Typ offen | 10'419 | enthält Aktien, aber auch andere Instrumente; nicht pauschal als Aktien gezählt |

Die Summe zählt **Katalogeinträge, keine weltweit eindeutigen Wertpapiere**. Ein Ticker-Eintrag
und eine Fonds-Anteilsklasse können dasselbe Papier betreffen. `AAPL` findet Apple; `VTI` und
`VOO` zeigen bewusst den offenen Anteilsklassenstatus der Mehrklassenserie. `SPY` steht in der
SEC-Tickerliste, ist durch diese Quelle allein aber noch nicht als ETF klassifiziert.

## Benutzung

```powershell
cd "C:\Users\Bader\OneDrive\Desktop\Projekt Transparenz"
.venv\Scripts\python -m transparenz market-update
.venv\Scripts\python -m transparenz market-search Apple
.venv\Scripts\python -m transparenz market-search VTI
.venv\Scripts\python scripts/audit_market_catalog.py
```

Der Updatebefehl gibt den vollständigen Pfad zu `catalogue.html` aus. Im Explorer doppelklicken.
Alternativ: `data/processed/market/current.json` nennt den aktuellen Unterordner in `generations/`.
Die HTML-Datei braucht keinen Server und keine externen Bibliotheken; sie ist derzeit ca. 48 MB.
`--source sec_ncen` aktualisiert nur die Fondsmeldungen; `--export-only` arbeitet ohne Netzwerk.
`--force` ignoriert das Updateintervall, der 24h-Rohdaten-Cache bleibt wirksam.

Kontakt-E-Mail: ausschliesslich lokal in `.env` als `TRANSPARENZ_SEC_CONTACT`. Der Nutzer hat
die Verwendung im SEC-HTTP-User-Agent ausdrücklich erlaubt. Sie erscheint weder im
Quellenkatalog noch in Original-Metadaten oder Git. Keine E-Mail-Nachrichten werden versandt.

## Datenmodell und Herkunft

- `market_sources.toml`, `DataUpdateManager`, separate `data/processed/markets.sqlite`.
- Rohdateien in `data/raw/external/sec_*/objects/`, unverändert mit SHA-256, Abrufzeit,
  offiziellen URLs und geprüftem Lizenzregister. Aktivierungsmanifeste wie beim Schweizer Import.
- `market_records` enthält validierte Quellenbeobachtungen. Der bestehende ISIN-basierte
  Screening-Bestand wird nicht mit unbestätigten Ticker-Einträgen gefüllt.
- CIK = Registrant; Serien-ID = Fondsserie; Class-ID = Anteilsklasse. Keine Fusion über Name,
  Ticker allein oder den gemeinsamen Registranten. Keine synthetischen ISINs/LEIs.
- Für jede Serie wird der jüngste Berichtszeitraum, dann das jüngste Einreichungsdatum gewählt.
  Gleichrangige Meldungen bleiben ungeklärt. Eine im jüngsten Bericht fehlende Klasse erbt
  keinen älteren ETF-Nachweis. Berichtsdatum und Abrufzeit bleiben getrennt.
- Vier zuletzt verfügbare N-CEN-Quartale: 2025Q4 bis 2026Q3. Jährliche Meldungen sind
  historische Selbstauskünfte. Laut SEC fehlen im Bulkbestand Meldungen nach Schema 3.1.
- Ungewöhnliche gemeldete Serienkennungen (z. B. `CEF0000002`) und Platzhalter werden als
  Originalangaben erhalten, nicht in gültige SEC-Serien-/Class-IDs umgedeutet.

## Was für «alle weltweit» noch fehlt

| Baustein | Status und konkrete nächste Arbeit |
|---|---|
| Börsen-Referenzuniversum je Markt/MIC | nicht vorhanden; ohne Soll-Liste kein belastbarer Vollständigkeitsprozentsatz |
| Aktienklassifikation der SEC-Ticker | zusätzliche amtliche Gattung/Klasse erforderlich; Warrants, Units, Notes, ADRs und Fonds unterscheiden |
| Schweizer und europäische Kotierungen | SIX selbst weiterhin nicht freigegeben; **Wikidata CC0 liefert seit D-034 einen Teilbestand** (293 Kandidaten, u. a. Roche, Nestlé, Novartis, UBS, ABB) über `swiss-update --source wikidata_ch` / `swiss-search`, getrennt von diesem SEC-Katalog, siehe `docs/DATA_SOURCES.md` |
| Asien/Pazifik, Amerika ausserhalb SEC, Afrika/Nahost | noch keine integrierten Quellen; Börsen und Länder einzeln erschliessen |
| Instrument ↔ Listing | ISIN und Anteilsklasse getrennt von MIC, lokalem Ticker, Währung, Listing-Status und Gültigkeitszeitraum |
| ETF-Mehrklassenserien / UITs / neue Fonds | zusätzliche Meldungen nötig; N-CEN alleine deckt sie nicht vollständig ab |
| Pflege | Delistings, Umbenennungen, neue Klassen, Corporate Actions und Quellen-Ausfälle nachvollziehbar verarbeiten |

Nächste Quellenkandidaten sind CVM Brasilien (amtliches Fondsregister unter ODbL;
Share-Alike und Anteilsklassenmodell vor Integration konkret prüfen) sowie FSMA Belgien
(eigene Website-Informationen CC BY 4.0; eine passende Instrumentdatei noch auswählen).
Sie sind **noch nicht importiert** und werden nicht als Marktabdeckung gezählt.

Soll ein kommerzieller Gesamtkatalog eingesetzt werden, zuerst ein konkretes Angebot mit
Aktien/ETF-Abdeckung, Anteilsklassen, Listings, Delistings sowie ausdrücklichen Speicher-,
Ableitungs- und Weitergaberechten prüfen. Es wurde nichts bestellt oder bezahlt.

## Prüfstand

17 neue Regressionstests zu Identität, zeitlicher Auswahl, Mehrklassenserien, Rohdatenhash,
Pfadgrenzen, Lizenzsperre, fehlendem Kontakt, Versionsschutz und HTML-Escaping. Offline-Audit
prüft Originalhashes, aktive Versionen und jeden der 4'168 ETF-Nachweise nochmals direkt gegen
die unveränderten TSV-Tabellen. JavaScript-Syntax mit `node --check` geprüft. Die visuelle
Browserprüfung konnte nicht stattfinden: lokale `file:`-URLs sind im integrierten Browser
gesperrt. Keine Umgehung und deshalb keine Behauptung einer visuellen Endprüfung.
