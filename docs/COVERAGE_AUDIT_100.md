# Abdeckungstest: 100 börsenkotierte Firmen

Prüfdatum: 08.11.2026. Projekt Transparenz. Lokaler Datenstand vom 08.11.2026.

## Ergebnis

**57 Firmen mit passendem Quellenhinweis, 43 ohne Treffer** in den beiden echten Wertpapier-Kandidatenkatalogen. Davon 50 im SEC-Katalog und 10 im Schweizer Wikidata-Bestand, mit 3 Überschneidungen. Ein Quellenhinweis ist kein bestätigtes Emittenten-/Instrumentmapping. Die öffentliche Website nutzt weiterhin Demodaten.

## Auswahl und Grenzen

Explorative, regional geschichtete Zufallsauswahl: vor dem lokalen Abgleich je 12 bekannte börsenkotierte Firmen aus 10 Märkten manuell zusammengestellt; daraus je 10 ohne Zurücklegen mit Python random.Random(20261108), in der Reihenfolge von POOLS im Skript. Vollständiger Pool und Verfahren: scripts/company_coverage_probe.py. Der Pool umfasst 120 Firmen. Keine Gleichverteilung über sämtliche Weltbörsen, keine Welt-Abdeckungsquote; kleine Firmen, Kanada, Korea, Taiwan und zahlreiche weitere Märkte fehlen im Auswahlrahmen. Die Börsen-/Index-/Emittentenlinks dienen der Kotierungsrecherche; keine vollständigen Börsendatenbanken importiert, keine Kurse übernommen. Quellenstände reichen teilweise vor das Prüfdatum zurück. Kein Nachweis der Handelbarkeit an jedem einzelnen Tag.

Geprüft werden Firmenhinweise im SEC-Wertpapierkatalog und Schweizer ISIN-Kandidaten. Die 801'732 Schweizer Registereinheiten sind kein globales Aktienuniversum und wurden nicht als Aktienabdeckung gezählt. Im bestätigten Screening-Wertpapierbestand gibt es weiterhin 0 echte Wertpapiere. ETFs sind nicht Teil dieser Firmenstichprobe.

## Prüfmethode

Akzente, Satzzeichen und explizite Namensvarianten wurden für die Recherche normalisiert. Kandidaten wurden manuell nach Firmenname und konkretem SEC-Ticker geprüft; keine automatische Identitätsfusion. Beispielsweise Apple Hospitality, Coca-Cola HBC, CSL Vifor, BYD Electronic, Siemens Energy/Healthineers und Tencent Music zählen nicht für die jeweils gesuchte Mutter-/Namensfirma. UBS ist als UBS vorhanden; Bradesco als BANK BRADESCO; Exxon Mobil als ExxonMobil Holdings Corp (XOM). Präferenzaktien, Notes und andere zusätzliche Ticker desselben Registranten werden nicht pauschal als Stammaktien gezählt.

SEC-Originalprüfung: alle 10,419 CIK-/Ticker-/Börsen-Tupel entsprechen exakt dem Export (Mengenvergleich). Keine fehlende SEC-Quellenzeile im Export. Original-SHA-256: `e1469df6a5e24ec90676d0bbd0059f857167207722b4e9952852b8f0806a9472`. Fehlende Firmen sind damit eine Abdeckungslücke des verwendeten Snapshots bzw. Quellenzuschnitts, kein hier nachgewiesener Importverlust. Kein Rückschluss, dass sie niemals SEC-Meldungen eingereicht hätten oder generell nicht OTC-gehandelt würden.

Geprüfte Exporte: `data/processed/market/generations/a4cebdd4a883748ba61e751b/catalogue.json` und `data/processed/swiss/generations/20261108T205325611928Z/security_candidates.json`. SHA-256 beider Exporte, 100 Einzelbefunde und Rohkandidaten stehen lokal in `data/processed/coverage_audit/`. Wiederholung: `.venv\Scripts\python scripts/company_coverage_probe.py`.

## Ergebnis nach Markt

| Markt | SEC-Firmentreffer | Schweizer Kandidat | Ohne Treffer |
|---|---:|---:|---:|
| USA | 10 | 0 | 0 |
| Schweiz | 3 | 10 | 0 |
| Deutschland | 5 | 0 | 5 |
| Grossbritannien | 9 | 0 | 1 |
| Japan | 6 | 0 | 4 |
| Hongkong/China | 4 | 0 | 6 |
| Indien | 3 | 0 | 7 |
| Australien | 3 | 0 | 7 |
| Brasilien | 5 | 0 | 5 |
| Südafrika | 2 | 0 | 8 |

## Alle 100 Einzelprüfungen

SEC = konkreter Firmentreffer im SEC-Snapshot, auch ADR/OTC. CH = unverifizierter Wikidata-ISIN-Kandidat. Die Referenzticker sind börsenspezifische Rechercheangaben, keine neu importierten Listings. Ein ausländischer SEC-Treffer belegt die Heimatkotierung nicht. Für jeden fehlenden Eintrag nennt die letzte Spalte den Beschaffungsweg im nächsten Abschnitt.

| Nr. | Markt | Firma / Referenzticker | SEC-Treffer | CH-Kandidat | Befund / Beschaffung |
|---:|---|---|---|---|---|
| 1 | USA | [Alphabet](https://www.sec.gov/files/company_tickers_exchange.json) · GOOGL | Alphabet Inc. · GOOGL · Nasdaq · CIK 0001652044 | — | Vorhandener Firmenhinweis |
| 2 | USA | [Amazon](https://www.sec.gov/files/company_tickers_exchange.json) · AMZN | AMAZON COM INC · AMZN · Nasdaq · CIK 0001018724 | — | Vorhandener Firmenhinweis |
| 3 | USA | [Apple](https://www.sec.gov/files/company_tickers_exchange.json) · AAPL | Apple Inc. · AAPL · Nasdaq · CIK 0000320193 | — | Vorhandener Firmenhinweis |
| 4 | USA | [Coca-Cola](https://www.sec.gov/files/company_tickers_exchange.json) · KO | COCA COLA CO · KO · NYSE · CIK 0000021344 | — | Vorhandener Firmenhinweis |
| 5 | USA | [Exxon Mobil](https://www.sec.gov/files/company_tickers_exchange.json) · XOM | ExxonMobil Holdings Corp · XOM · NYSE · CIK 0002115436 | — | Vorhandener Firmenhinweis |
| 6 | USA | [JPMorgan Chase](https://www.sec.gov/files/company_tickers_exchange.json) · JPM | JPMORGAN CHASE & CO · JPM · NYSE · CIK 0000019617 | — | Vorhandener Firmenhinweis |
| 7 | USA | [Meta Platforms](https://www.sec.gov/files/company_tickers_exchange.json) · META | Meta Platforms, Inc. · META · Nasdaq · CIK 0001326801 | — | Vorhandener Firmenhinweis |
| 8 | USA | [Procter & Gamble](https://www.sec.gov/files/company_tickers_exchange.json) · PG | PROCTER & GAMBLE Co · PG · NYSE · CIK 0000080424 | — | Vorhandener Firmenhinweis |
| 9 | USA | [Visa](https://www.sec.gov/files/company_tickers_exchange.json) · V | VISA INC. · V · NYSE · CIK 0001403161 | — | Vorhandener Firmenhinweis |
| 10 | USA | [Walmart](https://www.sec.gov/files/company_tickers_exchange.json) · WMT | Walmart Inc. · WMT · Nasdaq · CIK 0000104169 | — | Vorhandener Firmenhinweis |
| 11 | Schweiz | [ABB](https://www.six-group.com/de/market-data/indices/switzerland/equity/smi.html) · ABBN | ABB LTD · ABBNY · OTC · CIK 0001091587 | Q52825 | Vorhandener Firmenhinweis |
| 12 | Schweiz | [Alcon](https://www.six-group.com/de/market-data/indices/switzerland/equity/smi.html) · ALC | ALCON INC · ALC · NYSE · CIK 0001167379 | Q684825 | Vorhandener Firmenhinweis |
| 13 | Schweiz | [Givaudan](https://www.six-group.com/de/market-data/indices/switzerland/equity/smi.html) · GIVN | — | Q509544 | Vorhandener Firmenhinweis |
| 14 | Schweiz | [Lonza](https://www.six-group.com/de/market-data/indices/switzerland/equity/smi.html) · LONN | — | Q674216 | Vorhandener Firmenhinweis |
| 15 | Schweiz | [Nestlé](https://www.six-group.com/de/market-data/indices/switzerland/equity/smi.html) · NESN | — | Q160746 | Vorhandener Firmenhinweis |
| 16 | Schweiz | [Roche](https://www.six-group.com/de/market-data/indices/switzerland/equity/smi.html) · ROG | — | Q25463170 | Vorhandener Firmenhinweis |
| 17 | Schweiz | [Sika](https://www.six-group.com/de/market-data/indices/switzerland/equity/smi.html) · SIKA | — | Q691382 | Vorhandener Firmenhinweis |
| 18 | Schweiz | [Swiss Re](https://www.six-group.com/de/market-data/indices/switzerland/equity/smi.html) · SREN | — | Q605565 | Vorhandener Firmenhinweis |
| 19 | Schweiz | [UBS Group](https://www.six-group.com/de/market-data/indices/switzerland/equity/smi.html) · UBSG | UBS Group AG · UBS · NYSE · CIK 0001610520 | Q193199 | Vorhandener Firmenhinweis |
| 20 | Schweiz | [Zurich Insurance](https://www.six-group.com/de/market-data/indices/switzerland/equity/smi.html) · ZURN | — | Q230426 | Vorhandener Firmenhinweis |
| 21 | Deutschland | [Allianz](https://stoxx.com/index/dax/?factsheet=true) · ALV | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Deutschland |
| 22 | Deutschland | [BASF](https://stoxx.com/index/dax/?factsheet=true) · BAS | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Deutschland |
| 23 | Deutschland | [BMW](https://stoxx.com/index/dax/?factsheet=true) · BMW | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Deutschland |
| 24 | Deutschland | [Deutsche Bank](https://stoxx.com/index/dax/?factsheet=true) · DBK | DEUTSCHE BANK AKTIENGESELLSCHAFT · DB · NYSE · CIK 0001159508 | — | Vorhandener Firmenhinweis |
| 25 | Deutschland | [Deutsche Telekom](https://stoxx.com/index/dax/?factsheet=true) · DTE | DEUTSCHE TELEKOM AG · DTEGY · OTC · CIK 0000946770 | — | Vorhandener Firmenhinweis |
| 26 | Deutschland | [Infineon](https://stoxx.com/index/dax/?factsheet=true) · IFX | INFINEON TECHNOLOGIES AG · IFNNY · OTC · CIK 0001107457 | — | Vorhandener Firmenhinweis |
| 27 | Deutschland | [Mercedes-Benz](https://stoxx.com/index/dax/?factsheet=true) · MBG | DAIMLER AG · MBGAF · OTC · CIK 0001067318 | — | Vorhandener Firmenhinweis |
| 28 | Deutschland | [Münchener Rück](https://stoxx.com/index/dax/?factsheet=true) · MUV2 | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Deutschland |
| 29 | Deutschland | [SAP](https://stoxx.com/index/dax/?factsheet=true) · SAP | SAP SE · SAP · NYSE · CIK 0001000184 | — | Vorhandener Firmenhinweis |
| 30 | Deutschland | [Siemens](https://stoxx.com/index/dax/?factsheet=true) · SIE | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Deutschland; Tochter-/Namensfirmen verworfen |
| 31 | Grossbritannien | [AstraZeneca](https://www.londonstockexchange.com/en/indices/ftse-100/constituents) · AZN | ASTRAZENECA PLC · AZN · NYSE · CIK 0000901832 | — | Vorhandener Firmenhinweis |
| 32 | Grossbritannien | [BP](https://www.londonstockexchange.com/en/indices/ftse-100/constituents) · BP. | BP PLC · BP · NYSE · CIK 0000313807 | — | Vorhandener Firmenhinweis |
| 33 | Grossbritannien | [Diageo](https://www.londonstockexchange.com/en/indices/ftse-100/constituents) · DGE | DIAGEO PLC · DEO · NYSE · CIK 0000835403 | — | Vorhandener Firmenhinweis |
| 34 | Grossbritannien | [GSK](https://www.londonstockexchange.com/en/indices/ftse-100/constituents) · GSK | GSK plc · GSK · NYSE · CIK 0001131399 | — | Vorhandener Firmenhinweis |
| 35 | Grossbritannien | [HSBC](https://www.londonstockexchange.com/en/indices/ftse-100/constituents) · HSBA | HSBC HOLDINGS PLC · HSBC · NYSE · CIK 0001089113 | — | Vorhandener Firmenhinweis |
| 36 | Grossbritannien | [Lloyds Banking Group](https://www.londonstockexchange.com/en/indices/ftse-100/constituents) · LLOY | Lloyds Banking Group plc · LYG · NYSE · CIK 0001160106 | — | Vorhandener Firmenhinweis |
| 37 | Grossbritannien | [RELX](https://www.londonstockexchange.com/en/indices/ftse-100/constituents) · REL | RELX PLC · RELX · NYSE · CIK 0000929869 | — | Vorhandener Firmenhinweis |
| 38 | Grossbritannien | [Shell](https://www.londonstockexchange.com/en/indices/ftse-100/constituents) · SHEL | Shell plc · SHEL · NYSE · CIK 0001306965 | — | Vorhandener Firmenhinweis |
| 39 | Grossbritannien | [Tesco](https://www.londonstockexchange.com/en/indices/ftse-100/constituents) · TSCO | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Grossbritannien |
| 40 | Grossbritannien | [Unilever](https://www.londonstockexchange.com/en/indices/ftse-100/constituents) · ULVR | UNILEVER PLC · UL · NYSE · CIK 0000217410 | — | Vorhandener Firmenhinweis |
| 41 | Japan | [Fast Retailing](https://indexes.nikkei.co.jp/en/nkave/index/component) · 9983 | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Japan |
| 42 | Japan | [Honda Motor](https://indexes.nikkei.co.jp/en/nkave/index/component) · 7267 | HONDA MOTOR CO LTD · HMC · NYSE · CIK 0000715153 | — | Vorhandener Firmenhinweis |
| 43 | Japan | [Mitsubishi UFJ Financial](https://indexes.nikkei.co.jp/en/nkave/index/component) · 8306 | MITSUBISHI UFJ FINANCIAL GROUP INC · MUFG · NYSE · CIK 0000067088 | — | Vorhandener Firmenhinweis |
| 44 | Japan | [Nintendo](https://indexes.nikkei.co.jp/en/nkave/index/component) · 7974 | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Japan |
| 45 | Japan | [Recruit Holdings](https://indexes.nikkei.co.jp/en/nkave/index/component) · 6098 | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Japan |
| 46 | Japan | [SoftBank Group](https://indexes.nikkei.co.jp/en/nkave/index/component) · 9984 | SOFTBANK GROUP CORP. · SFTBF · OTC · CIK 0001065521 | — | Vorhandener Firmenhinweis |
| 47 | Japan | [Sony Group](https://indexes.nikkei.co.jp/en/nkave/index/component) · 6758 | Sony Group Corp · SONY · NYSE · CIK 0000313838 | — | Vorhandener Firmenhinweis |
| 48 | Japan | [Takeda Pharmaceutical](https://indexes.nikkei.co.jp/en/nkave/index/component) · 4502 | TAKEDA PHARMACEUTICAL CO LTD · TAK · NYSE · CIK 0001395064 | — | Vorhandener Firmenhinweis |
| 49 | Japan | [Tokyo Electron](https://indexes.nikkei.co.jp/en/nkave/index/component) · 8035 | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Japan |
| 50 | Japan | [Toyota Motor](https://indexes.nikkei.co.jp/en/nkave/index/component) · 7203 | TOYOTA MOTOR CORP/ · TM · NYSE · CIK 0001094517 | — | Vorhandener Firmenhinweis |
| 51 | Hongkong/China | [AIA Group](https://www.hkex.com.hk/Services/Trading/Securities/Securities-Lists?sc_lang=en) · 1299 | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Hongkong/China |
| 52 | Hongkong/China | [BYD](https://www.hkex.com.hk/Services/Trading/Securities/Securities-Lists?sc_lang=en) · 1211 | BYD CO LTD · BYDDF · OTC · CIK 0001445162 | — | Vorhandener Firmenhinweis |
| 53 | Hongkong/China | [Bank of China](https://www.hkex.com.hk/Services/Trading/Securities/Securities-Lists?sc_lang=en) · 3988 | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Hongkong/China |
| 54 | Hongkong/China | [China Construction Bank](https://www.hkex.com.hk/Services/Trading/Securities/Securities-Lists?sc_lang=en) · 0939 | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Hongkong/China |
| 55 | Hongkong/China | [China Mobile](https://www.hkex.com.hk/Services/Trading/Securities/Securities-Lists?sc_lang=en) · 0941 | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Hongkong/China |
| 56 | Hongkong/China | [Hong Kong Exchanges](https://www.hkex.com.hk/Services/Trading/Securities/Securities-Lists?sc_lang=en) · 0388 | Hong Kong Exchanges & Clearing Ltd · HKXCF · OTC · CIK 0001445476 | — | Vorhandener Firmenhinweis |
| 57 | Hongkong/China | [Meituan](https://www.hkex.com.hk/Services/Trading/Securities/Securities-Lists?sc_lang=en) · 3690 | Meituan Dianping/ADR · MPNGF · OTC · CIK 0001754088 | — | Vorhandener Firmenhinweis |
| 58 | Hongkong/China | [Ping An Insurance](https://www.hkex.com.hk/Services/Trading/Securities/Securities-Lists?sc_lang=en) · 2318 | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Hongkong/China |
| 59 | Hongkong/China | [Tencent](https://www.hkex.com.hk/Services/Trading/Securities/Securities-Lists?sc_lang=en) · 0700 | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Hongkong/China; Tochter-/Namensfirmen verworfen |
| 60 | Hongkong/China | [Xiaomi](https://www.hkex.com.hk/Services/Trading/Securities/Securities-Lists?sc_lang=en) · 1810 | Xiaomi Corporation/ADR · XIACF · OTC · CIK 0001748830 | — | Vorhandener Firmenhinweis |
| 61 | Indien | [Bharti Airtel](https://www.nseindia.com/static/products-services/indices-nifty50-index) · BHARTIARTL | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Indien |
| 62 | Indien | [HDFC Bank](https://www.nseindia.com/static/products-services/indices-nifty50-index) · HDFCBANK | HDFC BANK LTD · HDB · NYSE · CIK 0001144967 | — | Vorhandener Firmenhinweis |
| 63 | Indien | [Hindustan Unilever](https://www.nseindia.com/static/products-services/indices-nifty50-index) · HINDUNILVR | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Indien |
| 64 | Indien | [ICICI Bank](https://www.nseindia.com/static/products-services/indices-nifty50-index) · ICICIBANK | ICICI BANK LTD · IBN · NYSE · CIK 0001103838 | — | Vorhandener Firmenhinweis |
| 65 | Indien | [ITC](https://www.nseindia.com/static/products-services/indices-nifty50-index) · ITC | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Indien |
| 66 | Indien | [Infosys](https://www.nseindia.com/static/products-services/indices-nifty50-index) · INFY | Infosys Ltd · INFY · NYSE · CIK 0001067491 | — | Vorhandener Firmenhinweis |
| 67 | Indien | [Reliance Industries](https://www.nseindia.com/static/products-services/indices-nifty50-index) · RELIANCE | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Indien |
| 68 | Indien | [State Bank of India](https://www.nseindia.com/static/products-services/indices-nifty50-index) · SBIN | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Indien |
| 69 | Indien | [Sun Pharmaceutical](https://www.nseindia.com/static/products-services/indices-nifty50-index) · SUNPHARMA | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Indien |
| 70 | Indien | [Tata Consultancy Services](https://www.nseindia.com/static/products-services/indices-nifty50-index) · TCS | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Indien |
| 71 | Australien | [ANZ Group](https://www.solactive.com/announcements/69448) · ANZ | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Australien |
| 72 | Australien | [BHP Group](https://www.solactive.com/announcements/69448) · BHP | BHP Group Ltd · BHP · NYSE · CIK 0000811809 | — | Vorhandener Firmenhinweis |
| 73 | Australien | [CSL](https://www.solactive.com/announcements/69448) · CSL | CSL LTD · CSLLY · OTC · CIK 0001274152 | — | Vorhandener Firmenhinweis |
| 74 | Australien | [Fortescue](https://www.solactive.com/announcements/69448) · FMG | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Australien |
| 75 | Australien | [Macquarie Group](https://www.solactive.com/announcements/69448) · MQG | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Australien |
| 76 | Australien | [National Australia Bank](https://www.solactive.com/announcements/69448) · NAB | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Australien |
| 77 | Australien | [Telstra Group](https://www.solactive.com/announcements/69448) · TLS | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Australien |
| 78 | Australien | [Wesfarmers](https://www.solactive.com/announcements/69448) · WES | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Australien |
| 79 | Australien | [Woodside Energy](https://www.solactive.com/announcements/69448) · WDS | WOODSIDE ENERGY GROUP LTD · WDS · NYSE · CIK 0000844551 | — | Vorhandener Firmenhinweis |
| 80 | Australien | [Woolworths Group](https://www.solactive.com/announcements/69448) · WOW | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Australien |
| 81 | Brasilien | [B3 SA](https://www.b3.com.br/en_us/market-data-and-indices/indices/broad-indices/ibovespa.htm) · B3SA3 | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Brasilien |
| 82 | Brasilien | [Banco Bradesco](https://www.b3.com.br/en_us/market-data-and-indices/indices/broad-indices/ibovespa.htm) · BBDC4 | BANK BRADESCO · BBD · NYSE · CIK 0001160330 | — | Vorhandener Firmenhinweis |
| 83 | Brasilien | [Banco do Brasil](https://www.b3.com.br/en_us/market-data-and-indices/indices/broad-indices/ibovespa.htm) · BBAS3 | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Brasilien |
| 84 | Brasilien | [Itaú Unibanco](https://www.b3.com.br/en_us/market-data-and-indices/indices/broad-indices/ibovespa.htm) · ITUB4 | Itau Unibanco Holding S.A. · ITUB · NYSE · CIK 0001132597 | — | Vorhandener Firmenhinweis |
| 85 | Brasilien | [Localiza](https://www.b3.com.br/en_us/market-data-and-indices/indices/broad-indices/ibovespa.htm) · RENT3 | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Brasilien |
| 86 | Brasilien | [Raia Drogasil](https://www.b3.com.br/en_us/market-data-and-indices/indices/broad-indices/ibovespa.htm) · RADL3 | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Brasilien |
| 87 | Brasilien | [Sabesp](https://www.b3.com.br/en_us/market-data-and-indices/indices/broad-indices/ibovespa.htm) · SBSP3 | COMPANHIA DE SANEAMENTO BASICO DO ESTADO DE SAO PAULO-SABESP · SBS · NYSE · CIK 0001170858 | — | Vorhandener Firmenhinweis |
| 88 | Brasilien | [Suzano](https://www.b3.com.br/en_us/market-data-and-indices/indices/broad-indices/ibovespa.htm) · SUZB3 | Suzano S.A. · SUZ · NYSE · CIK 0000909327 | — | Vorhandener Firmenhinweis |
| 89 | Brasilien | [Vale](https://www.b3.com.br/en_us/market-data-and-indices/indices/broad-indices/ibovespa.htm) · VALE3 | Vale S.A. · VALE · NYSE · CIK 0000917851 | — | Vorhandener Firmenhinweis |
| 90 | Brasilien | [WEG](https://www.b3.com.br/en_us/market-data-and-indices/indices/broad-indices/ibovespa.htm) · WEGE3 | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Brasilien |
| 91 | Südafrika | [Absa Group](https://www.jse.co.za/current-companies/companies-and-financial-instruments) · ABG | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Südafrika |
| 92 | Südafrika | [Bidcorp](https://www.jse.co.za/current-companies/companies-and-financial-instruments) · BID | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Südafrika |
| 93 | Südafrika | [Capitec](https://www.jse.co.za/current-companies/companies-and-financial-instruments) · CPI | Capitec Limited/ADR · CKHGY · OTC · CIK 0001469059 | — | Vorhandener Firmenhinweis |
| 94 | Südafrika | [FirstRand](https://www.jse.co.za/current-companies/companies-and-financial-instruments) · FSR | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Südafrika |
| 95 | Südafrika | [MTN Group](https://www.jse.co.za/current-companies/companies-and-financial-instruments) · MTN | MTN GROUP LTD/ADR · MTNOY · OTC · CIK 0001163420 | — | Vorhandener Firmenhinweis |
| 96 | Südafrika | [Naspers](https://www.jse.co.za/current-companies/companies-and-financial-instruments) · NPN | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Südafrika |
| 97 | Südafrika | [Nedbank](https://www.jse.co.za/current-companies/companies-and-financial-instruments) · NED | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Südafrika |
| 98 | Südafrika | [Sanlam](https://www.jse.co.za/current-companies/companies-and-financial-instruments) · SLM | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Südafrika |
| 99 | Südafrika | [Standard Bank Group](https://www.jse.co.za/current-companies/companies-and-financial-instruments) · SBK | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Südafrika |
| 100 | Südafrika | [Vodacom](https://www.jse.co.za/current-companies/companies-and-financial-instruments) · VOD | — | — | Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg Südafrika |

## Weshalb Firmen fehlen und wie sie beschafft werden können

Die Ursache pro fehlender Firma ist durch den Quellenumfang erklärt: SEC-Original enthält keinen passenden Firmeneintrag, während der Wikidata-Import nur Schweizer/SIX-Kandidaten auswählt. Die Bedingungen des jeweiligen Datenlieferanten sind ein zusätzlicher Ausbaupunkt, kein behaupteter Grund, weshalb eine Firma im SEC-Original fehlt.

| Markt / gilt für jeden fehlenden Eintrag oben | Konkreter Beschaffungsweg |
|---|---|
| USA | SEC-Original pruefen; Schreibweise/Alias und korrekte Aktiengattung erfassen. |
| Schweiz | Globalen Wikidata-CC0-Kandidatenimport ausbauen; SIX-Referenzliste erst nach Datenfreigabe; ISIN/LEI/Listing getrennt bestaetigen. |
| Deutschland | Wikidata CC0 je Boerse; ESMA-FIRDS fuer ISIN/MIC/Emittent nach konkreter Rechtepruefung; Xetra-Stammdatenvertrag als Alternative. |
| Grossbritannien | Wikidata CC0; FCA-FIRDS als Kandidat nach Rechtepruefung; LSE-Stammdaten mit ausdruecklichen Speicher-/Nutzungsrechten. |
| Japan | Wikidata CC0 je TSE; JPX-Excel ist technisch verfuegbar, kommerzielle Massennutzung erfordert JPX-Erlaubnis/Vertrag. |
| Hongkong/China | Wikidata CC0 je HKEX; HKEX Securities Lists / Issuer-Verzeichnis nach Rechtefreigabe; H-/A-Aktien und ADR getrennt halten. |
| Indien | Wikidata CC0; NSE-/BSE-Aktienlisten samt ISIN nach Rechtepruefung; Firmenrechtstraeger und Aktienklassen getrennt modellieren. |
| Australien | Wikidata CC0; ASX Company Directory nach Rechtepruefung, zusaetzlich Instrumentliste/ISIN und Status erforderlich. |
| Brasilien | CVM cia_aberta-cad (ODbL, Bedingungen konkret umsetzen) fuer CNPJ/CVM-ID; B3-Listing/Ticker/ISIN zusaetzlich mit schriftlicher Freigabe oder lizenziertem Anbieter. |
| Südafrika | Wikidata CC0 je JSE; JSE-Instrumentverzeichnis nach Rechtepruefung; Emittenten-IR fuer gezielte Kennungs-/Listing-Verifikation. |

## Priorisierte Umsetzung

1. Einen gemeinsamen Suchzugang über SEC und Schweizer Kandidaten schaffen, mit sichtbarer Herkunft und Vertrauensstufe. Das behebt Sichtbarkeitslücken, fügt aber keine fehlenden Firmen hinzu.
2. Wikidata CC0 global und börsenweise ergänzen. P414-Börsenstatement und zugehörigen P249-Ticker zusammen auslesen; Start-/Enddatum, Rang und Quellenreferenzen erhalten. Nicht jede globale Firma hat eine ISIN in Wikidata: Firmenhinweis ohne ISIN zulassen, aber nie als bestätigtes Wertpapier. Kleine Queries, Rohdatenhashes und explizite Teilabdeckung verwenden. Lizenz erlaubt Weiterverwendung; Vollständigkeit/aktuelle Kotierung sind gesondert zu prüfen.
3. Pro Börse eine unabhängige Soll-Liste samt MIC, Stichtag und Nutzungsrechten aufbauen und gegen den Ist-Bestand vergleichen. Erst dann eine echte Abdeckungsquote je Börse ausweisen. Corporate Actions, Delistings, Umbenennungen und Mehrklassenfälle erhalten.
4. Amtliche/vertraglich freigegebene Instrumentdaten für ISIN, Gattung, Listing und Emittent ergänzen; LEI/GLEIF erst über belegte Kennungen verbinden. ADR und Heimataktie getrennt; Konzern und Tochter getrennt. CVM-Register allein liefert noch keine vollständige B3-Instrumentliste.

## Quellen und Nutzbarkeit

- [Wikidata-Lizenz](https://www.wikidata.org/wiki/Wikidata:Licensing): strukturierte Daten CC0; bestehend freigegebene Alternative für einen globalen Kandidatenbestand.
- [JPX-Emittentenliste](https://www.jpx.co.jp/english/markets/statistics-equities/misc/01.html) und [JPX-Bedingungen](https://www.jpx.co.jp/english/term-of-use/): Excel technisch verfügbar; kommerzielle Sammlung/Weiterverwendung nur mit Erlaubnis oder Vertrag. Nicht als frei importierbar bezeichnet.
- [CVM-Register börsenoffener Gesellschaften](https://dados.cvm.gov.br/dataset/cia_aberta-cad): ODbL ausgewiesen; Datenbank-/Weitergabepflichten vor Integration umsetzen. Registerstatus ist nicht gleich aktive Börsenkotierung.
- [B3-Bedingungen](https://www.b3.com.br/main.jsp?doui_processActionId=setLocaleProcessAction&locale=en_US&lumA=1&lumII=8AE690F77A1A49BA017A5CE182412193&lumPageId=8AE690F77A1A49BA017A5CDEBBCF67BD): keine pauschale kommerzielle Freigabe; schriftliche Zustimmung erforderlich. Keine Freigabe durch Quellenangabe unterstellen.
- [ESMA MiFIR/FIRDS](https://www.esma.europa.eu/data-reporting/mifir-reporting): Instrument-Referenzdaten als Ausbaukandidat; konkrete Datei und Nutzungsrechte weiterhin offen. FCA-FIRDS analog separat prüfen.
- [Naspers](https://www.naspers.com/the-group/group-structure), [Nedbank](https://group.nedbank.co.za/explore-investor-relations/equity-investors.html), [Tesco/LSE](https://www.londonstockexchange.com/en/quote/equity/TSCO/tesco-plc): gezielte Primärbelege für echte Kotierungen trotz fehlendem Katalogtreffer.
- [Mercedes-Benz: Aktie und US-Ticker MBGAF](https://group.mercedes-benz.com/investors/share/) und [Umbenennung Daimler AG](https://group.mercedes-benz.com/company/news/daimler-becomes-mercedes-benz-group.html): erklärt den unter dem aktuellen Namen fehlenden, unter DAIMLER AG vorhandenen SEC-Firmenhinweis. Keine Verwechslung mit Daimler Truck.

Kein kostenpflichtiger Dienst bestellt, keine neuen Produktionsquellen aktiviert, kein Push und keine öffentliche Datenfreigabe. Die Prüfung beantwortet die Bestandsfrage; die genannten Ausbauten sind noch nicht implementiert.
