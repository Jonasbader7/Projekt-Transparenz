"""Erzeugt die FIKTIVEN Beispieldaten in data/sample/ (deterministisch).

Alle Unternehmen, Fonds, Herausgeber und Sachverhalte sind erfunden.
* ISINs beginnen mit «ZZ» (ISO-3166 user-assigned, kein reales Land).
* LEIs beginnen mit «FIKT00».
* Quell-URLs zeigen auf example.org (für Beispiele reservierte Domain).

Die Daten decken gezielt alle Belegstufen und Problemfälle ab (siehe
docs/DATA_MODEL.md, Abschnitt «Fiktive Beispieldaten»). Ausführen mit:

    python scripts/generate_sample_data.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from transparenz.entities.identifiers import make_isin, make_lei  # noqa: E402
from transparenz.ingestion.parsing import (  # noqa: E402
    COVERAGE_COLUMNS,
    EVIDENCE_COLUMNS,
    HOLDINGS_COLUMNS,
)

OUT = ROOT / "data" / "sample"
URL = "https://example.org/fiktiv"

# key, Name, LEI-Basis (18) oder None, Land, ISIN-Körper (11) oder None
COMPANIES = [
    ("C01", "Alpenstrom Muster AG", "FIKT00ALPENSTROM01", "CH", "ZZALPSTR001"),
    ("C02", "Nordkohle Beispiel plc", "FIKT00NORDKOHLE001", "GB", "ZZNRDKHL001"),
    ("C03", "Tiefsee Öl & Gas Beispiel SA", "FIKT00TIEFSEEOEL01", "NO", "ZZTFSOEL001"),
    ("C04", "Muster Textil Gruppe AG", "FIKT00MUSTERTEX001", "DE", "ZZMSTTXT001"),
    ("C05", "Waldland Agrar Beispiel Ltd", "FIKT00WALDLAND0001", "BR", "ZZWLDAGR001"),
    ("C06", "Präzisionstechnik Beispiel AG", "FIKT00PRAEZISIO001", "CH", "ZZPRZTCH001"),
    ("C07", "Wehrtechnik Beispiel Holding AG", "FIKT00WEHRTECH0001", "DE", "ZZWHRTCH001"),
    ("C08", "Sonnenpark Beispiel AG", "FIKT00SONNENPARK01", "CH", "ZZSNNPRK001"),
    ("C09", "Grüne Logistik Beispiel AG", "FIKT00GRUENELOG001", "AT", "ZZGRNLGS001"),
    ("C10", "Fernost Handel Beispiel Corp", "FIKT00FERNOSTHA001", "SG", None),
    ("C11", "Medizinal Beispiel AG", "FIKT00MEDIZINAL001", "CH", "ZZMDZNAL001"),
    ("C12", "Datenwolke Beispiel Inc", "FIKT00DATENWOLK001", "US", "ZZDTNWLK001"),
    ("C13", "Kakao Handel Beispiel SA", "FIKT00KAKAOHAND001", "CI", "ZZKKOHDL001"),
    ("C14", "Bergbau Vielfalt Beispiel Ltd", "FIKT00BERGBAU00001", "AU", "ZZBRGBAU001"),
    ("C15", "Versicherung Beispiel AG", "FIKT00VERSICHER001", "CH", "ZZVRSCHR001"),
    ("C16", "Bauchemie Beispiel AG", None, "CH", "ZZBCHEMI001"),
    ("C17", "Bahnbau Beispiel AG", "FIKT00BAHNBAU00001", "CH", "ZZBHNBAU001"),
]
LEI = {k: make_lei(b) for k, _, b, _, _ in COMPANIES if b}
ISIN = {k: make_isin(b) for k, _, _, _, b in COMPANIES if b}
NAME = {k: n for k, n, _, _, _ in COMPANIES}
BOND_ISIN = make_isin("ZZALPSTRB01")
UNKNOWN_ISIN = make_isin("ZZUNBKNT001")
FUND_ISIN = make_isin("ZZFIKETF001")


def write_csv(path: Path, columns: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(columns), lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({c: ("" if r.get(c) is None else r.get(c)) for c in columns})


def holdings() -> list[dict[str, object]]:
    fund = {
        "fund_isin": FUND_ISIN,
        "fund_name": "Muster Nachhaltigkeit Welt ETF (fiktiv)",
        "fund_provider": "Fiktiver ETF-Anbieter (Demo)",
        "fund_as_of_date": "2026-09-30",
        "fund_currency": "CHF",
        "fund_is_fictional": "ja",
        "fund_description": "Erfundener «nachhaltiger» Aktien-ETF zur Demonstration der Methodik.",
    }
    positions = [
        (ISIN["C11"], NAME["C11"], "aktie", 10.0, "CH", "CHF"),
        (ISIN["C12"], NAME["C12"], "aktie", 12.0, "US", "USD"),
        (ISIN["C08"], NAME["C08"], "aktie", 9.0, "CH", "CHF"),
        (ISIN["C15"], NAME["C15"], "aktie", 8.0, "CH", "CHF"),
        (ISIN["C01"], NAME["C01"], "aktie", 6.0, "CH", "CHF"),
        (BOND_ISIN, "Alpenstrom Muster AG 1.5 % 2031", "anleihe", 2.0, "CH", "CHF"),
        (ISIN["C09"], NAME["C09"], "aktie", 6.0, "AT", "EUR"),
        (ISIN["C03"], NAME["C03"], "aktie", 5.5, "NO", "NOK"),
        (ISIN["C06"], NAME["C06"], "aktie", 5.0, "CH", "CHF"),
        (ISIN["C16"], NAME["C16"], "aktie", 5.0, "CH", "CHF"),
        (ISIN["C04"], NAME["C04"], "aktie", 4.5, "DE", "EUR"),
        (ISIN["C17"], NAME["C17"], "aktie", 4.5, "CH", "CHF"),
        (ISIN["C05"], NAME["C05"], "aktie", 4.0, "BR", "BRL"),
        (ISIN["C14"], NAME["C14"], "aktie", 4.0, "AU", "AUD"),
        (ISIN["C13"], NAME["C13"], "aktie", 3.5, "CI", "XOF"),
        (ISIN["C02"], NAME["C02"], "aktie", 3.0, "GB", "GBP"),
        (UNKNOWN_ISIN, "Unbekannte Beteiligung Beispiel AG", "aktie", 3.0, "CH", "CHF"),
        (None, "Barmittel CHF", "barmittel", 3.5, None, "CHF"),
        (None, "Devisentermingeschäft USD/CHF", "derivat", 1.5, None, "CHF"),
    ]
    rows = []
    for isin, name, cls, weight, country, cur in positions:
        rows.append(
            fund | {
                "position_isin": isin,
                "position_name": name,
                "asset_class": cls,
                "weight_pct": weight,
                "country": country,
                "currency": cur,
            }
        )
    return rows


def entities() -> dict[str, object]:
    companies = [
        {"company_key": k, "name": n, "lei": LEI.get(k), "country": c}
        for k, n, _, c, _ in COMPANIES
    ]
    securities = []
    for k, n, _, _, _ in COMPANIES:
        if k not in ISIN:
            continue
        method, conf, src = "register", "hoch", "Fiktives Wertpapierregister (Demo)"
        if k == "C16":
            method, conf, src = "manuell", "mittel", "Manuelle Zuordnung anhand Fiktiv-Factsheet"
        if k == "C17":
            method, conf, src = "name", "tief", "Nur Namensähnlichkeit, nicht bestätigt"
        securities.append(
            {"isin": ISIN[k], "name": f"{n} Namenaktie", "issuer_company_key": k,
             "mapping_method": method, "mapping_confidence": conf, "mapping_source": src}
        )
    securities.append(
        {"isin": BOND_ISIN, "name": "Alpenstrom Muster AG 1.5 % 2031", "issuer_company_key": "C01",
         "mapping_method": "register", "mapping_confidence": "hoch",
         "mapping_source": "Fiktives Wertpapierregister (Demo)"}
    )
    relationships = [
        {"parent_key": "C07", "child_key": "C06", "relationship_type": "direkte_mutter",
         "verified": True, "ownership_pct": 100.0,
         "source": "Fiktiver Geschäftsbericht 2025 der Wehrtechnik Beispiel Holding AG"},
        {"parent_key": "C10", "child_key": "C09", "relationship_type": "direkte_mutter",
         "verified": False, "ownership_pct": 51.0,
         "source": "Fiktiver Medienbericht – Beteiligung nicht bestätigt"},
    ]
    return {
        "_hinweis": "FIKTIVE DEMODATEN – alle Unternehmen und Kennungen sind erfunden.",
        "companies": companies,
        "securities": securities,
        "relationships": relationships,
    }


ETHIKRAT = ("Fiktiver Ethikrat für Anlagen", "institution")
KLIMA = ("Fiktive Klima-Recherche e.V.", "ngo")
MENSCHENRECHTE = ("Fiktive Menschenrechtsbeobachtung", "ngo")
WALD = ("Fiktive Waldallianz", "ngo")
ZEITUNG = ("Fiktive Wirtschaftszeitung", "medien")
PORTAL = ("Fiktives Nachrichtenportal", "medien")


def ev(eid, company, criterion, desc, etype, status, publisher, published, verification,
       reviewed=None, event=None, lei=True, isin=False, name=None, lei_override=None,
       metric=None):
    pub, ptype = publisher
    row = {
        "evidence_id": eid,
        "company_name": name or NAME.get(company, company),
        "lei": lei_override or (LEI.get(company) if lei else None),
        "isin": ISIN.get(company) if isin else None,
        "criterion": criterion,
        "description": desc,
        "evidence_type": etype,
        "proceeding_status": status,
        "publisher": pub,
        "publisher_type": ptype,
        "source_title": f"{pub}: Dokument {eid} (fiktiv)",
        "source_url": f"{URL}/{eid.lower()}",
        "published_date": published,
        "event_date": event,
        "verification_level": verification,
        "last_reviewed": reviewed,
    }
    if metric:
        row |= {"metric_name": metric[0], "metric_value": metric[1], "metric_unit": metric[2]}
    return row


def exclusion_list() -> list[dict[str, object]]:
    return [
        ev("ETH-001", "C01", "kohle",
           "Ausschluss wegen Stromerzeugung aus Kohle; Umsatzanteil laut Ethikrat 32 %.",
           "ausschlussentscheid", "abgeschlossen", ETHIKRAT, "2025-06-15", "quelle_gesichtet",
           reviewed="2026-09-01", metric=("umsatzanteil_kohle", 32.0, "%")),
        ev("ETH-002", "C02", "kohle", "Ausschluss wegen Abbau von Kraftwerkskohle.",
           "ausschlussentscheid", "abgeschlossen", ETHIKRAT, "2024-11-20", "quelle_gesichtet",
           reviewed="2026-09-01", metric=("umsatzanteil_kohle", 78.0, "%")),
        ev("ETH-003", "C07", "geaechtete_waffen",
           "Ausschluss wegen Herstellung von Schlüsselkomponenten für Streumunition.",
           "ausschlussentscheid", "abgeschlossen", ETHIKRAT, "2023-03-10", "quelle_gesichtet",
           reviewed="2026-09-01"),
    ]


def evidence_collection() -> list[dict[str, object]]:
    rows = [
        ev("BEL-001", "C01", "kohle",
           "Recherche dokumentiert den geplanten Ausbau eines Kohlekraftwerks um 400 MW.",
           "vorwurf", "nicht_anwendbar", KLIMA, "2026-02-10", "dokument_geprueft",
           reviewed="2026-10-01"),
        ev("BEL-002", "C03", "oel_gas_expansion",
           "Bewilligung zur Erschliessung von zwei neuen Offshore-Gasfeldern erteilt.",
           "behoerdliche_feststellung", "abgeschlossen",
           ("Fiktive Energieaufsicht Nordmeer", "behoerde"), "2025-09-30", "dokument_geprueft",
           reviewed="2026-10-01", event="2025-09-30"),
        ev("BEL-003", "C03", "oel_gas_expansion",
           "Bericht über geplante Investitionen von 2 Mrd. in neue Förderprojekte.",
           "vorwurf", "nicht_anwendbar", ZEITUNG, "2026-03-05", "ungeprueft",
           lei=False, isin=True),
        ev("BEL-004", "C03", "oel_gas_expansion",
           "Das Unternehmen bezeichnet die Projekte als notwendig für die Versorgungssicherheit.",
           "unternehmensstellungnahme", "nicht_anwendbar",
           (NAME["C03"], "unternehmen"), "2026-03-07", "quelle_gesichtet"),
        ev("BEL-005", "C04", "zwangs_kinderarbeit",
           "Recherche dokumentiert Hinweise auf Zwangsarbeit bei einem Zulieferer "
           "(Interviews, Lieferdokumente).",
           "vorwurf", "nicht_anwendbar", MENSCHENRECHTE, "2026-05-12", "quelle_gesichtet",
           reviewed="2026-10-01"),
        ev("BEL-006", "C04", "zwangs_kinderarbeit",
           "Beschwerde gegen das Unternehmen zur vertieften Prüfung angenommen; Verfahren laufend.",
           "vorwurf", "laufend",
           ("Fiktive Nationale Kontaktstelle für Unternehmensverantwortung", "behoerde"),
           "2026-07-01", "quelle_gesichtet", reviewed="2026-10-01"),
        ev("BEL-007", "C04", "zwangs_kinderarbeit",
           "Das Unternehmen weist die Vorwürfe zurück und kündigt ein externes Audit an.",
           "unternehmensstellungnahme", "nicht_anwendbar",
           (NAME["C04"], "unternehmen"), "2026-05-20", "quelle_gesichtet"),
        ev("BEL-008", "C05", "entwaldung",
           "Gericht bestätigt eine Busse wegen illegaler Rodung von 1 200 ha Primärwald.",
           "gerichtsurteil", "abgeschlossen",
           ("Fiktives Verwaltungsgericht Musterkanton", "gericht"), "2025-03-12",
           "dokument_geprueft", reviewed="2026-10-01", event="2023-08-01"),
        ev("BEL-009", "C05", "entwaldung",
           "Satellitenanalyse zeigt fortgesetzte Rodungen in Zulieferbetrieben.",
           "vorwurf", "nicht_anwendbar", WALD, "2026-04-02", "quelle_gesichtet",
           reviewed="2026-10-01"),
        ev("BEL-010", "C05", "entwaldung",
           "Das Unternehmen meldet ein Wiederaufforstungsprogramm und ein Lieferantenaudit.",
           "abhilfe", "nicht_anwendbar", (NAME["C05"], "unternehmen"), "2026-06-15",
           "quelle_gesichtet"),
        ev("BEL-011", "C07", "geaechtete_waffen",
           "Exportbehörde stellt Lieferung von Streumunitions-Komponenten fest (Verfügung).",
           "behoerdliche_feststellung", "abgeschlossen",
           ("Fiktive Exportkontrollbehörde", "behoerde"), "2024-05-08", "quelle_gesichtet",
           reviewed="2026-08-15"),
        ev("BEL-012", "C10", "zwangs_kinderarbeit",
           "Bericht über Zwangsarbeit in Lagerbetrieben des Konzerns.",
           "vorwurf", "nicht_anwendbar", MENSCHENRECHTE, "2026-01-20", "quelle_gesichtet",
           reviewed="2026-10-01"),
        ev("BEL-013", "C13", "zwangs_kinderarbeit",
           "Bericht über Kinderarbeit auf Zulieferplantagen.",
           "vorwurf", "nicht_anwendbar", PORTAL, "2026-06-01", "ungeprueft",
           lei=False, name="Kakao Handel Beispiel S.A."),
        ev("BEL-014", "C13", "zwangs_kinderarbeit",
           "Artikel greift den Bericht über Kinderarbeit auf Zulieferplantagen auf.",
           "vorwurf", "nicht_anwendbar", ZEITUNG, "2026-06-03", "ungeprueft",
           lei=False, name="Kakao Handel Beispiel"),
        ev("BEL-015", "C14", "kohle",
           "Recherche beziffert den Umsatzanteil aus Kraftwerkskohle auf 4 %.",
           "vorwurf", "nicht_anwendbar", KLIMA, "2026-03-15", "quelle_gesichtet",
           reviewed="2026-10-01", metric=("umsatzanteil_kohle", 4.0, "%")),
        ev("BEL-016", "C17", "zwangs_kinderarbeit",
           "Recherche zu Arbeitsbedingungen bei einem Subunternehmer im Gleisbau.",
           "vorwurf", "nicht_anwendbar", MENSCHENRECHTE, "2026-02-25", "quelle_gesichtet",
           reviewed="2026-10-01"),
        ev("BEL-017", "Phantom Minen Beispiel GmbH", "geaechtete_waffen",
           "Bericht über Produktion von Antipersonenminen.",
           "vorwurf", "nicht_anwendbar", PORTAL, "2026-04-11", "ungeprueft", lei=False),
        ev("BEL-018", "C08", "entwaldung",
           "Bericht über Rodungen für einen Solarpark – betrifft eine gleichnamige "
           "Gesellschaft mit anderem LEI.",
           "vorwurf", "nicht_anwendbar", ZEITUNG, "2026-08-08", "ungeprueft",
           lei_override=make_lei("FIKT00SONNENPARK02")),
    ]
    # Absichtlich ein exaktes Duplikat: zeigt die Duplikaterkennung (Warnung, entfernt).
    rows.append(dict(rows[4]))
    return rows


def coverage(keys: list[str], criteria: list[str], reviewed: str) -> list[dict[str, object]]:
    rows = []
    for k in keys:
        for c in criteria:
            row = {"company_name": NAME[k], "lei": LEI.get(k), "criterion": c,
                   "reviewed_date": reviewed}
            if k not in LEI:
                row["isin"] = ISIN[k]  # ohne LEI über das Wertpapier identifiziert
            rows.append(row)
    return rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / "fiktiv_etf_positionen.csv", HOLDINGS_COLUMNS, holdings())
    (OUT / "fiktiv_stammdaten.json").write_text(
        json.dumps(entities(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_csv(OUT / "fiktiv_ausschlussliste.csv", EVIDENCE_COLUMNS, exclusion_list())
    write_csv(OUT / "fiktiv_belegsammlung.csv", EVIDENCE_COLUMNS, evidence_collection())
    ethikrat_universe = [f"C{i:02d}" for i in range(1, 18) if i != 12]
    write_csv(
        OUT / "fiktiv_ausschlussliste_abdeckung.csv", COVERAGE_COLUMNS,
        coverage(ethikrat_universe, ["kohle", "geaechtete_waffen"], "2026-09-01"),
    )
    research = ["C01", "C03", "C04", "C05", "C08", "C09", "C11", "C13", "C14", "C15"]
    write_csv(
        OUT / "fiktiv_belegsammlung_abdeckung.csv", COVERAGE_COLUMNS,
        coverage(research, ["zwangs_kinderarbeit", "entwaldung", "oel_gas_expansion"],
                 "2026-10-01"),
    )
    print(f"Fiktive Beispieldaten geschrieben nach {OUT}")


if __name__ == "__main__":
    main()
