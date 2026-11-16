"""Pilot «Position → Unternehmen → Beleg»: ausschliesslich fiktive Kennungen und Namen."""
import csv
import gzip
import importlib.util
import io
import sys
import zipfile
from pathlib import Path

import httpx
import pytest

from transparenz.entities.identifiers import make_isin, make_lei
from transparenz.ingestion.eu_ets import load_ets, summarise_ets
from transparenz.ingestion.fi_holdings import find_fund, parse_fund
from transparenz.ingestion.gem import classify_gem_assets, gem_stake, gem_status, load_gem
from transparenz.ingestion.gleif_lookup import fetch_gleif, load_group_links
from transparenz.ingestion.wikidata_isin import fetch_wikidata_isins, wikidata_candidates
from transparenz.reports.fund_chain_report import (
    CRITERION_TESTS,
    GENERIC_CRITERION_TEST,
    criteria_readiness,
    criteria_status,
    explain_finding,
    render_html,
    render_markdown,
)
from transparenz.services.entity_matching import DEVELOPMENT_FUNDS, names_agree, position_region
from transparenz.services.fund_chain import (
    build_chain,
    index_candidates,
    index_emissions,
    mapping_confidence,
    name_check,
    relationship_timing,
    review_queue,
)
from transparenz.services.fund_findings import expansion_finding, sensitivity
from transparenz.services.mapping_reference import dispute_queue, evaluate_methods, reference_cases

ISIN_A = make_isin("ZZ000000001")
ISIN_B = make_isin("ZZ000000002")
ISIN_C = make_isin("ZZ000000003")
ISIN_D = make_isin("ZZ000000004")
LEI_PARENT = make_lei("FIKT00000000000001")
LEI_CHILD = make_lei("FIKT00000000000002")
LEI_HINT_CHILD = make_lei("FIKT00000000000003")
LEI_OTHER = make_lei("FIKT00000000000004")
NS = "http://schemas.fi.se/publika/vardepappersfonder/20200331"


def test_command_line_script_loads() -> None:
    """Das Skript ist nur Befehlszeile; seine Importe aus dem Paket müssen auflösen."""
    path = Path(__file__).parents[1] / "scripts/pilot_fund_chain.py"
    spec = importlib.util.spec_from_file_location("pilot_fund_chain_cli", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    assert callable(module.main)
    with pytest.raises(SystemExit):
        module.main(["--help"])


def fund_xml(name: str = "Fiktiver Testfonds", positions: tuple = ()) -> bytes:
    items = "".join(
        f"<FinansielltInstrument><Instrumentnamn>{title}</Instrumentnamn>"
        f"<ISIN-kod_instrument>{isin}</ISIN-kod_instrument><Landkod_Emittent>ZZ</Landkod_Emittent>"
        f"<Valuta>CHF</Valuta><Marknadsvärde_instrument>100</Marknadsvärde_instrument>"
        f"<Andel_av_fondförmögenhet_instrument>{weight}</Andel_av_fondförmögenhet_instrument>"
        "</FinansielltInstrument>" for title, isin, weight in positions)
    return (
        f'<?xml version="1.0" encoding="utf-8"?><VärdepappersfondInnehav xmlns="{NS}">'
        "<Rapportinformation><Kvartalsslut>2099-06-30</Kvartalsslut></Rapportinformation>"
        "<Bolagsinformation><Fondbolag_namn>Fiktive Fondsleitung</Fondbolag_namn>"
        "</Bolagsinformation><Fondinformation>"
        f"<Fond_namn>{name}</Fond_namn><Fondförmögenhet>400</Fondförmögenhet>"
        f"<FinansiellaInstrument>{items}</FinansiellaInstrument></Fondinformation>"
        "<Fondinformation /></VärdepappersfondInnehav>").encode()


POSITIONS = (("Fiktive Mutter AG", ISIN_A, "40"), ("Fiktive Zweideutig AG", ISIN_B, "30"),
             ("Fiktive Unbekannt AG", ISIN_C, "20"), ("Kaputte Kennung", "ZZ0000000000", "10"))


def candidate(isin: str, item: str, *leis: str) -> dict:
    return {"isin": isin, "wikidata_id": item, "name": f"Fiktiv {item}",
            "claims": {"P1278": list(leis)}}


def emission(lei: str, year: int = 2099) -> dict:
    return {"company_key": f"lei:{lei}", "mapping_status": "exact_uid_match", "year": year,
            "uid_facility": "CHE000000000", "data_as_of": "2099-12-31",
            "pollutant_name": "Fiktiver Stoff", "medium": "Luft", "value": 1.5, "unit": "kg/a"}


def link(child: str, parent: str, verified: bool) -> dict:
    return {"child_lei": child, "kind": "direct-parent", "parent_lei": parent,
            "corroboration_level": "FULLY_CORROBORATED" if verified else "ENTITY_SUPPLIED_ONLY",
            "verified": verified}


def test_parse_fund_reads_positions_and_flags_invalid_isin():
    fund = parse_fund(fund_xml(positions=POSITIONS))
    assert (fund.fund_name, fund.quarter_end, len(fund.positions)) == (
        "Fiktiver Testfonds", "2099-06-30", 4)
    assert [p.isin_valid for p in fund.positions] == [True, True, True, False]
    assert fund.positions[0].weight_percent == 40.0


def test_parse_fund_rejects_file_without_fund():
    with pytest.raises(ValueError):
        parse_fund(f'<VärdepappersfondInnehav xmlns="{NS}"/>'.encode())


def test_chain_transfers_evidence_only_over_verified_relationship():
    fund = parse_fund(fund_xml(positions=POSITIONS))
    candidates = index_candidates([
        candidate(ISIN_A, "Q1", LEI_PARENT),
        candidate(ISIN_B, "Q2", LEI_OTHER), candidate(ISIN_B, "Q3", LEI_OTHER)])
    emissions = index_emissions([
        emission(LEI_CHILD), emission(LEI_CHILD, 2098), emission(LEI_HINT_CHILD),
        emission(LEI_OTHER),
        {**emission(LEI_PARENT), "mapping_status": "unresolved"}])
    gleif = {"names": {LEI_CHILD: {"legal_name": "Fiktive Tochter AG"}},
             "parents": [link(LEI_CHILD, LEI_PARENT, True),
                         link(LEI_HINT_CHILD, LEI_PARENT, False)]}
    report = build_chain(fund, candidates, emissions, gleif)
    mother, ambiguous, unknown, broken = report["positions"]

    assert mother["mapping_status"] == "unverified_candidate_with_lei"
    assert [e["via"] for e in mother["evidence"]] == ["verified_group_relationship"]
    assert mother["evidence"][0]["child_legal_name"] == "Fiktive Tochter AG"
    assert mother["evidence"][0]["years"] == [2098, 2099]
    assert [h["child_lei"] for h in mother["group_hints"]] == [LEI_HINT_CHILD]
    # Zwei Wikidata-Einträge für dieselbe ISIN: kein Beleg, obwohl der LEI Emissionen meldet.
    assert ambiguous["mapping_status"] == "ambiguous_candidate" and not ambiguous["evidence"]
    assert unknown["mapping_status"] == "unknown_no_mapping_source" and unknown["company"] is None
    assert broken["mapping_status"] == "no_valid_isin"
    summary = report["summary"]
    assert summary["with_valid_isin"] == {"positions": 3, "weight_percent": 90.0}
    assert summary["with_company_candidate"] == {"positions": 2, "weight_percent": 70.0}
    assert summary["with_evidence"] == {"positions": 1, "weight_percent": 40.0}
    markdown = render_markdown(report)
    assert "kein Nachweis eines Rechtsverstosses" in markdown
    assert "Finansinspektionen (FI)" in markdown and "2099-06-30" in markdown


def test_chain_without_gleif_uses_only_direct_evidence():
    fund = parse_fund(fund_xml(positions=POSITIONS[:1]))
    report = build_chain(
        fund, index_candidates([candidate(ISIN_A, "Q1", LEI_PARENT)]),
        index_emissions([emission(LEI_PARENT), emission(LEI_CHILD)]), None)
    assert [e["via"] for e in report["positions"][0]["evidence"]] == ["direct"]


def sparql_row(isin: str, item: str, lei: str | None = None) -> dict:
    row = {"isin": {"value": isin}, "item": {"value": f"http://www.wikidata.org/entity/{item}"},
           "itemLabel": {"value": f"Fiktiv {item}"}}
    if lei:
        row["lei"] = {"value": lei}
    return row


def test_wikidata_lookup_sends_only_valid_isins_and_keeps_ambiguity():
    queries: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        queries.append(request.content.decode())
        return httpx.Response(200, json={"results": {"bindings": [
            sparql_row(ISIN_A, "Q1", LEI_PARENT), sparql_row(ISIN_A, "Q1", LEI_PARENT),
            sparql_row(ISIN_C, "Q7", LEI_OTHER), sparql_row(ISIN_C, "Q8"),
            sparql_row(ISIN_D, "Q9")]}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    lookup = fetch_wikidata_isins(
        [ISIN_A, ISIN_C, ISIN_D, "ZZ0000000000", 'X" } DROP'], "test-agent", client,
        lambda _: None)
    assert lookup["isins_queried"] == [ISIN_A, ISIN_C, ISIN_D]
    assert len(queries) == 1 and "ZZ0000000000" not in queries[0] and "DROP" not in queries[0]

    extra = wikidata_candidates(lookup)
    assert sorted((c["isin"], c["wikidata_id"], tuple(c["claims"]["P1278"])) for c in extra) == [
        (ISIN_A, "Q1", (LEI_PARENT,)), (ISIN_C, "Q7", (LEI_OTHER,)), (ISIN_C, "Q8", ()),
        (ISIN_D, "Q9", ())]

    # Lokaler Kandidat und Wikidata-Abfrage nennen denselben Eintrag: bleibt ein Unternehmen.
    fund = parse_fund(fund_xml(positions=(
        ("Fiktive Mutter AG", ISIN_A, "40"), ("Fiktive Doppelt AG", ISIN_C, "30"),
        ("Fiktive Ohne LEI AG", ISIN_D, "20"))))
    candidates = index_candidates([candidate(ISIN_A, "Q1", LEI_PARENT), *extra])
    report = build_chain(fund, candidates, index_emissions([emission(LEI_PARENT)]),
                               None)
    mother, double, without_lei = report["positions"]
    assert mother["company"]["wikidata_ids"] == ["Q1"]
    assert [e["via"] for e in mother["evidence"]] == ["direct"]
    assert double["mapping_status"] == "ambiguous_candidate"
    assert without_lei["mapping_status"] == "candidate_without_lei"
    assert report["summary"]["with_unique_lei"] == {"positions": 1, "weight_percent": 40.0}
    html = render_html(report, [])
    assert "Fiktive Ohne LEI AG" in html and "Unternehmen ohne LEI" in html


def test_wikidata_lookup_fails_loudly_on_http_error():
    failing = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(429)))
    with pytest.raises(httpx.HTTPStatusError):
        fetch_wikidata_isins([ISIN_A], "test-agent", failing, lambda _: None)


def test_lei_unknown_to_gleif_blocks_evidence():
    fund = parse_fund(fund_xml(positions=POSITIONS[:1]))
    candidates = index_candidates([candidate(ISIN_A, "Q1", LEI_PARENT)])
    emissions = index_emissions([emission(LEI_PARENT)])
    checked_missing = {"names": {}, "names_checked": [LEI_PARENT], "parents": []}
    row = build_chain(fund, candidates, emissions, checked_missing)["positions"][0]
    assert row["mapping_status"] == "candidate_lei_not_in_gleif" and not row["evidence"]
    checked_found = {"names": {LEI_PARENT: {"legal_name": "Fiktive Mutter AG", "country": "ZZ",
                                            "entity_status": "ACTIVE",
                                            "registration_status": "ISSUED"}},
                     "names_checked": [LEI_PARENT], "parents": []}
    row = build_chain(fund, candidates, emissions, checked_found)["positions"][0]
    assert row["mapping_status"] == "unverified_candidate_with_lei" and row["evidence"]


OPERATOR_HEADER = ("INSTALLATION_IDENTIFIER,REGISTRY_CODE,INSTALLATION_NAME,ACTIVITY_TYPE,"
                   "PERMIT_REVOCATION_DATE,ACCOUNT_HOLDER_NAME,ACCOUNT_HOLDER_LEI,SNAPSHOT_DATE")


def hyphenated(lei: str) -> str:
    """Schreibweise des Registers: XXXX-XXXXXXXXXXXXXX-XX."""
    return f"{lei[:4]}-{lei[4:18]}-{lei[18:]}"


def write_gz(path: Path, lines: list[str]) -> Path:
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        handle.write("\n".join(lines) + "\n")
    return path


@pytest.fixture
def ets_files(tmp_path):
    operators = write_gz(tmp_path / "operators_daily.csv.gz", [
        OPERATOR_HEADER,
        f"1,ZZ,Fiktives Werk A,Combustion of fuels,,Fiktive Tochter AG,{hyphenated(LEI_CHILD)},"
        "2099-11-11",
        f"2,ZZ,Fiktives Werk B,Combustion of fuels,2098-01-01,Fiktive Tochter AG,{LEI_CHILD},"
        "2099-11-11",
        f"3,ZZ,Fiktives Werk C,Combustion of fuels,,Fiktive Mutter AG,{LEI_PARENT},2099-11-11",
        "4,ZZ,Fiktives Werk D,Combustion of fuels,,Fiktiv ohne LEI,,2099-11-11",
        "5,ZZ,Fiktives Werk E,Combustion of fuels,,Fiktiv kaputt,FIKT-00000000000000-00,"
        "2099-11-11",
        f"6,ZZ,Fiktives Werk F,Combustion of fuels,,Fiktive Hinweis AG,{LEI_HINT_CHILD},"
        "2099-11-11"])
    activity = write_gz(tmp_path / "operators_yearly_activity_daily.csv.gz", [
        "INSTALLATION_IDENTIFIER,REGISTRY_CODE,PERIOD_YEAR,VERIFIED_EMISSIONS",
        "1,ZZ,2097,100", "1,ZZ,2098,120.5", "1,ZZ,2099,n/a", "2,ZZ,2096,7",
        "3,ZZ,2099,n/a", "4,ZZ,2099,999", "6,ZZ,2099,5"])
    return operators, activity


def test_load_ets_keeps_only_valid_leis_and_ignores_missing_values(ets_files):
    ets = load_ets(*ets_files)
    assert ets["snapshot_date"] == "2099-11-11"
    assert ets["stats"] == {"installations": 6, "with_lei_field": 5, "invalid_lei": 1,
                            "with_valid_lei": 4, "distinct_leis": 3}
    child = {i["installation_id"]: i for i in ets["by_lei"][LEI_CHILD]}
    assert child["1"]["verified_emissions"] == {2097: 100.0, 2098: 120.5}  # «n/a» ist kein 0
    assert ets["by_lei"][LEI_PARENT][0]["verified_emissions"] == {}
    # Ohne verifizierten Jahreswert entsteht kein Beleg.
    assert summarise_ets(LEI_PARENT, ets["by_lei"][LEI_PARENT], "2099-11-11") is None
    summary = summarise_ets(LEI_CHILD, ets["by_lei"][LEI_CHILD], "2099-11-11")
    assert [(i["installation_id"], i["latest_year"], i["latest_verified_t_co2e"],
             i["permit_revocation_date"]) for i in summary["installations"]] == [
        ("1", 2098, 120.5, None), ("2", 2096, 7.0, "2098-01-01")]


def test_load_ets_rejects_missing_columns(tmp_path):
    operators = write_gz(tmp_path / "operators_daily.csv.gz", ["INSTALLATION_IDENTIFIER", "1"])
    activity = write_gz(tmp_path / "activity.csv.gz", ["INSTALLATION_IDENTIFIER", "1"])
    with pytest.raises(ValueError, match="Spalten fehlen"):
        load_ets(operators, activity)


def rr_zip(tmp_path: Path, rows: list[tuple]) -> Path:
    header = ["Relationship.StartNode.NodeID", "Relationship.StartNode.NodeIDType",
              "Relationship.EndNode.NodeID", "Relationship.EndNode.NodeIDType",
              "Relationship.RelationshipType", "Relationship.RelationshipStatus",
              "Registration.RegistrationStatus", "Registration.ValidationSources"]
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows(rows)
    path = tmp_path / "fiktiv-rr-golden-copy.csv.zip"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("fiktiv-rr.csv", buffer.getvalue())
    return path


def test_group_links_from_file_filter_and_verify(tmp_path):
    path = rr_zip(tmp_path, [
        (LEI_CHILD, "LEI", LEI_PARENT, "LEI", "IS_DIRECTLY_CONSOLIDATED_BY", "ACTIVE",
         "PUBLISHED", "FULLY_CORROBORATED"),
        (LEI_HINT_CHILD, "LEI", LEI_PARENT, "LEI", "IS_ULTIMATELY_CONSOLIDATED_BY", "ACTIVE",
         "PUBLISHED", "ENTITY_SUPPLIED_ONLY"),
        (LEI_OTHER, "LEI", LEI_PARENT, "LEI", "IS_DIRECTLY_CONSOLIDATED_BY", "ACTIVE",
         "PUBLISHED", "FULLY_CORROBORATED"),  # Kind ohne Beleg: wird nicht geladen
        (LEI_CHILD, "LEI", LEI_OTHER, "LEI", "IS_DIRECTLY_CONSOLIDATED_BY", "ACTIVE",
         "PUBLISHED", "FULLY_CORROBORATED"),  # Mutter nicht im Fonds
        (LEI_CHILD, "LEI", LEI_PARENT, "LEI", "IS_INTERNATIONAL_BRANCH_OF", "ACTIVE",
         "PUBLISHED", "FULLY_CORROBORATED")])
    links = load_group_links(path, {LEI_CHILD, LEI_HINT_CHILD}, {LEI_PARENT})
    assert [(link["child_lei"], link["kind"], link["verified"]) for link in links] == [
        (LEI_CHILD, "direct-parent", True), (LEI_HINT_CHILD, "ultimate-parent", False)]


def test_chain_combines_swissprtr_and_eu_ets_evidence(ets_files, tmp_path):
    fund = parse_fund(fund_xml(positions=POSITIONS[:1]))
    candidates = index_candidates([candidate(ISIN_A, "Q1", LEI_PARENT)])
    emissions = index_emissions([emission(LEI_CHILD)])
    ets = load_ets(*ets_files)
    links = load_group_links(rr_zip(tmp_path, [
        (LEI_CHILD, "LEI", LEI_PARENT, "LEI", "IS_DIRECTLY_CONSOLIDATED_BY", "ACTIVE",
         "PUBLISHED", "FULLY_CORROBORATED"),
        (LEI_CHILD, "LEI", LEI_PARENT, "LEI", "IS_ULTIMATELY_CONSOLIDATED_BY", "ACTIVE",
         "PUBLISHED", "FULLY_CORROBORATED"),
        (LEI_HINT_CHILD, "LEI", LEI_PARENT, "LEI", "IS_DIRECTLY_CONSOLIDATED_BY", "ACTIVE",
         "PUBLISHED", "ENTITY_SUPPLIED_ONLY")]), set(ets["by_lei"]) | {LEI_CHILD}, {LEI_PARENT})
    report = build_chain(fund, candidates, emissions, None, ets, links)
    row = report["positions"][0]
    # Mutter hat eine Anlage ohne verifizierten Wert: kein direkter Beleg.
    assert sorted((e["via"], e["source"]) for e in row["evidence"]) == [
        ("verified_group_relationship", "eu_ets"), ("verified_group_relationship", "swissprtr")]
    assert [(h["child_lei"], h["sources"]) for h in row["group_hints"]] == [
        (LEI_HINT_CHILD, ["eu_ets"])]
    summary = report["summary"]
    assert summary["with_evidence"]["positions"] == 1
    assert summary["with_evidence_eu_ets"]["positions"] == 1
    assert summary["with_evidence_swissprtr"]["positions"] == 1
    # Ohne GLEIF-Namen und ohne Beginn der Beziehung wird nichts bestätigt, aber alles gezeigt.
    assert summary["with_confirmed_evidence"]["positions"] == 0
    assert {e["status"] for e in row["evidence"]} == {"position_mapping_unconfirmed"}
    assert set(row["evidence"][0]["blocking"]) == {"position_mapping_unconfirmed",
                                                   "relationship_start_unknown"}
    markdown = render_markdown(report)
    assert "Separat: nicht mitgezählte Belege" in markdown
    assert "ZZ-1 «Fiktives Werk A»" in markdown and "120 t CO2e" in markdown
    assert "Genehmigung widerrufen 01.01.2098" in markdown
    assert "Quelle Emissionshandel" in markdown
    assert "**Sichtprüfung nötig:**" not in markdown  # Name nicht abgefragt: keine Warnung


def test_name_check_only_flags_and_never_blocks_evidence(ets_files):
    assert name_check(["Fiktive Tochter AG"], "FIKTIVE TOCHTER AKTIENGESELLSCHAFT") == (
        "shared_word")
    assert name_check(["Fiktive Reederei Ltd"], "Fiktive Tochter AG") == "shared_word"
    assert name_check(["Ganz Anders Ltd"], "Fiktive Tochter AG") == "different"
    assert name_check(["Ganz Anders AG"], None) == "not_checked"

    fund = parse_fund(fund_xml(positions=POSITIONS[:1]))
    candidates = index_candidates([candidate(ISIN_A, "Q1", LEI_CHILD)])
    gleif = {"names": {LEI_CHILD: {"legal_name": "Ganz Andere Holding", "country": "ZZ",
                                   "entity_status": "ACTIVE", "registration_status": "ISSUED"}},
             "names_checked": [LEI_CHILD], "parents": []}
    report = build_chain(fund, candidates, {}, gleif, load_ets(*ets_files))
    evidence = report["positions"][0]["evidence"]
    assert [(e["via"], e["source"], e["name_check"]) for e in evidence] == [
        ("direct", "eu_ets", "different")]
    assert report["summary"]["with_identity_conflict"]["positions"] == 1
    assert report["summary"]["with_confirmed_evidence"]["positions"] == 0
    assert "**Sichtprüfung nötig:**" in render_markdown(report)
    html = render_html(report, [])
    assert "5.1 Identitätskonflikte im Register" in html and "Fiktive Tochter AG" in html


def gleif_entry(name: str, status: str = "ISSUED", *other: str) -> dict:
    return {"legal_name": name, "other_names": [{"name": n, "type": "PREVIOUS_LEGAL_NAME"}
                                                for n in other],
            "country": "ZZ", "entity_status": "ACTIVE", "registration_status": status}


def test_names_agree_handles_accents_spacing_and_generic_words():
    assert names_agree(["Fiktiv Nestle Reg"], ["FIKTIV NESTLÉ S.A."]) is True
    assert names_agree(["U C B"], ["UCB SA"]) is True
    assert names_agree(["Cap Fiktiv"], ["CAPFIKTIV"]) is True
    assert names_agree(["Fiktive Energy Holding"], ["Andere Energy Holding"]) is False
    assert names_agree(["Fiktive AG"], [None]) is None


def test_mapping_confidence_uses_previous_names_and_flags_lapsed():
    names = {LEI_PARENT: gleif_entry("Neue Fiktiv AG", "ISSUED", "Fiktive Mutter AG"),
             LEI_OTHER: gleif_entry("Fiktive Mutter AG", "LAPSED"),
             LEI_CHILD: gleif_entry("Ganz Anders AG")}
    checked = set(names)
    assert mapping_confidence("Fiktive Mutter AG", LEI_PARENT, names, checked) == (
        "consistent")
    assert mapping_confidence("Fiktive Mutter AG", LEI_OTHER, names, checked) == (
        "consistent_lapsed")
    assert mapping_confidence("Fiktive Mutter AG", LEI_CHILD, names, checked) == (
        "name_mismatch")
    assert mapping_confidence("Fiktive Mutter AG", LEI_HINT_CHILD, names, checked | {
        LEI_HINT_CHILD}) == "lei_not_in_gleif"


@pytest.mark.parametrize(("start", "end", "first", "last", "valid", "status"), [
    ("2098-01-01", None, 2098, None, True, "ok"),
    ("2098-06-01", None, 2099, None, True, "ok"),
    ("2098-06-01", "2099-06-30", 2099, 2098, True, "ok"),
    ("2099-07-01", None, 2100, None, False, "relationship_not_valid_at_fund_date"),
    (None, None, None, None, None, "relationship_start_unknown")])
def test_relationship_timing(start, end, first, last, valid, status):
    timing = relationship_timing({"relationship_start": start, "relationship_end": end,
                                        "registration_initial_date": "2098-06-01"},
                                       "2099-06-30")
    assert (timing["first_full_year"], timing["last_full_year"], timing["valid_at_fund_date"],
            timing["status"]) == (first, last, valid, status)
    assert timing["start_is_registration_date"] is (start == "2098-06-01")


def dated_link(child: str, start: str | None, verified: bool = True) -> dict:
    return {**link(child, LEI_PARENT, verified), "relationship_start": start,
            "relationship_end": None, "registration_initial_date": None}


def test_group_evidence_only_counts_years_inside_relationship():
    fund = parse_fund(fund_xml(positions=POSITIONS[:1]))
    candidates = index_candidates([candidate(ISIN_A, "Q1", LEI_PARENT)])
    emissions = index_emissions([
        emission(LEI_CHILD, 2097), emission(LEI_CHILD, 2098), emission(LEI_CHILD, 2099),
        emission(LEI_HINT_CHILD, 2096)])
    gleif = {"names": {LEI_PARENT: gleif_entry("Fiktive Mutter AG"),
                       LEI_CHILD: gleif_entry("Fiktive Tochter AG"),
                       LEI_HINT_CHILD: gleif_entry("Fiktive Hinweis AG")},
             "names_checked": [LEI_PARENT, LEI_CHILD, LEI_HINT_CHILD],
             "parents": [dated_link(LEI_CHILD, "2098-06-01"),
                         dated_link(LEI_HINT_CHILD, "2098-06-01")]}
    report = build_chain(fund, candidates, emissions, gleif)
    row = report["positions"][0]
    assert row["mapping_confidence"] == "consistent"
    by_child = {(e["child_lei"], e["status"]): e for e in row["evidence"]}
    confirmed = by_child[(LEI_CHILD, "confirmed")]
    assert confirmed["years"] == [2099, 2099] and confirmed["timing"]["first_full_year"] == 2099
    assert (LEI_HINT_CHILD, "outside_relationship_period") in by_child
    summary = report["summary"]
    assert summary["confirmed_coverage"]["positions"] == 1
    assert summary["with_confirmed_evidence_swissprtr"]["positions"] == 1
    assert [r["child_lei"] for r in report["group_relationships"]] == [LEI_CHILD, LEI_HINT_CHILD]
    html = render_html(report, [{"key": "fiktiv", "name": "Fiktives Kriterium",
                                       "description": "nur zum Test"}])
    assert "zugerechnet ab 2099" in html
    assert "Emissionsjahre vor Beginn der Konzernbeziehung" in html
    assert "Fiktives Kriterium" in html and "Unbekannt (keine Datenabdeckung)" in html


def test_criteria_are_unknown_without_a_covering_source():
    status = criteria_status([{"key": "a", "name": "A"}, {"key": "b", "name": "B"}])
    assert [(c["key"], c["status"], c["evidence_count"]) for c in status] == [
        ("a", "unbekannt", 0), ("b", "unbekannt", 0)]


def test_find_fund_requires_exactly_one_exact_name(tmp_path):
    archive = tmp_path / "fiktiv.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("a/eins.xml", fund_xml("Fiktiver Testfonds", POSITIONS[:1]))
        handle.writestr("a/zwei.xml", fund_xml("Fiktiver Testfonds Plus", POSITIONS[:1]))
        handle.writestr("a/kaputt.xml", b"<kein-xml")
    member, fund = find_fund(archive, "fiktiver testfonds")
    assert member == "a/eins.xml" and fund.fund_name == "Fiktiver Testfonds"
    with pytest.raises(ValueError, match="0 Treffer"):
        find_fund(archive, "Fiktiver")


def test_fetch_gleif_treats_404_as_no_relationship_and_fails_on_other_errors():
    relationship = {"data": {"attributes": {
        "relationship": {"endNode": {"id": LEI_PARENT}, "status": "ACTIVE", "periods": [
            {"startDate": "2090-01-01T00:00:00Z", "endDate": "2090-12-31T00:00:00Z",
             "type": "ACCOUNTING_PERIOD"},
            {"startDate": "2091-05-04T00:00:00+02:00", "type": "RELATIONSHIP_PERIOD"}]},
        "registration": {"status": "PUBLISHED", "corroborationLevel": "FULLY_CORROBORATED",
                         "initialRegistrationDate": "2091-05-04T00:00:00Z",
                         "lastUpdateDate": "2098-01-02T10:00:00Z"}}}}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/lei-records"):
            return httpx.Response(200, json={"data": [{"id": LEI_CHILD, "attributes": {
                "entity": {"legalName": {"name": "Fiktive Tochter AG"}, "status": "ACTIVE",
                           "otherNames": [{"name": "Alte Fiktiv AG",
                                           "type": "PREVIOUS_LEGAL_NAME"}],
                           "legalAddress": {"country": "ZZ"}},
                "registration": {"status": "ISSUED"}}}]})
        if request.url.path.endswith("/direct-parent-relationship"):
            return httpx.Response(200, json=relationship)
        return httpx.Response(404, json={"errors": []})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = fetch_gleif([LEI_CHILD], [LEI_CHILD], "test-agent", client, lambda _: None)
    assert result["names"][LEI_CHILD]["legal_name"] == "Fiktive Tochter AG"
    assert result["names"][LEI_CHILD]["other_names"] == [
        {"name": "Alte Fiktiv AG", "type": "PREVIOUS_LEGAL_NAME"}]
    assert result["parents"] == [{
        "child_lei": LEI_CHILD, "kind": "direct-parent", "parent_lei": LEI_PARENT,
        "relationship_status": "ACTIVE", "registration_status": "PUBLISHED",
        "corroboration_level": "FULLY_CORROBORATED", "verified": True,
        "relationship_start": "2091-05-04", "relationship_end": None,
        "registration_initial_date": "2091-05-04", "registration_last_update": "2098-01-02"}]

    failing = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(500)))
    with pytest.raises(httpx.HTTPStatusError):
        fetch_gleif([LEI_CHILD], [], "test-agent", failing, lambda _: None)


# ------------------------------------------------------------- Global Energy Monitor
OWNERSHIP_HEADER = ["Parent GEM Entity ID", "Parent", "Project", "Share", "Ownership Path",
                    "Immediate Project Owner", "Tracker", "Status"]


def _cell(ref: str, value: str) -> str:
    from xml.sax.saxutils import escape
    return f'<c r="{ref}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'


def write_xlsx(path: Path, sheets: dict[str, list[list[str]]]) -> Path:
    """Minimale XLSX-Datei mit Inline-Texten (nur für Tests, ausschliesslich fiktive Werte)."""
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    rel_ns = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    with zipfile.ZipFile(path, "w") as archive:
        entries, rels = [], []
        for index, (name, rows) in enumerate(sheets.items(), start=1):
            safe = name.replace("&", "&amp;").replace('"', "&quot;")
            entries.append(f'<sheet name="{safe}" sheetId="{index}" r:id="rId{index}"/>')
            rels.append(f'<Relationship Id="rId{index}" Type="{rel_ns}/worksheet" '
                        f'Target="worksheets/sheet{index}.xml"/>')
            body = "".join(
                f'<row r="{r}">' + "".join(_cell(f"{chr(65 + c)}{r}", v)
                                           for c, v in enumerate(row) if v) + "</row>"
                for r, row in enumerate(rows, start=1))
            archive.writestr(f"xl/worksheets/sheet{index}.xml",
                             f'<worksheet xmlns="{ns}"><sheetData>{body}</sheetData></worksheet>')
        archive.writestr("xl/workbook.xml", f'<workbook xmlns="{ns}" xmlns:r="{rel_ns}">'
                         f'<sheets>{"".join(entries)}</sheets></workbook>')
        archive.writestr("xl/_rels/workbook.xml.rels",
                         '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
                         f'relationships">{"".join(rels)}</Relationships>')
    return path


@pytest.fixture
def gem_file(tmp_path):
    coal_rows = [
        [*OWNERSHIP_HEADER, "Capacity (MW)", "GEM unit ID"],
        ["EFIKT01", "Fiktive Mutter AG", "Fiktivwerk 1", "100", "Fiktive Mutter AG -> Werk",
         "Fiktive Mutter AG", "Global Coal Plant Tracker", "operating", "300", "GFIKT1"],
        ["EFIKT01", "Fiktive Mutter AG", "Fiktivwerk 2", "35", "Fiktive Mutter AG -> Werk",
         "Fiktive Tochter AG", "Global Coal Plant Tracker", "construction", "500", "GFIKT2"],
        ["EFIKT01", "Fiktive Mutter AG", "Fiktivwerk 2", "35", "Fiktive Mutter AG -> Werk",
         "Fiktive Tochter AG", "Global Coal Plant Tracker", "construction", "500", "GFIKT2"],
        ["EFIKT02", "Fiktive Bank AG", "Fiktivwerk 3", "1.5",
         "Fiktive Bank AG -> Fiktiver Versorger AG [5%] -> Fiktivwerk 3 [30%]",
         "Fiktiver Versorger", "Global Coal Plant Tracker", "operating", "200", "GFIKT3"],
        ["EFIKT02", "Fiktive Bank AG", "Fiktivwerk 4", "unknown",
         "Fiktive Bank AG -> Fiktiv Nominees Ltd [100%] -> Werk [100%]", "Fiktiv",
         "Global Coal Plant Tracker", "operating", "100", "GFIKT4"],
        ["EFIKT99", "Fremde Firma", "Fiktivwerk 5", "100", "Fremde Firma -> Werk", "Fremd",
         "Global Coal Plant Tracker", "operating", "100", "GFIKT5"]]
    lng_rows = [[*OWNERSHIP_HEADER, "CapacityinMtpa", "UnitID"],
                ["EFIKT02", "Fiktive Bank AG", "Fiktiv-LNG", "60",
                 "Fiktive Bank AG -> Fiktiv-LNG [60%]",
                 "Fiktiv", "Global LNG Terminals Tracker", "proposed", "4.2", "TFIKT1"]]
    gas_rows = [[*OWNERSHIP_HEADER, "Capacity (MW)", "GEM unit ID"],
                ["EFIKT01", "Fiktive Mutter AG", "Fiktiv-Notstrom", "100",
                 "Fiktive Mutter AG -> Fiktiv-Notstrom [100%]", "Fiktive Mutter AG",
                 "Global Oil and Gas Plant Tracker", "construction", "120", "GFIKTG1"]]
    sheets = {"About": [["Fiktive Testdatei"]],
              "All Entities": [["Entity ID", "Name", "Global Legal Entity Identifier Index",
                                "PubliclyListed"],
                               ["EFIKT01", "Fiktive Mutter AG", LEI_PARENT, "1"],
                               ["EFIKT02", "Fiktive Bank AG", LEI_OTHER, "1"],
                               ["EFIKT03", "Fiktiv ohne LEI", "not found", "0"],
                               ["EFIKT04", "Fiktiver Versorger AG", "not found", "1"],
                               ["EFIKT99", "Fremde Firma", LEI_HINT_CHILD, "0"]],
              "Coal Plant Ownership": coal_rows,
              "Coal Mine Ownership": [OWNERSHIP_HEADER],
              "Gas Plant Ownership": gas_rows,
              "LNG Terminal Ownership": lng_rows,
              "Gas Pipeline Ownership": [OWNERSHIP_HEADER],
              "Oil & NGL Pipeline Ownership": [OWNERSHIP_HEADER]}
    write_xlsx(tmp_path / "Global Oil and Gas Plant Tracker (GOGPT) - Fiktiv 2099.xlsx",
               {"Gas & Oil Units": [
                   ["GEM unit ID", "Plant name", "Unit name", "Fuel", "Start year",
                    "Captive industry use", "Captive industry type", "Backup Power",
                    "Country/Area", "Wiki URL"],
                   ["GFIKTG1", "Fiktiv-Rechenzentrum", "GN1 (backup)", "fossil liquids: diesel",
                    "2099", "power", "data center", "", "Fiktivland",
                    "https://example.org/fiktiv/gem-wiki"]]})
    return write_xlsx(tmp_path / "Global-Energy-Ownership-Tracker-Fiktiv-2099-V1.xlsx", sheets)


@pytest.mark.parametrize(("share", "path", "stake"), [
    (100.0, "A -> B", "control"), (50.0, None, "control"), (35.0, None, "significant"),
    (1.5, None, "small"), (None, "A -> B", "unknown"),
    (80.0, "Bank -> Custody Nominees Ltd -> Werk", "custodial")])
def test_gem_stake(share, path, stake):
    assert gem_stake(share, path) == stake


@pytest.mark.parametrize(("status", "group"), [
    ("operating", "operating"), ("Proposed", "expansion"), ("pre-permit", "expansion"),
    ("retired", "closed"), ("cancelled - inferred 4 y", "closed"), ("shelved", "closed"),
    (None, "unknown"), ("–", "unknown")])
def test_gem_status(status, group):
    assert gem_status(status) == group


def test_load_gem_links_only_via_gem_lei_column(gem_file):
    gem = load_gem(gem_file, {LEI_PARENT, LEI_OTHER}, gem_file.parent)
    assert gem["entities"] == {LEI_PARENT: ["EFIKT01"], LEI_OTHER: ["EFIKT02"]}
    mother = gem["assets"][LEI_PARENT]
    assert [(a["project"], a["stake"], a["status_group"]) for a in mother] == [
        ("Fiktivwerk 1", "control", "operating"), ("Fiktivwerk 2", "significant", "expansion"),
        ("Fiktiv-Notstrom", "control", "expansion")]
    backup = mother[2]["details"]
    assert backup["backup"] and backup["fuel"] == "fossil liquids: diesel"
    bank = {a["project"]: a for a in gem["assets"][LEI_OTHER]}
    assert bank["Fiktivwerk 3"]["stake"] == "small"
    assert bank["Fiktivwerk 3"]["hops"][0] == {"holder": "Fiktive Bank AG",
                                               "name": "Fiktiver Versorger AG", "share": 5.0}
    assert gem["listed"]["Fiktiver Versorger AG"] is True
    # Beziehungstyp erst bei der Auswertung: Verwahrung über die Nominee-Gesellschaft.
    classified = {a["project"]: a for a in classify_gem_assets(
        gem["assets"][LEI_OTHER], True, gem["listed"])}
    assert classified["Fiktivwerk 4"]["relationship"] == "custody"
    assert classified["Fiktivwerk 3"]["relationship"] == "financial_stake_unclear"
    assert classified["Fiktivwerk 3"]["old_stake"] == "small"  # Regel bis Profil 1.0
    assert classified["Fiktiv-LNG"]["relationship"] == "own_account"
    assert (bank["Fiktiv-LNG"]["capacity_label"], bank["Fiktiv-LNG"]["unit_id"]) == (
        "CapacityinMtpa", "TFIKT1")
    assert LEI_HINT_CHILD not in gem["assets"]  # nicht im Fonds: nicht geladen


def test_load_gem_rejects_missing_sheets(tmp_path):
    path = write_xlsx(tmp_path / "Global-Energy-Ownership-Tracker-Kaputt.xlsx",
                      {"All Entities": [["Entity ID"]]})
    with pytest.raises(ValueError, match="Blätter fehlen"):
        load_gem(path, set())


def test_chain_reports_coal_by_relationship_type(gem_file):
    fund = parse_fund(fund_xml(positions=(
        ("Fiktive Mutter AG", ISIN_A, "40"), ("Fiktive Bank AG", ISIN_B, "30"),
        ("Fiktive Ohne GEM AG", ISIN_C, "20"), ("Fiktive Ungeklärt AG", ISIN_D, "10"))))
    candidates = index_candidates([
        candidate(ISIN_A, "Q1", LEI_PARENT), candidate(ISIN_B, "Q2", LEI_OTHER),
        candidate(ISIN_C, "Q3", LEI_CHILD), candidate(ISIN_D, "Q4", LEI_HINT_CHILD)])
    gleif = {"names": {LEI_PARENT: gleif_entry("Fiktive Mutter AG"),
                       LEI_OTHER: gleif_entry("Fiktive Bank AG"),
                       LEI_CHILD: gleif_entry("Fiktive Ohne GEM AG"),
                       LEI_HINT_CHILD: gleif_entry("Ganz Anderer Name AG")},
             "names_checked": [LEI_PARENT, LEI_OTHER, LEI_CHILD, LEI_HINT_CHILD], "parents": []}
    gem = load_gem(gem_file, {LEI_PARENT, LEI_OTHER, LEI_CHILD, LEI_HINT_CHILD},
                         gem_file.parent)
    profiles = {"Q2": {"industries": ["bank"], "register": {}},
                "Q1": {"industries": ["energy company"], "register": {}}}
    report = build_chain(fund, candidates, {}, gleif, None, None, gem, profiles=profiles)
    mother, bank, without, unclear = report["positions"]
    coal = mother["coal"]
    assert (coal["has_active_coal"], coal["strongest"], coal["conflict"]) == (
        True, "control", True)
    assert coal["by_stake"] == {"control": {"operating": 1, "expansion": 0},
                                "significant": {"operating": 0, "expansion": 1}}
    assert coal["max_own_share"] == 100.0 and coal["relationships"] == ["own_account"]
    assert coal["categories"] == {"kohleverstromung": 2}
    # Bank: 5 % an einem kotierten Versorger = Finanzbeteiligung, Nominee = Verwahrung.
    # Nach der Regel bis Profil 1.0 war das ein Konflikt, jetzt nicht mehr.
    assert bank["company"]["financial_institution"] is True
    assert bank["coal"]["strongest"] == "financial_stake_unclear"
    assert bank["coal"]["conflict"] is False and bank["coal"]["old_conflict"] is True
    assert "keine belegte Eigentumsbeteiligung" in explain_finding(
        bank["coal"], "has_active_coal", 0.0)
    # Eigene Projektbeteiligung der Bank (LNG, 60 %) bleibt Eigentum auf eigene Rechnung.
    assert bank["expansion"]["conflict"] is True
    assert (bank["expansion"]["phases"], bank["expansion"]["capacity_types"]) == (
        {"ankuendigung": 1}, {"lng": 1})
    # Fossile Expansion: Phase und Art der neuen Kapazität bleiben getrennt.
    exp = mother["expansion"]
    assert (exp["strongest"], exp["phases"], exp["capacity_types"], exp["conflict"]) == (
        "control", {"bau": 2}, {"kraftwerke": 2}, True)
    assert exp["own_captive_or_backup"] == 1  # Notstromaggregat des Rechenzentrums
    assert without["expansion"] == {"has_expansion": False} and unclear["expansion"] is None
    assert without["coal"] == {"has_active_coal": False} and without["gem"] is None
    # Name passt nicht zu GLEIF: Prüffall, deshalb keine GEM-Aussage (auch kein «keine Hinweise»).
    assert unclear["mapping_confidence"] == "name_mismatch" and unclear["coal"] is None
    s = report["summary"]
    assert s["coal_active"]["positions"] == 2 and s["coal_strongest_control"]["positions"] == 1
    assert s["coal_no_hint"]["positions"] == 1 and s["coal_checked"]["positions"] == 3
    assert s["coal_conflict"]["positions"] == 1 and s["coal_old_conflict"]["positions"] == 2
    assert s["expansion_any"] == {"positions": 2, "weight_percent": 70.0}
    assert s["expansion_conflict"]["positions"] == 2 and s["expansion_checked"]["positions"] == 3
    assert s["expansion_phase_bau"]["positions"] == 1 and s["expansion_type_lng"]["positions"] == 1
    crit = criteria_status([
        {"key": "kohle", "name": "Kohle", "rule": "Fiktive Regel", "decision": "decided"},
        {"key": "fossile_expansion", "name": "Fossile Expansion"},
        {"key": "waffen", "name": "Waffen", "source_gap": "Fiktive Lücke",
         "decision": "proposed"}], report)
    assert (crit[0]["status"], crit[0]["evidence_count"]) == ("teilweise belegt", 2)
    assert crit[0]["conflict"] == {"positions": 1, "weight_percent": 40.0}
    assert (crit[1]["status"], crit[1]["evidence_count"]) == ("teilweise belegt", 2)
    assert "nur mit Namen" in crit[1]["reason"]
    # Ohne Quelle: unbekannt, kein Konfliktwert (auch nicht 0), Lücke wird genannt.
    assert (crit[2]["status"], crit[2]["conflict"], crit[2]["reason"]) == (
        "unbekannt", None, "Fiktive Lücke")
    assert crit[0]["rule_decided"] and not crit[2]["rule_decided"]
    html = render_html(report, [{"key": "kohle", "name": "Kohle", "description": "x",
                                       "rule": "Fiktive Regel"}])
    assert "Fiktive Regel" in html and "unsere Bewertungsentscheidung" in html
    assert "Fossile Anlagen und Beteiligungen" in html
    assert "Kohle und fossile Expansion laut GEM" in html
    assert "Verwahrung für Dritte" in html and "keine Hinweise in GEM" in html
    assert "Belegt laut GEM (Teilabdeckung)" in html and "nicht geprüft" in html
    report["attribution"].pop("gem")
    assert "nicht von Global Energy Monitor geprüft" not in render_html(report, [])
    report["attribution"]["gem"] = ("Global Energy Monitor, Fiktiv (CC BY 4.0)", "https://x")
    assert "nicht von Global Energy Monitor geprüft" in render_html(report, [])


def test_expansion_counts_captive_units_and_threshold(gem_file):
    gem = load_gem(gem_file, {LEI_PARENT}, gem_file.parent)
    assets = classify_gem_assets(gem["assets"][LEI_PARENT], False, gem["listed"])
    strict = expansion_finding(assets)
    assert strict["conflict"] and strict["own_captive_or_backup"] == 1
    assert strict["own_units_total"] == 2
    # Schwelle 50 %: der Notstrom (100 %) zählt noch, die 35-%-Beteiligung allein nicht.
    assert expansion_finding(assets, 50.0)["conflict"] is True
    without_backup = [a for a in assets if a["project"] != "Fiktiv-Notstrom"]
    assert expansion_finding(without_backup, 50.0)["conflict"] is False
    assert expansion_finding(without_backup, 20.0)["conflict"] is True
    # Kategorie mit Wirkung «separate» löst nie einen Konflikt aus.
    assert expansion_finding(assets, 0.0, {"kraftwerke": "separate"})["conflict"] is False
    rows = [{"weight_percent": 10.0, "expansion": expansion_finding(without_backup)}]
    assert [t["positions"] for t in sensitivity(rows, "expansion")] == [1, 1, 1, 1, 0]


def test_automatic_mapping_paths_and_release():
    fund = parse_fund(fund_xml(positions=(
        ("Fiktiv Register AG", ISIN_A, "40"), ("Fiktiv Name AG", ISIN_B, "30"),
        ("Fiktiv Zwei AG", ISIN_C, "20"), ("Fiktiv Umbenannt AG", ISIN_D, "10"))))
    candidates = index_candidates([
        candidate(ISIN_A, "Q1"), candidate(ISIN_C, "Q3", LEI_PARENT, LEI_OTHER),
        candidate(ISIN_D, "Q4", LEI_HINT_CHILD)])
    gleif = {"names": {LEI_PARENT: gleif_entry("Fiktiv Zwei AG"),
                       LEI_OTHER: gleif_entry("Fiktiv Zwei Holding Schweiz"),
                       LEI_HINT_CHILD: gleif_entry("Ganz Neuer Name AG")},
             "names_checked": [LEI_PARENT, LEI_OTHER, LEI_HINT_CHILD], "parents": []}

    def accepted(method, lei):
        return {"method": method, "lei": lei, "status": "accepted", "reason": "fiktiv",
                "candidates": [lei]}

    auto = {ISIN_A: {"register": accepted("register", LEI_CHILD), "name": None,
                     "entities": {LEI_CHILD: {"lei": LEI_CHILD, "legal_name": "Fiktiv Register",
                                              "registration_status": "ISSUED"}}},
            ISIN_B: {"name": accepted("gleif_name_country", LEI_CHILD), "register": None,
                     "entities": {}},
            ISIN_C: {"name": accepted("gleif_name_country", LEI_PARENT), "register": None,
                     "entities": {}},
            ISIN_D: {"name": accepted("gleif_name_country", LEI_HINT_CHILD), "register": None,
                     "entities": {}}}
    held = build_chain(fund, candidates, {}, gleif, auto=auto, name_released=False)
    by_isin = {r["isin"]: r for r in held["positions"]}
    # Registernummer ist eine Kennung: wirkt immer.
    assert by_isin[ISIN_A]["mapping_confidence"] == "confirmed_by_register"
    # Namenssuche ohne Freigabe: nur Vorschlag, als Frage in der Liste, nicht zugeordnet.
    assert by_isin[ISIN_B]["mapping_confidence"] == "name_proposal"
    assert by_isin[ISIN_C]["mapping_confidence"] == "ambiguous"
    assert by_isin[ISIN_D]["mapping_confidence"] == "name_mismatch"
    assert [c["signal"] for c in review_queue(held["positions"])].count(
        "name_proposal") == 1
    released = build_chain(fund, candidates, {}, gleif, auto=auto, name_released=True)
    by_isin = {r["isin"]: r for r in released["positions"]}
    assert by_isin[ISIN_B]["mapping_confidence"] == "auto_by_name"
    # Zwei unabhängige Wege zeigen auf denselben LEI: löst Mehrdeutigkeit und Namensabweichung.
    assert by_isin[ISIN_C]["mapping_confidence"] == "confirmed_by_agreement"
    assert by_isin[ISIN_C]["company"]["leis"] == [LEI_PARENT]
    assert by_isin[ISIN_D]["mapping_confidence"] == "confirmed_by_agreement"
    # Ein menschliches «Nein» schlägt jedes automatische Verfahren.
    vetoed = build_chain(fund, candidates, {}, gleif, auto=auto, name_released=True,
                               decisions={ISIN_B: {LEI_CHILD: "no"}})
    assert {r["isin"]: r for r in vetoed["positions"]}[ISIN_B]["mapping_confidence"] == "unknown"
    # Referenzfälle: nur über einen unabhängigen Weg gesicherte Zuordnungen, nie die Namenssuche.
    refs = reference_cases(released["positions"], "Fiktivfonds")
    assert set(refs) == set() or all(r["reference_source"] in ("isin_wikidata", "decision")
                                     for r in refs.values())


def test_reference_cases_feed_the_evaluation():
    rows = [{"isin": ISIN_A, "name": "A", "mapping_confidence": "consistent",
             "company": {"lei": LEI_PARENT},
             "auto_match": {"name": {"status": "accepted", "lei": LEI_PARENT},
                            "register": {"status": "not_searched", "lei": None}}},
            {"isin": ISIN_B, "name": "B", "mapping_confidence": "auto_by_name",
             "company": {"lei": LEI_OTHER}, "auto_match": {}}]
    store = reference_cases(rows, "Fiktivfonds")
    # automatisch über den Namen zugeordnet: keine Referenz
    assert list(store) == [f"Fiktivfonds|{ISIN_A}"]
    evaluation = evaluate_methods(store)
    assert (evaluation["name"]["answered"], evaluation["name"]["correct"]) == (1, 1)
    assert evaluation["register"]["reference_cases"] == 0  # nicht gesucht: nicht gezählt
    assert evaluation["name"]["released"] is False  # zu wenige Fälle


def test_every_named_criterion_test_exists():
    root = Path(__file__).parents[1]
    names = {*(t for tests in CRITERION_TESTS.values() for t in tests),
             GENERIC_CRITERION_TEST}
    for name in names:
        path, _, function = name.partition("::")
        assert f"def {function}(" in (root / path).read_text(encoding="utf-8"), name


def test_criteria_readiness_separates_the_five_stages():
    readiness = criteria_readiness([
        {"key": "kohle", "name": "Kohle", "decision": "decided", "data_status_label": "Quelle "
         "integriert", "categories": [{"key": "a", "effect": "conflict"},
                                      {"key": "b", "effect": "separate"}]},
        {"key": "waffen", "name": "Waffen", "decision": "proposed",
         "data_status_label": "Quelle vorhanden, Nutzungsrechte ungeklärt"}], None)
    coal, weapons = readiness
    assert coal["defined"] == "ja" and "Kategorien entscheiden" in coal["implemented"]
    assert coal["fund"].startswith("nein")  # ohne GEM-Lauf nicht am Fonds geprüft
    assert weapons["defined"].startswith("ja (Vorschlag")
    assert weapons["data"] == "Quelle vorhanden, Nutzungsrechte ungeklärt"
    assert "test_weapons_category_decides_conflict" in weapons["tests"]


def test_report_renders_chains_measurement_and_readiness(gem_file):
    fund = parse_fund(fund_xml(positions=(("Fiktive Bank AG", ISIN_B, "60"),
                                                ("Fiktive Mutter AG", ISIN_A, "40"))))
    candidates = index_candidates([candidate(ISIN_A, "Q1", LEI_PARENT),
                                         candidate(ISIN_B, "Q2", LEI_OTHER)])
    gleif = {"names": {LEI_PARENT: gleif_entry("Fiktive Mutter AG"),
                       LEI_OTHER: gleif_entry("Fiktive Bank AG")},
             "names_checked": [LEI_PARENT, LEI_OTHER], "parents": []}
    gem = load_gem(gem_file, {LEI_PARENT, LEI_OTHER}, gem_file.parent)
    report = build_chain(fund, candidates, {}, gleif, None, None, gem, profiles={
        "Q2": {"industries": ["bank"], "register": {}}})
    report["cases"] = [ISIN_B, ISIN_A]
    report["mapping_evaluation"] = evaluate_methods(
        reference_cases(report["positions"], "Fiktivfonds"))
    report["relationship_rules"] = [{"key": "custody", "name": "Verwahrung von Wertpapieren",
                                     "description": "fiktiv", "effect": "separate",
                                     "decision": "decided", "reason": "Keine Beteiligung.",
                                     "data_status_label": "Quelle integriert",
                                     "data_note": "fiktiv"}]
    html = render_html(report, [{"key": "kohle", "name": "Kohle", "rule": "Regel",
                                       "decision": "decided", "data_status_label": "integriert",
                                       "categories": [{"key": "k", "effect": "separate"}]}])
    for text in ("Vollständige Belegketten", "Fiktiver Versorger AG", "Verwahrung für Dritte",
                 "Finanzbeteiligung, Rechnung ungeklärt", "Notstrom", "GEM-Wiki",
                 "Wie zuverlässig sind die automatischen Verfahren?", "Umsetzungsstand",
                 "Alle betroffenen Treffer", "Wirkung einer Beteiligungsschwelle",
                 "Verwahrung von Wertpapieren"):
        assert text in html, text
    markdown = render_markdown(report)
    assert "Präzision und Abdeckung getrennt" in markdown and "Beziehungstyp" in markdown


def test_independent_measurement_excludes_development_isins_and_counts_each_isin_once():
    dev = sorted(DEVELOPMENT_FUNDS)[0]

    def case(fund, isin, predicted):
        return {"isin": isin, "position_name": "x", "fund": fund, "reference_lei": LEI_PARENT,
                "reference_source": "isin_wikidata",
                "name": {"status": "accepted", "lei": predicted}, "register": None}

    store = {"a": case(dev, ISIN_A, LEI_PARENT), "b": case("Testfonds 1", ISIN_A, LEI_OTHER),
             "c": case("Testfonds 1", ISIN_B, LEI_PARENT),
             "d": case("Testfonds 2", ISIN_B, LEI_PARENT),
             "e": case("Testfonds 2", ISIN_C, LEI_PARENT)}
    name = evaluate_methods(store)["name"]
    # ISIN_A kommt im Entwicklungsfonds vor (zählt nicht), ISIN_B nur einmal.
    assert (name["answered"], name["correct"], name["wrong"]) == (2, 2, 0)
    assert name["development"]["answered"] == 1


def test_disagreements_become_questions_with_both_candidates():
    evaluation = {"name": {"wrong_cases": [
        {"isin": ISIN_A, "position_name": "Fiktiv ASA", "fund": "Testfonds",
         "reference_lei": LEI_CHILD, "predicted_lei": LEI_PARENT}],
        "development": {"wrong_cases": []}},
        "register": {"wrong_cases": [], "development": {"wrong_cases": [
            {"isin": ISIN_A, "position_name": "Fiktiv ASA", "fund": "Testfonds",
             "reference_lei": LEI_CHILD, "predicted_lei": LEI_OTHER}]}}}
    entities = {LEI_PARENT: {"legal_name": "FIKTIV ASA", "registration_status": "ISSUED"},
                LEI_CHILD: {"legal_name": "FIKTIV AS", "other_names": [{"name": "Alt"}]}}
    cases = dispute_queue(evaluation, entities)
    assert len(cases) == 1 and cases[0]["signal"] == "reference_dispute"
    assert [c["lei"] for c in cases[0]["candidates"]] == [LEI_CHILD, LEI_PARENT, LEI_OTHER]
    assert cases[0]["candidates"][0]["other_names"] == ["Alt"]
    assert cases[0]["candidates"][2]["legal_name"] is None  # nicht geladen: ehrlich leer


def test_nport_reference_replaces_wikidata_and_decision_goes_first():
    rows = [{"isin": ISIN_A, "name": "A", "issuer_country": "SE",
             "mapping_confidence": "consistent", "company": {"lei": LEI_OTHER},
             "auto_match": {"name": {"status": "accepted", "lei": LEI_PARENT}}},
            {"isin": ISIN_B, "name": "B", "issuer_country": "US",
             "mapping_confidence": "confirmed_by_decision", "company": {"lei": LEI_CHILD},
             "auto_match": {}},
            {"isin": ISIN_C, "name": "C", "issuer_country": None,
             "mapping_confidence": "consistent", "company": {"lei": LEI_PARENT},
             "auto_match": {}}]
    store = reference_cases(rows, "Fiktivfonds", {ISIN_A: LEI_PARENT, ISIN_B: LEI_OTHER})
    by_isin = {c["isin"]: c for c in store.values()}
    # Wikidata nennt LEI_OTHER, N-PORT LEI_PARENT: Referenz ist N-PORT.
    assert by_isin[ISIN_A]["reference_source"] == "nport_consensus"
    assert by_isin[ISIN_A]["reference_lei"] == LEI_PARENT
    assert by_isin[ISIN_A]["region"] == "europe"
    # Ein menschlicher Entscheid geht dem N-PORT-Konsens vor.
    assert by_isin[ISIN_B]["reference_source"] == "decision"
    assert by_isin[ISIN_B]["reference_lei"] == LEI_CHILD
    # Ohne N-PORT-Eintrag keine Referenz, auch wenn Wikidata widerspruchsfrei ist.
    assert ISIN_C not in by_isin
    # Ohne Wertpapierstamm: frühere Referenz (Wikidata-Kennung).
    assert reference_cases(rows, "Fiktivfonds")[f"Fiktivfonds|{ISIN_C}"][
        "reference_source"] == "isin_wikidata"


def test_name_search_is_released_per_region():
    def case(i, region, correct=True):
        isin = make_isin(f"ZZREG{i:06d}")
        return isin, {"isin": isin, "position_name": "x", "fund": "Testfonds",
                      "reference_lei": LEI_PARENT, "reference_source": "nport_consensus",
                      "region": region, "register": None,
                      "name": {"status": "accepted",
                               "lei": LEI_PARENT if correct else LEI_OTHER}}

    store = dict(case(i, "europe") for i in range(120))
    store.update(case(i, "north_america") for i in range(200, 250))
    store.update(case(i, "asia_pacific", correct=i % 20 != 0) for i in range(300, 420))
    name = evaluate_methods(store)["name"]
    # Europa: 120/120 → frei. Nordamerika: zu wenige Fälle. Asien-Pazifik: 5 % falsch.
    assert name["released_regions"] == ["europe"]
    assert name["regions"]["north_america"]["released"] is False
    assert name["regions"]["asia_pacific"]["wrong"] == 6
    assert "wrong_cases" not in name["regions"]["europe"]


def test_released_region_decides_per_position():
    fund = parse_fund(fund_xml(positions=(("Fiktiv Name AG", ISIN_B, "60"),
                                          ("Fiktiv Anders AG", ISIN_C, "40"))))
    accepted = {"method": "gleif_name_country", "lei": LEI_CHILD, "status": "accepted",
                "reason": "fiktiv", "candidates": [LEI_CHILD]}
    auto = {isin: {"name": accepted, "register": None, "entities": {}}
            for isin in (ISIN_B, ISIN_C)}
    region = position_region(fund.positions[0].issuer_country, ISIN_B)
    report = build_chain(fund, {}, {}, None, auto=auto, name_released=frozenset({region}))
    assert {r["mapping_confidence"] for r in report["positions"]} == {"auto_by_name"}
    none = build_chain(fund, {}, {}, None, auto=auto, name_released=frozenset({"nirgends"}))
    assert {r["mapping_confidence"] for r in none["positions"]} == {"name_proposal"}
    assert none["positions"][0]["auto_match"]["name_released"] is False


def test_name_never_acts_against_confirmed_reference():
    fund = parse_fund(fund_xml(positions=(("Fiktiv Name AG", ISIN_B, "60"),
                                          ("Fiktiv Anders AG", ISIN_C, "40"))))
    accepted = {"method": "gleif_name_country", "lei": LEI_CHILD, "status": "accepted",
                "reason": "fiktiv", "candidates": [LEI_CHILD]}
    auto = {isin: {"name": accepted, "register": None, "entities": {}}
            for isin in (ISIN_B, ISIN_C)}
    # N-PORT bestätigt für ISIN_B einen anderen LEI, für ISIN_C denselben. Ein Mensch hat den
    # N-PORT-LEI von ISIN_B verworfen: Der Kennungsweg fällt weg, der Name wirkt trotzdem nicht.
    report = build_chain(fund, {}, {}, None, auto=auto, name_released=True,
                         decisions={ISIN_B: {LEI_OTHER: "no"}},
                         reference={ISIN_B: LEI_OTHER, ISIN_C: LEI_CHILD})
    by_isin = {r["isin"]: r for r in report["positions"]}
    assert by_isin[ISIN_B]["mapping_confidence"] == "name_proposal"
    assert by_isin[ISIN_B]["auto_match"]["name_contradicts_reference"] is True
    # Kennungsweg geht der Namenssuche vor, auch wenn beide denselben LEI nennen.
    assert by_isin[ISIN_C]["mapping_confidence"] == "confirmed_by_nport"
    assert "name_contradicts_reference" not in by_isin[ISIN_C]["auto_match"]


def nport_fund():
    return parse_fund(fund_xml(positions=(
        ("Fiktiv Gleich AG", ISIN_A, "40"), ("Fiktiv Tochter AG", ISIN_B, "30"),
        ("Fiktiv Ohne AG", ISIN_C, "20"), ("Fiktiv Entscheid AG", ISIN_D, "10"))))


def test_nport_consensus_maps_before_wikidata_and_shows_disagreement():
    fund = nport_fund()
    candidates = index_candidates([candidate(ISIN_A, "Q1", LEI_PARENT),
                                   candidate(ISIN_B, "Q2", LEI_CHILD),
                                   candidate(ISIN_D, "Q4", LEI_OTHER)])
    gleif = {"names": {LEI_PARENT: gleif_entry("Fiktiv Gleich AG"),
                       LEI_CHILD: gleif_entry("Fiktiv Tochter AG"),
                       LEI_OTHER: gleif_entry("Fiktiv Entscheid AG")},
             "names_checked": [LEI_PARENT, LEI_CHILD, LEI_OTHER], "parents": []}
    reference = {ISIN_A: LEI_PARENT, ISIN_B: LEI_PARENT, ISIN_C: LEI_HINT_CHILD,
                 ISIN_D: LEI_PARENT}
    details = {ISIN_B: {"independent": 4, "funds": 9, "gleif_entity_status": "ACTIVE"}}
    emissions = index_emissions([emission(LEI_PARENT)])
    report = build_chain(fund, candidates, emissions, gleif, decisions={
        ISIN_D: {LEI_OTHER: "yes"}}, reference=reference, reference_details=details)
    by_isin = {r["isin"]: r for r in report["positions"]}
    a, b, c, d = (by_isin[i] for i in (ISIN_A, ISIN_B, ISIN_C, ISIN_D))
    assert a["mapping_confidence"] == "confirmed_by_nport"
    assert a["company"]["wikidata_check"] == "same"
    assert a["company"]["name_check"] == "shared_word"
    # Wikidata nennt die Tochter: Der Konsens gilt, die Abweichung bleibt sichtbar.
    assert b["mapping_confidence"] == "confirmed_by_nport"
    assert b["company"]["lei"] == LEI_PARENT and b["company"]["leis"] == [LEI_PARENT]
    assert b["company"]["wikidata_leis"] == [LEI_CHILD]
    assert b["company"]["wikidata_check"] == "different"
    assert b["mapping_signal"] == "wikidata_differs"
    assert b["company"]["nport"] == details[ISIN_B]
    assert [e["status"] for e in b["evidence"]] == ["confirmed"]
    # Ohne Wikidata-Eintrag: Kennungsweg trotzdem; GLEIF-Name nicht geladen = ehrlich leer.
    assert c["mapping_confidence"] == "confirmed_by_nport"
    assert c["company"]["wikidata_check"] == "no_entry"
    assert c["company"]["gleif"] == {} and c["company"]["name_check"] == "not_checked"
    # Ein menschlicher Entscheid geht dem Konsens vor.
    assert d["mapping_confidence"] == "confirmed_by_decision"
    assert d["company"]["lei"] == LEI_OTHER
    s = report["summary"]
    assert s["confirmed_coverage"]["positions"] == 4
    assert {k: v["positions"] for k, v in s["nport_by_wikidata_check"].items()} == {
        "different": 1, "no_entry": 1, "same": 1}
    # Ohne Wertpapierstamm unverändert über Wikidata.
    plain = {r["isin"]: r for r in build_chain(fund, candidates, emissions, gleif)["positions"]}
    assert plain[ISIN_B]["mapping_confidence"] == "consistent"
    assert plain[ISIN_B]["company"]["lei"] == LEI_CHILD


def test_measurement_does_not_depend_on_the_nport_assignment():
    """Die Referenz misst die Namensvorschläge jeder Position, egal welcher Weg zuordnet."""
    fund = nport_fund()
    candidates = index_candidates([candidate(ISIN_A, "Q1", LEI_PARENT),
                                   candidate(ISIN_B, "Q2", LEI_CHILD)])
    accepted = {"method": "gleif_name_country", "lei": LEI_PARENT, "status": "accepted",
                "reason": "fiktiv", "candidates": [LEI_PARENT]}
    auto = {isin: {"name": accepted, "register": None, "entities": {}}
            for isin in (ISIN_A, ISIN_B, ISIN_C, ISIN_D)}
    reference = {ISIN_A: LEI_PARENT, ISIN_B: LEI_PARENT, ISIN_C: LEI_OTHER}
    mapped = build_chain(fund, candidates, {}, None, auto=auto, reference=reference)
    unmapped = build_chain(fund, candidates, {}, None, auto=auto)
    assert {r["mapping_confidence"] for r in mapped["positions"][:3]} == {"confirmed_by_nport"}
    store = reference_cases(mapped["positions"], "Testfonds", reference)
    assert store == reference_cases(unmapped["positions"], "Testfonds", reference)
    name = evaluate_methods(store)["name"]
    assert (name["answered"], name["correct"], name["wrong"]) == (3, 2, 1)


def test_report_shows_nport_path_and_wikidata_disagreement():
    fund = nport_fund()
    candidates = index_candidates([candidate(ISIN_B, "Q2", LEI_CHILD)])
    reference = {ISIN_B: LEI_PARENT}
    report = build_chain(fund, candidates, {}, None, reference=reference,
                         reference_details={ISIN_B: {"independent": 3}})
    report["mapping_evaluation"] = {
        **evaluate_methods(reference_cases(report["positions"], "Testfonds", reference)),
        "reference": {"kind": "nport_consensus", "rule_version": "fiktiv",
                      "built_at": "2099-01-01"}}
    html = render_html(report, [])
    for text in ("Fondsmeldungen an die SEC und Wikidata im Vergleich",
                 "Wikidata nennt einen anderen LEI", "N-PORT-Konsens, Wertpapierstamm "
                 "Regelversion fiktiv", "Kennung: Fondsmeldungen an die SEC", LEI_CHILD):
        assert text in html, text
    markdown = render_markdown(report)
    assert "## N-PORT-Konsens und Wikidata-Kennung" in markdown
    assert f"{LEI_PARENT} (nicht geladen) ← {LEI_CHILD}" in markdown
