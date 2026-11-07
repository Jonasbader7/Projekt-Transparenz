# Datenquellen

**Stand 07.11.2026.** Angebunden sind ausschliesslich fiktive Demoquellen. Die Angaben zu den
echten Kandidaten stammen aus Vorwissen und sind **nicht verifiziert**. Vor jeder Anbindung:
Nutzungsbedingungen lesen, Lizenz festhalten, kommerzielle Nutzbarkeit klären, Ergebnis hier
eintragen. Öffentlich zugänglich heisst nicht kommerziell nutzbar.

Statuswerte: **aktiv** · **geplant** · **zu prüfen** (Lizenz/Zugang unklar) · **verworfen**

## Aktive Quellen

| Quelle | Zweck | Format | Lizenz | Kommerziell | Status |
|---|---|---|---|---|---|
| Fiktiver ETF «Muster Nachhaltigkeit Welt» | Positionen | CSV | fiktiv, frei | ja | aktiv (Demo) |
| Fiktive Stammdaten | Unternehmen, Wertpapiere, Konzern | JSON | fiktiv, frei | ja | aktiv (Demo) |
| Fiktive Ausschlussliste «Ethikrat» + Abdeckung | Ausschlussentscheide | CSV | fiktiv, frei | ja | aktiv (Demo) |
| Fiktive Belegsammlung + Abdeckung | Sachverhalte versch. Herausgeber | CSV | fiktiv, frei | ja | aktiv (Demo) |

## Kandidaten für echte Quellen

URLs sind Einstiegsseiten; die genaue Datenseite wird beim Onboarding verifiziert.

### Fondspositionen

| Quelle | Zweck | URL | Format | Aktualität | Lizenz | Kommerziell | Status |
|---|---|---|---|---|---|---|---|
| iShares (BlackRock) | Positionen iShares-ETFs | https://www.ishares.com | CSV/XLS-Download je Produkt | meist täglich | Website-Nutzungsbedingungen | unklar | zu prüfen |
| UBS ETF | Positionen UBS-ETFs | https://www.ubs.com | Download je Produkt | regelmässig | Website-Nutzungsbedingungen | unklar | zu prüfen |
| Xtrackers (DWS) | Positionen Xtrackers-ETFs | https://etf.dws.com | Download je Produkt | regelmässig | Website-Nutzungsbedingungen | unklar | zu prüfen |
| SEC EDGAR (Form N-PORT) | Positionen US-Fonds | https://www.sec.gov/edgar | XML/API | quartalsweise (verzögert) | US-Behördendaten; Fair-Access-Regeln (User-Agent, Rate-Limit) | vermutlich ja | zu prüfen |
| Halbjahres-/Jahresberichte | vollständige Positionen zum Stichtag | Anbieter-Websites | PDF | halbjährlich | Urheberrecht des Anbieters | unklar | zu prüfen |

### Identifikation

| Quelle | Zweck | URL | Format | Aktualität | Lizenz | Kommerziell | Status |
|---|---|---|---|---|---|---|---|
| GLEIF | LEI, Rechtsträger, Mutter-Tochter (Level 2) | https://www.gleif.org | API (JSON), Golden-Copy-Dateien | mehrmals täglich | nach Vorwissen CC0 | vermutlich ja | geplant (rechtlich am klarsten) |
| OpenFIGI | ISIN → Instrument/Emittent | https://www.openfigi.com | API (JSON) | laufend | eigene Nutzungsbedingungen | unklar | zu prüfen |
| Wikidata | Namen, Konzernbezüge, Ergänzungen | https://www.wikidata.org | SPARQL/JSON | laufend | CC0 | ja | geplant (nur ergänzend, Qualität schwankt) |

### Ausschlüsse und Kontroversen

| Quelle | Zweck | URL | Format | Aktualität | Lizenz | Kommerziell | Status |
|---|---|---|---|---|---|---|---|
| NBIM / Council on Ethics (norw. Staatsfonds) | Ausschlüsse mit begründeten Empfehlungen | https://www.nbim.no | Webseite/Liste, Empfehlungen als PDF | bei Entscheiden | Website-Bedingungen | unklar | zu prüfen (inhaltlich sehr wertvoll) |
| SVVK-ASIR | Ausschlussempfehlungen Schweizer Vorsorgeeinrichtungen | https://www.svvk-asir.ch | Liste (PDF/Web) | periodisch | unklar | unklar | zu prüfen |
| Urgewald GCEL | Kohleunternehmen inkl. Kennzahlen | https://www.coalexit.org | Excel nach Registrierung | jährlich | eigene Bedingungen | unklar | zu prüfen |
| Urgewald GOGEL | Öl/Gas inkl. Expansion | https://gogel.org | Excel nach Registrierung | jährlich | eigene Bedingungen | unklar | zu prüfen |
| Business & Human Rights Resource Centre | Vorwürfe + Unternehmensantworten | https://www.business-humanrights.org | Web | laufend | unklar | unklar | zu prüfen |
| KnowTheChain | Benchmark Zwangsarbeit | https://knowthechain.org | Berichte | periodisch | unklar | unklar | zu prüfen |
| Corporate Human Rights Benchmark (WBA) | Menschenrechts-Benchmark | https://www.worldbenchmarkingalliance.org | Berichte/Daten | periodisch | nach Vorwissen teils CC BY | unklar | zu prüfen |
| OECD-Kontaktstellen | Beschwerdeverfahren (Specific Instances) | https://mneguidelines.oecd.org | Datenbank/Web | laufend | OECD-Bedingungen | unklar | zu prüfen |
| Forest 500 (Global Canopy) | Entwaldungsrisiko Unternehmen | https://forest500.org | Bewertungen | jährlich | unklar | unklar | zu prüfen |
| Global Forest Watch | Geodaten Waldverlust | https://www.globalforestwatch.org | Geodaten | laufend | je Datensatz, oft CC BY | teilweise | zu prüfen (Verknüpfung mit Firmen schwierig) |
| OpenSanctions | Sanktionen, PEP | https://www.opensanctions.org | JSON/CSV | täglich | nach Vorwissen nicht-kommerziell frei, kommerziell lizenzpflichtig | nein (ohne Lizenz) | zu prüfen |
| Behörden- und Gerichtsentscheide | Feststellungen, Urteile | je Behörde/Gericht | PDF/Web | laufend | Schweiz: amtliche Entscheide nicht urheberrechtlich geschützt (Art. 5 URG); andere Länder prüfen | CH: vermutlich ja | geplant (manuell, Einzelfälle) |

## Regeln

- Keine unzulässigen Scraper, keine Umgehung von Zugangsbeschränkungen (Login, Captcha, Paywall).
- Ist eine Quelle unklar: Adapter mit fiktiven Testdaten bauen und dokumentieren, was fehlt.
- Daten, deren Lizenz eine Veröffentlichung ausschliesst, gehören nach `data/licensed/`
  (gitignored) und nie ins Repository.
- Jede Zuordnung (Wertpapier → Unternehmen, Tochter → Mutter) hat Quelle und Vertrauensstatus.

## Empfohlene Reihenfolge (Vorschlag, Entscheid offen)

1. **Eine echte ETF-Positionsliste** (lokal, nur zum Testen, nicht veröffentlichen) – zeigt, ob
   Format und Zuordnung in der Realität funktionieren.
2. **GLEIF** – rechtlich klar (CC0), löst die Zuordnung LEI ↔ Unternehmen und Konzernstrukturen.
3. **Eine Ausschluss-/Kontroversenquelle** (z. B. NBIM), sobald die Lizenz geklärt ist.

Erst wenn eine Quelle zuverlässig läuft (Import, Validierung, Aktualisierung), folgt die nächste.
