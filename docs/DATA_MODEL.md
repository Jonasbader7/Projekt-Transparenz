# Datenmodell

## Tabellen (SQLAlchemy, `src/transparenz/database/models.py`)

| Tabelle | Zweck | Schlüssel / Verweise |
|---|---|---|
| `sources` | registrierte Quellen inkl. Lizenz, kommerzieller Nutzbarkeit, fiktiv ja/nein | `key` |
| `dataset_versions` | ein importierter Datenstand je Quelle (Hash, Abrufzeit, Datenstand, Status active/superseded, ETag) | `source_key` |
| `update_runs` | jeder Aktualisierungsversuch (Status, Versuche, Fehler, Warnungen, Rohdatei) | `source_key`, `dataset_version_id` |
| `funds` | Fonds (ISIN, Name, Anbieter, Stichtag) | `dataset_version_id` |
| `holdings` | Positionen (Wertpapier-ISIN, Name, Anlageklasse, Gewicht) | `fund_isin` |
| `companies` | Unternehmen / Rechtsträger (`company_key`, Name, LEI) | `company_key` |
| `securities` | Wertpapier → Emittent, mit Methode, Vertrauen und Quelle der Zuordnung | `isin` → `company_key` |
| `company_relationships` | Mutter–Tochter, **verifiziert ja/nein**, Quelle, Anteil | `parent_key`, `child_key` |
| `evidence` | Sachverhalte gemäss Belegmodell | Name/LEI/ISIN wie in der Quelle |
| `coverage` | welche Quelle welches Unternehmen für welches Kriterium geprüft hat | Name/LEI/ISIN |

Alle Datentabellen hängen an einer `dataset_version`. Gelesen wird nur, was zu einer aktiven
Version gehört. Verweise laufen über fachliche Schlüssel (ISIN, `company_key`), damit
Versionen einzelner Quellen unabhängig ausgetauscht werden können.

**ISIN ≠ LEI:** Die ISIN steht nur bei Wertpapieren (`holdings`, `securities`), der LEI nur bei
Rechtsträgern (`companies`). Sachverhalte tragen die Kennung, die die Quelle selbst angibt;
die Zuordnung passiert erst beim Screening und wird mit Methode und Vertrauen ausgewiesen.

## Internes Austauschformat (Version 1)

Echte Quellen werden später von eigenen Adaptern in dieses Format übersetzt.

### Positionsliste – CSV (eine Datei = ein Fonds, ein Stichtag)

Pflicht: `fund_isin, fund_name, fund_provider, fund_as_of_date, position_name, asset_class, weight_pct`
Optional: `fund_currency, fund_is_fictional, fund_description, position_isin, country, currency`

- Komma oder Semikolon als Trennzeichen, UTF-8 (auch mit BOM aus Excel)
- Gewicht in Prozent, Dezimalpunkt oder -komma («4,5»)
- `asset_class`: aktie, anleihe, barmittel, derivat, sonstige
- Fondsangaben wiederholen sich in jeder Zeile und müssen identisch sein

### Stammdaten – JSON

`{"companies": [...], "securities": [...], "relationships": [...]}` – Felder siehe
`entities/models.py` (`CompanyRecord`, `SecurityRecord`, `RelationshipRecord`).

### Sachverhalte – CSV

Spalten: `evidence_id, company_name, lei, isin, criterion, description, evidence_type,
proceeding_status, publisher, publisher_type, source_title, source_url, published_date,
event_date, verification_level, last_reviewed, metric_name, metric_value, metric_unit`

### Abdeckung – CSV

Spalten: `company_name, lei, isin, criterion, reviewed_date`

## Fiktive Beispieldaten

Erzeugt mit `python scripts/generate_sample_data.py` (deterministisch). Alle Namen,
Herausgeber und Kennungen sind erfunden: ISIN-Präfix `ZZ` (kein reales Land), LEI-Präfix
`FIKT00`, Links auf `example.org`. Die Daten decken gezielt alle Fälle ab:

| Position | Fall |
|---|---|
| Tiefsee Öl & Gas | behördliche Feststellung, geprüft → festgestellt; Medienbericht nur über ISIN; Stellungnahme |
| Waldland Agrar | Gerichtsurteil → festgestellt; NGO-Vorwurf; Abhilfe (verrechnet nicht) |
| Präzisionstechnik | Beleg nur bei der **verifizierten** Muttergesellschaft; Entscheid noch nicht von uns geprüft |
| Muster Textil | Beschwerde bei Kontaktstelle laufend; NGO-Vorwurf; Stellungnahme |
| Alpenstrom (Aktie + Anleihe) | Ausschlussentscheid + NGO → dokumentiert; Kennzahl ohne Schwellenwert |
| Grüne Logistik | Beleg nur bei **unverifizierter** Muttergesellschaft → nicht übernommen, Hinweis |
| Kakao Handel | zwei Medienberichte, nur über Namen zuordenbar → Zuordnung unsicher |
| Bahnbau | Wertpapier nur per Namensähnlichkeit zugeordnet → Zuordnung unsicher |
| Datenwolke | von keiner Quelle abgedeckt → unbekannt |
| Unbekannte Beteiligung | ISIN nicht in Stammdaten → Emittent nicht identifiziert |
| Barmittel, Devisentermin | nicht anwendbar |
| (keine Position) | Sachverhalt zu unbekannter Firma; Namensvetter mit anderem LEI → nicht zugeordnet |
| (Belegsammlung) | absichtliches exaktes Duplikat → wird erkannt und entfernt |
