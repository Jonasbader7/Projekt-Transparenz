"""Read-only audit. Seeded regional draw from explicit curated pool, not global census.

Aliases serve research discovery only; no product identity merges or DB writes.
"""

from __future__ import annotations

# ruff: noqa: E501 -- explicit, reviewable research pools and source URLs
import hashlib
import json
import random
import re
import unicodedata
from collections import Counter
from pathlib import Path

from transparenz.config.settings import local_data_dir

ROOT = Path(__file__).resolve().parents[1]
DATA = local_data_dir(ROOT)  # Datenordner (TRANSPARENZ_DATA_DIR, sonst data/)
OUT = DATA / "processed/coverage_audit"
SEED = 20261108
POOLS = {
    "USA": "Apple|Microsoft|NVIDIA|Amazon|Alphabet|Meta Platforms|JPMorgan Chase|Exxon Mobil|Visa|Coca-Cola|Walmart|Procter & Gamble",
    "Schweiz": "Nestlé|Roche|Novartis|UBS Group|ABB|Zurich Insurance|Swiss Re|Swisscom|Sika|Givaudan|Lonza|Alcon",
    "Deutschland": "SAP|Siemens|Allianz|Deutsche Telekom|Deutsche Bank|BASF|BMW|Mercedes-Benz|Volkswagen|adidas|Infineon|Münchener Rück",
    "Grossbritannien": "Shell|AstraZeneca|HSBC|Unilever|BP|GSK|Diageo|RELX|National Grid|Tesco|Lloyds Banking Group|Barclays",
    "Japan": "Toyota Motor|Sony Group|Nintendo|Hitachi|Keyence|Tokyo Electron|SoftBank Group|Mitsubishi UFJ Financial|Honda Motor|Takeda Pharmaceutical|Recruit Holdings|Fast Retailing",
    "Hongkong/China": "Tencent|Alibaba|AIA Group|China Mobile|China Construction Bank|ICBC|Bank of China|Xiaomi|Meituan|BYD|Hong Kong Exchanges|Ping An Insurance",
    "Indien": "Reliance Industries|Tata Consultancy Services|HDFC Bank|ICICI Bank|Infosys|Bharti Airtel|State Bank of India|Larsen & Toubro|ITC|Hindustan Unilever|Sun Pharmaceutical|Axis Bank",
    "Australien": "BHP Group|Commonwealth Bank|CSL|National Australia Bank|Westpac|ANZ Group|Macquarie Group|Wesfarmers|Woolworths Group|Fortescue|Telstra Group|Woodside Energy",
    "Brasilien": "Vale|Petrobras|Itaú Unibanco|Banco Bradesco|Ambev|WEG|B3 SA|Banco do Brasil|Sabesp|Suzano|Localiza|Raia Drogasil",
    "Südafrika": "Naspers|FirstRand|Standard Bank Group|MTN Group|Capitec|Absa Group|Vodacom|Sanlam|Shoprite|Bidcorp|Nedbank|Discovery",
}
SOURCES = {
    "USA": "https://www.sec.gov/files/company_tickers_exchange.json",
    "Schweiz": "https://www.six-group.com/de/market-data/indices/switzerland/equity/smi.html",
    "Deutschland": "https://stoxx.com/index/dax/?factsheet=true",
    "Grossbritannien": "https://www.londonstockexchange.com/en/indices/ftse-100/constituents",
    "Japan": "https://indexes.nikkei.co.jp/en/nkave/index/component",
    "Hongkong/China": "https://www.hkex.com.hk/Services/Trading/Securities/Securities-Lists?sc_lang=en",
    "Indien": "https://www.nseindia.com/static/products-services/indices-nifty50-index",
    "Australien": "https://www.solactive.com/announcements/69448",
    "Brasilien": "https://www.b3.com.br/en_us/market-data-and-indices/indices/broad-indices/ibovespa.htm",
    "Südafrika": "https://www.jse.co.za/current-companies/companies-and-financial-instruments",
}
ALIASES = {
    "Mercedes-Benz": ["DAIMLER AG"],
    "Exxon Mobil": ["ExxonMobil"],
    "UBS Group": ["UBS"],
    "Banco Bradesco": ["BANK BRADESCO"],
    "Nestlé": ["Nestle"],
    "Roche": ["Roche Holding"],
    "Zurich Insurance": ["Zurich Insurance Group"],
    "Münchener Rück": ["Munich Re", "Muenchener Rueck", "Munchener Ruck"],
    "ICBC": ["Industrial & Commercial Bank", "Industrial and Commercial Bank"],
    "Petrobras": ["Petroleo Brasileiro"],
    "Itaú Unibanco": ["Itau Unibanco"],
    "B3 SA": ["B3 S.A.", "B3 SA Brasil"],
    "Raia Drogasil": ["RD Saude"],
    "Hong Kong Exchanges": ["Hong Kong Exchanges and Clearing"],
    "Sabesp": ["Companhia de Saneamento Basico do Estado de Sao Paulo"],
    "Commonwealth Bank": ["Commonwealth Bank of Australia"],
    "BMW": ["Bayerische Motoren Werke"],
    "GSK": ["GlaxoSmithKline"],
}

# Manually reviewed company-level hits. Excludes subsidiaries, notes and name collisions.
# These are observations of presence, NOT an instrument/issuer mapping.
PRIMARY = dict(
    zip(
        [
            "Alphabet",
            "Amazon",
            "Apple",
            "Coca-Cola",
            "Exxon Mobil",
            "JPMorgan Chase",
            "Meta Platforms",
            "Procter & Gamble",
            "Visa",
            "Walmart",
            "ABB",
            "Alcon",
            "UBS Group",
            "Deutsche Bank",
            "Deutsche Telekom",
            "Infineon",
            "SAP",
            "AstraZeneca",
            "BP",
            "Diageo",
            "GSK",
            "HSBC",
            "Lloyds Banking Group",
            "RELX",
            "Shell",
            "Unilever",
            "Honda Motor",
            "Mitsubishi UFJ Financial",
            "SoftBank Group",
            "Sony Group",
            "Takeda Pharmaceutical",
            "Toyota Motor",
            "BYD",
            "Hong Kong Exchanges",
            "Meituan",
            "Xiaomi",
            "HDFC Bank",
            "ICICI Bank",
            "Infosys",
            "BHP Group",
            "CSL",
            "Woodside Energy",
            "Banco Bradesco",
            "Itaú Unibanco",
            "Sabesp",
            "Suzano",
            "Vale",
            "Capitec",
            "MTN Group",
        ],
        [
            "GOOGL",
            "AMZN",
            "AAPL",
            "KO",
            "XOM",
            "JPM",
            "META",
            "PG",
            "V",
            "WMT",
            "ABBNY",
            "ALC",
            "UBS",
            "DB",
            "DTEGY",
            "IFNNY",
            "SAP",
            "AZN",
            "BP",
            "DEO",
            "GSK",
            "HSBC",
            "LYG",
            "RELX",
            "SHEL",
            "UL",
            "HMC",
            "MUFG",
            "SFTBF",
            "SONY",
            "TAK",
            "TM",
            "BYDDF",
            "HKXCF",
            "MPNGF",
            "XIACF",
            "HDB",
            "IBN",
            "INFY",
            "BHP",
            "CSLLY",
            "WDS",
            "BBD",
            "ITUB",
            "SBS",
            "SUZ",
            "VALE",
            "CKHGY",
            "MTNOY",
        ],
        strict=True,
    )
)
PRIMARY["Mercedes-Benz"] = "MBGAF"
LOCAL = [
    "GOOGL AMZN AAPL KO XOM JPM META PG V WMT",
    "ABBN ALC GIVN LONN NESN ROG SIKA SREN UBSG ZURN",
    "ALV BAS BMW DBK DTE IFX MBG MUV2 SAP SIE",
    "AZN BP. DGE GSK HSBA LLOY REL SHEL TSCO ULVR",
    "9983 7267 8306 7974 6098 9984 6758 4502 8035 7203",
    "1299 1211 3988 0939 0941 0388 3690 2318 0700 1810",
    "BHARTIARTL HDFCBANK HINDUNILVR ICICIBANK ITC INFY RELIANCE SBIN SUNPHARMA TCS",
    "ANZ BHP CSL FMG MQG NAB TLS WES WDS WOW",
    "B3SA3 BBDC4 BBAS3 ITUB4 RENT3 RADL3 SBSP3 SUZB3 VALE3 WEGE3",
    "ABG BID CPI FSR MTN NPN NED SLM SBK VOD",
]
ROUTES = {
    "USA": "SEC-Original pruefen; Schreibweise/Alias und korrekte Aktiengattung erfassen.",
    "Schweiz": "Globalen Wikidata-CC0-Kandidatenimport ausbauen; SIX-Referenzliste erst nach Datenfreigabe; ISIN/LEI/Listing getrennt bestaetigen.",
    "Deutschland": "Wikidata CC0 je Boerse; ESMA-FIRDS fuer ISIN/MIC/Emittent nach konkreter Rechtepruefung; Xetra-Stammdatenvertrag als Alternative.",
    "Grossbritannien": "Wikidata CC0; FCA-FIRDS als Kandidat nach Rechtepruefung; LSE-Stammdaten mit ausdruecklichen Speicher-/Nutzungsrechten.",
    "Japan": "Wikidata CC0 je TSE; JPX-Excel ist technisch verfuegbar, kommerzielle Massennutzung erfordert JPX-Erlaubnis/Vertrag.",
    "Hongkong/China": "Wikidata CC0 je HKEX; HKEX Securities Lists / Issuer-Verzeichnis nach Rechtefreigabe; H-/A-Aktien und ADR getrennt halten.",
    "Indien": "Wikidata CC0; NSE-/BSE-Aktienlisten samt ISIN nach Rechtepruefung; Firmenrechtstraeger und Aktienklassen getrennt modellieren.",
    "Australien": "Wikidata CC0; ASX Company Directory nach Rechtepruefung, zusaetzlich Instrumentliste/ISIN und Status erforderlich.",
    "Brasilien": "CVM cia_aberta-cad (ODbL, Bedingungen konkret umsetzen) fuer CNPJ/CVM-ID; B3-Listing/Ticker/ISIN zusaetzlich mit schriftlicher Freigabe oder lizenziertem Anbieter.",
    "Südafrika": "Wikidata CC0 je JSE; JSE-Instrumentverzeichnis nach Rechtepruefung; Emittenten-IR fuer gezielte Kennungs-/Listing-Verifikation.",
}


def normalize(value):
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def match(name, candidate):
    text = " " + normalize(candidate) + " "
    return any(" " + normalize(a) + " " in text for a in [name, *ALIASES.get(name, [])])


def current(folder, filename):
    base = DATA / "processed" / folder
    pointer = json.loads((base / "current.json").read_text(encoding="utf-8"))
    path = base / pointer["generation"] / filename
    return path, json.loads(path.read_text(encoding="utf-8"))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    mp, market = current("market", "catalogue.json")
    sp, swiss = current("swiss", "security_candidates.json")
    listings = [r for r in market if r["classification"] == "listed_instrument_unclassified"]
    rng = random.Random(SEED)
    rows = []
    for country, names in POOLS.items():
        for name in sorted(rng.sample(names.split("|"), 10)):
            sec = [r for r in listings if match(name, r["name"])]
            ch = [r for r in swiss if match(name, r["name"])]
            rows.append(
                {
                    "number": len(rows) + 1,
                    "market": country,
                    "company": name,
                    "reference_url": SOURCES[country],
                    "sec_candidates": [
                        {
                            k: r[k]
                            for k in (
                                "catalogue_key",
                                "name",
                                "tickers",
                                "exchange",
                                "registrant_cik",
                            )
                        }
                        for r in sec
                    ],
                    "swiss_candidates": [
                        {k: r[k] for k in ("name", "isin", "wikidata_id", "mapping_status")}
                        for r in ch
                    ],
                }
            )
    assert len(rows) == 100
    (OUT / "candidates.json").write_text(
        json.dumps(
            {
                "seed": SEED,
                "pool": POOLS,
                "market_path": str(mp.relative_to(DATA)),
                "swiss_path": str(sp.relative_to(DATA)),
                "market_sha256": hashlib.sha256(mp.read_bytes()).hexdigest(),
                "swiss_sha256": hashlib.sha256(sp.read_bytes()).hexdigest(),
                "rows": rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    for r in rows:
        print(
            r["number"],
            r["market"],
            r["company"],
            "SEC:",
            [(x["name"], x["tickers"], x["exchange"]) for x in r["sec_candidates"]],
            "CH:",
            sorted({x["name"] for x in r["swiss_candidates"]}),
        )
    # The candidates above remain available for review; only adjudicated hits count below.
    reviewed = []
    for index, row in enumerate(rows):
        ticker = PRIMARY.get(row["company"])
        sec = [r for r in listings if ticker and ticker in r["tickers"]]
        assert len(sec) == (1 if ticker else 0), (row["company"], sec)
        ch = (
            [r for r in swiss if match(row["company"], r["name"])]
            if row["market"] == "Schweiz"
            else []
        )
        assert not ticker or match(row["company"], sec[0]["name"])
        found = bool(sec or ch)
        reason = (
            "SEC-Firmentreffer; lokale Heimatkotierung daraus nicht belegt."
            if sec
            else "Nur im separaten Schweizer Wikidata-Kandidatenbestand; kein bestaetigtes Wertpapier."
            if ch
            else "Kein Firmentreffer im SEC-Snapshot; Heimatmarktquelle nicht integriert und ausserhalb des Schweizer Wikidata-Zuschnitts."
        )
        if ch and sec:
            reason = "SEC-Firmentreffer plus separater Schweizer Wikidata-Kandidat."
        if row["company"] in {"Tencent", "Siemens"}:
            reason += " Namensaehnliche eigenstaendige Unternehmen verworfen."
        reviewed.append(
            {
                "number": row["number"],
                "market": row["market"],
                "company": row["company"],
                "local_ticker_reference": LOCAL[index // 10].split()[index % 10],
                "found_company_hint": found,
                "sec_primary": sec[0] if sec else None,
                "swiss_candidates": ch,
                "reason": reason,
                "acquisition_route": ROUTES[row["market"]],
                "reference_url": row["reference_url"],
            }
        )
    summary = Counter("found" if r["found_company_hint"] else "missing" for r in reviewed)
    summary.update(
        {
            "sec": sum(bool(r["sec_primary"]) for r in reviewed),
            "swiss": sum(bool(r["swiss_candidates"]) for r in reviewed),
        }
    )
    # Check every SEC ticker observation against the original, not just this sample.
    digest = listings[0]["evidence"][0]["original_sha256"]
    original_path = DATA / "raw/external/sec_exchange_tickers/objects" / (digest + ".json")
    assert hashlib.sha256(original_path.read_bytes()).hexdigest() == digest
    original = json.loads(original_path.read_bytes())
    raw = [dict(zip(original["fields"], r, strict=True)) for r in original["data"]]
    raw_keys = {(str(r["cik"]).zfill(10), r["ticker"], r["exchange"]) for r in raw}
    export_keys = {(r["registrant_cik"], t, r["exchange"]) for r in listings for t in r["tickers"]}
    assert raw_keys == export_keys, "SEC source rows lost or added in export"
    payload = {
        "seed": SEED,
        "summary": dict(summary),
        "rows": reviewed,
        "sec_original_sha256": digest,
        "sec_original_rows": len(raw),
        "sec_export_exact_set_equal": True,
    }
    (OUT / "reviewed.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_report(payload, mp, sp)
    print("REVIEWED", dict(summary), "SEC exact rows", len(raw))


def write_report(payload, market_path, swiss_path):
    report = ROOT / "docs/COVERAGE_AUDIT_100.md"
    lines = [
        "# Abdeckungstest: 100 börsenkotierte Firmen",
        "",
        "Prüfdatum: 08.11.2026. Projekt Transparenz. Lokaler Datenstand vom 08.11.2026.",
        "",
        "## Ergebnis",
        "",
        f"**{payload['summary']['found']} Firmen mit passendem Quellenhinweis, {payload['summary']['missing']} ohne Treffer** in den beiden echten Wertpapier-Kandidatenkatalogen. Davon {payload['summary']['sec']} im SEC-Katalog und {payload['summary']['swiss']} im Schweizer Wikidata-Bestand, mit 3 Überschneidungen. Ein Quellenhinweis ist kein bestätigtes Emittenten-/Instrumentmapping. Die öffentliche Website nutzt weiterhin Demodaten.",
        "",
        "## Auswahl und Grenzen",
        "",
        "Explorative, regional geschichtete Zufallsauswahl: vor dem lokalen Abgleich je 12 bekannte börsenkotierte Firmen aus 10 Märkten manuell zusammengestellt; daraus je 10 ohne Zurücklegen mit Python random.Random(20261108), in der Reihenfolge von POOLS im Skript. Vollständiger Pool und Verfahren: scripts/company_coverage_probe.py. Der Pool umfasst 120 Firmen. Keine Gleichverteilung über sämtliche Weltbörsen, keine Welt-Abdeckungsquote; kleine Firmen, Kanada, Korea, Taiwan und zahlreiche weitere Märkte fehlen im Auswahlrahmen. Die Börsen-/Index-/Emittentenlinks dienen der Kotierungsrecherche; keine vollständigen Börsendatenbanken importiert, keine Kurse übernommen. Quellenstände reichen teilweise vor das Prüfdatum zurück. Kein Nachweis der Handelbarkeit an jedem einzelnen Tag.",
        "",
        "Geprüft werden Firmenhinweise im SEC-Wertpapierkatalog und Schweizer ISIN-Kandidaten. Die 801'732 Schweizer Registereinheiten sind kein globales Aktienuniversum und wurden nicht als Aktienabdeckung gezählt. Im bestätigten Screening-Wertpapierbestand gibt es weiterhin 0 echte Wertpapiere. ETFs sind nicht Teil dieser Firmenstichprobe.",
        "",
        "## Prüfmethode",
        "",
        "Akzente, Satzzeichen und explizite Namensvarianten wurden für die Recherche normalisiert. Kandidaten wurden manuell nach Firmenname und konkretem SEC-Ticker geprüft; keine automatische Identitätsfusion. Beispielsweise Apple Hospitality, Coca-Cola HBC, CSL Vifor, BYD Electronic, Siemens Energy/Healthineers und Tencent Music zählen nicht für die jeweils gesuchte Mutter-/Namensfirma. UBS ist als UBS vorhanden; Bradesco als BANK BRADESCO; Exxon Mobil als ExxonMobil Holdings Corp (XOM). Präferenzaktien, Notes und andere zusätzliche Ticker desselben Registranten werden nicht pauschal als Stammaktien gezählt.",
        "",
        f"SEC-Originalprüfung: alle {payload['sec_original_rows']:,} CIK-/Ticker-/Börsen-Tupel entsprechen exakt dem Export (Mengenvergleich). Keine fehlende SEC-Quellenzeile im Export. Original-SHA-256: `{payload['sec_original_sha256']}`. Fehlende Firmen sind damit eine Abdeckungslücke des verwendeten Snapshots bzw. Quellenzuschnitts, kein hier nachgewiesener Importverlust. Kein Rückschluss, dass sie niemals SEC-Meldungen eingereicht hätten oder generell nicht OTC-gehandelt würden.",
        "",
        f"Geprüfte Exporte: `{market_path.relative_to(DATA).as_posix()}` und `{swiss_path.relative_to(DATA).as_posix()}`. SHA-256 beider Exporte, 100 Einzelbefunde und Rohkandidaten stehen lokal in `data/processed/coverage_audit/`. Wiederholung: `.venv\\Scripts\\python scripts/company_coverage_probe.py`.",
        "",
        "## Ergebnis nach Markt",
        "",
        "| Markt | SEC-Firmentreffer | Schweizer Kandidat | Ohne Treffer |",
        "|---|---:|---:|---:|",
    ]
    for market in POOLS:
        rows = [r for r in payload["rows"] if r["market"] == market]
        lines.append(
            f"| {market} | {sum(bool(r['sec_primary']) for r in rows)} | {sum(bool(r['swiss_candidates']) for r in rows)} | {sum(not r['found_company_hint'] for r in rows)} |"
        )
    lines += [
        "",
        "## Alle 100 Einzelprüfungen",
        "",
        "SEC = konkreter Firmentreffer im SEC-Snapshot, auch ADR/OTC. CH = unverifizierter Wikidata-ISIN-Kandidat. Die Referenzticker sind börsenspezifische Rechercheangaben, keine neu importierten Listings. Ein ausländischer SEC-Treffer belegt die Heimatkotierung nicht. Für jeden fehlenden Eintrag nennt die letzte Spalte den Beschaffungsweg im nächsten Abschnitt.",
        "",
        "| Nr. | Markt | Firma / Referenzticker | SEC-Treffer | CH-Kandidat | Befund / Beschaffung |",
        "|---:|---|---|---|---|---|",
    ]
    for r in payload["rows"]:
        sec = r["sec_primary"]
        sec_text = (
            f"{sec['name']} · {','.join(sec['tickers'])} · {sec['exchange']} · CIK {sec['registrant_cik']}"
            if sec
            else "—"
        )
        ch_text = "; ".join(sorted({x["wikidata_id"] for x in r["swiss_candidates"]})) or "—"
        result = (
            "Vorhandener Firmenhinweis"
            if r["found_company_hint"]
            else f"Fehlt: SEC-Quellenlücke + Heimatmarkt nicht angebunden; Weg {r['market']}"
        )
        if r["company"] in {"Tencent", "Siemens"}:
            result += "; Tochter-/Namensfirmen verworfen"
        lines.append(
            f"| {r['number']} | {r['market']} | [{r['company']}]({r['reference_url']}) · {r['local_ticker_reference']} | {sec_text} | {ch_text} | {result} |"
        )
    lines += [
        "",
        "## Weshalb Firmen fehlen und wie sie beschafft werden können",
        "",
        "Die Ursache pro fehlender Firma ist durch den Quellenumfang erklärt: SEC-Original enthält keinen passenden Firmeneintrag, während der Wikidata-Import nur Schweizer/SIX-Kandidaten auswählt. Die Bedingungen des jeweiligen Datenlieferanten sind ein zusätzlicher Ausbaupunkt, kein behaupteter Grund, weshalb eine Firma im SEC-Original fehlt.",
        "",
        "| Markt / gilt für jeden fehlenden Eintrag oben | Konkreter Beschaffungsweg |",
        "|---|---|",
    ]
    lines += [f"| {k} | {v} |" for k, v in ROUTES.items()]
    lines += [
        "",
        "## Priorisierte Umsetzung",
        "",
        "1. Einen gemeinsamen Suchzugang über SEC und Schweizer Kandidaten schaffen, mit sichtbarer Herkunft und Vertrauensstufe. Das behebt Sichtbarkeitslücken, fügt aber keine fehlenden Firmen hinzu.",
        "2. Wikidata CC0 global und börsenweise ergänzen. P414-Börsenstatement und zugehörigen P249-Ticker zusammen auslesen; Start-/Enddatum, Rang und Quellenreferenzen erhalten. Nicht jede globale Firma hat eine ISIN in Wikidata: Firmenhinweis ohne ISIN zulassen, aber nie als bestätigtes Wertpapier. Kleine Queries, Rohdatenhashes und explizite Teilabdeckung verwenden. Lizenz erlaubt Weiterverwendung; Vollständigkeit/aktuelle Kotierung sind gesondert zu prüfen.",
        "3. Pro Börse eine unabhängige Soll-Liste samt MIC, Stichtag und Nutzungsrechten aufbauen und gegen den Ist-Bestand vergleichen. Erst dann eine echte Abdeckungsquote je Börse ausweisen. Corporate Actions, Delistings, Umbenennungen und Mehrklassenfälle erhalten.",
        "4. Amtliche/vertraglich freigegebene Instrumentdaten für ISIN, Gattung, Listing und Emittent ergänzen; LEI/GLEIF erst über belegte Kennungen verbinden. ADR und Heimataktie getrennt; Konzern und Tochter getrennt. CVM-Register allein liefert noch keine vollständige B3-Instrumentliste.",
        "",
        "## Quellen und Nutzbarkeit",
        "",
        "- [Wikidata-Lizenz](https://www.wikidata.org/wiki/Wikidata:Licensing): strukturierte Daten CC0; bestehend freigegebene Alternative für einen globalen Kandidatenbestand.",
        "- [JPX-Emittentenliste](https://www.jpx.co.jp/english/markets/statistics-equities/misc/01.html) und [JPX-Bedingungen](https://www.jpx.co.jp/english/term-of-use/): Excel technisch verfügbar; kommerzielle Sammlung/Weiterverwendung nur mit Erlaubnis oder Vertrag. Nicht als frei importierbar bezeichnet.",
        "- [CVM-Register börsenoffener Gesellschaften](https://dados.cvm.gov.br/dataset/cia_aberta-cad): ODbL ausgewiesen; Datenbank-/Weitergabepflichten vor Integration umsetzen. Registerstatus ist nicht gleich aktive Börsenkotierung.",
        "- [B3-Bedingungen](https://www.b3.com.br/main.jsp?doui_processActionId=setLocaleProcessAction&locale=en_US&lumA=1&lumII=8AE690F77A1A49BA017A5CE182412193&lumPageId=8AE690F77A1A49BA017A5CDEBBCF67BD): keine pauschale kommerzielle Freigabe; schriftliche Zustimmung erforderlich. Keine Freigabe durch Quellenangabe unterstellen.",
        "- [ESMA MiFIR/FIRDS](https://www.esma.europa.eu/data-reporting/mifir-reporting): Instrument-Referenzdaten als Ausbaukandidat; konkrete Datei und Nutzungsrechte weiterhin offen. FCA-FIRDS analog separat prüfen.",
        "- [Naspers](https://www.naspers.com/the-group/group-structure), [Nedbank](https://group.nedbank.co.za/explore-investor-relations/equity-investors.html), [Tesco/LSE](https://www.londonstockexchange.com/en/quote/equity/TSCO/tesco-plc): gezielte Primärbelege für echte Kotierungen trotz fehlendem Katalogtreffer.",
        "- [Mercedes-Benz: Aktie und US-Ticker MBGAF](https://group.mercedes-benz.com/investors/share/) und [Umbenennung Daimler AG](https://group.mercedes-benz.com/company/news/daimler-becomes-mercedes-benz-group.html): erklärt den unter dem aktuellen Namen fehlenden, unter DAIMLER AG vorhandenen SEC-Firmenhinweis. Keine Verwechslung mit Daimler Truck.",
        "",
        "Kein kostenpflichtiger Dienst bestellt, keine neuen Produktionsquellen aktiviert, kein Push und keine öffentliche Datenfreigabe. Die Prüfung beantwortet die Bestandsfrage; die genannten Ausbauten sind noch nicht implementiert.",
    ]
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
