"""Entscheid-Speicher für Zuordnungen: ausschliesslich fiktive Kennungen und Namen."""
import importlib.util
import sys
from datetime import date
from pathlib import Path

import pytest

from transparenz.entities.identifiers import make_isin, make_lei
from transparenz.ingestion.fi_holdings import parse_fund
from transparenz.reports.fund_chain_report import render_html
from transparenz.services.fund_chain import (
    build_chain,
    index_candidates,
    index_emissions,
    review_queue,
)
from transparenz.services.review_decisions import (
    MappingDecision,
    append_decision,
    decision_stats,
    index_decisions,
    load_decisions,
)

ISIN_A = make_isin("ZZ000000001")
ISIN_B = make_isin("ZZ000000002")
ISIN_C = make_isin("ZZ000000003")
LEI_ONE = make_lei("FIKT00000000000001")
LEI_TWO = make_lei("FIKT00000000000004")
DAY = date(2099, 1, 2)
NS = "http://schemas.fi.se/publika/vardepappersfonder/20200331"


def load_script(name: str):
    path = Path(__file__).parents[1] / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def reviewer():
    return load_script("review_mapping")


def decision(isin: str, lei: str, answer: str, signal: str = "name_mismatch") -> MappingDecision:
    return MappingDecision(isin=isin, lei=lei, decision=answer, decided_on=DAY, signal=signal)


def fund(*positions: tuple[str, str, str]):
    items = "".join(
        f"<FinansielltInstrument><Instrumentnamn>{title}</Instrumentnamn>"
        f"<ISIN-kod_instrument>{isin}</ISIN-kod_instrument><Landkod_Emittent>ZZ</Landkod_Emittent>"
        f"<Valuta>CHF</Valuta><Marknadsvärde_instrument>100</Marknadsvärde_instrument>"
        f"<Andel_av_fondförmögenhet_instrument>{weight}</Andel_av_fondförmögenhet_instrument>"
        "</FinansielltInstrument>" for title, isin, weight in positions)
    return parse_fund((
        f'<?xml version="1.0" encoding="utf-8"?><VärdepappersfondInnehav xmlns="{NS}">'
        "<Rapportinformation><Kvartalsslut>2099-06-30</Kvartalsslut></Rapportinformation>"
        "<Bolagsinformation><Fondbolag_namn>Fiktive Fondsleitung</Fondbolag_namn>"
        "</Bolagsinformation><Fondinformation><Fond_namn>Fiktiver Testfonds</Fond_namn>"
        f"<Fondförmögenhet>400</Fondförmögenhet><FinansiellaInstrument>{items}"
        "</FinansiellaInstrument></Fondinformation></VärdepappersfondInnehav>").encode())


def candidate(isin: str, item: str, *leis: str) -> dict:
    return {"isin": isin, "wikidata_id": item, "name": f"Fiktiv {item}",
            "claims": {"P1278": list(leis)}}


def gleif(**names: str) -> dict:
    return {"names": {lei: {"legal_name": name, "registration_status": "ISSUED"}
                      for lei, name in names.items()},
            "names_checked": list(names), "parents": []}


def emission(lei: str) -> dict:
    return {"company_key": f"lei:{lei}", "mapping_status": "exact_uid_match", "year": 2099,
            "uid_facility": "CHE000000000", "data_as_of": "2099-12-31",
            "pollutant_name": "Fiktiver Stoff", "medium": "Luft", "value": 1.5, "unit": "kg/a"}


# ------------------------------------------------------------------ Speicher
def test_decisions_roundtrip_and_latest_wins(tmp_path):
    path = tmp_path / "review" / "decisions.csv"
    assert load_decisions(path) == []
    append_decision(path, decision(ISIN_A, LEI_ONE, "no"))
    append_decision(path, decision(ISIN_A, LEI_ONE, "yes"))
    append_decision(path, decision(ISIN_B, LEI_TWO, "no", "ambiguous"))
    loaded = load_decisions(path)
    assert len(loaded) == 3 and loaded[0].decided_on == DAY
    assert index_decisions(loaded) == {ISIN_A: {LEI_ONE: "yes"}, ISIN_B: {LEI_TWO: "no"}}
    # Die Statistik zählt je Paar nur den geltenden Entscheid.
    assert decision_stats(loaded) == {"ambiguous": {"yes": 0, "no": 1},
                                      "name_mismatch": {"yes": 1, "no": 0}}


def test_two_approved_leis_for_one_isin_are_refused(tmp_path):
    path = tmp_path / "decisions.csv"
    append_decision(path, decision(ISIN_A, LEI_ONE, "yes"))
    with pytest.raises(ValueError, match="Widerspruch"):
        append_decision(path, decision(ISIN_A, LEI_TWO, "yes"))
    assert len(load_decisions(path)) == 1  # der widersprüchliche Entscheid wurde nicht gespeichert


@pytest.mark.parametrize("field, value", [("isin", "ZZ0000000000"), ("lei", "FIKT0000000000000199"),
                                          ("decision", "vielleicht")])
def test_invalid_rows_are_rejected_with_line_number(tmp_path, field, value):
    row = {"isin": ISIN_A, "lei": LEI_ONE, "decision": "yes", "decided_on": "2099-01-02",
           field: value}
    path = tmp_path / "decisions.csv"
    path.write_text("isin,lei,decision,decided_on\n" + ",".join(row.values()) + "\n", "utf-8")
    with pytest.raises(ValueError, match="Zeile 2"):
        load_decisions(path)


def test_missing_columns_are_rejected(tmp_path):
    path = tmp_path / "decisions.csv"
    path.write_text("isin,lei\n", "utf-8")
    with pytest.raises(ValueError, match="Spalten fehlen"):
        load_decisions(path)


# ------------------------------------------------------------------ Wirkung im Pilot
def test_yes_confirms_name_mismatch_and_releases_evidence():
    holdings = fund(("Ganz Anderer Name", ISIN_A, "60"))
    candidates = index_candidates([candidate(ISIN_A, "Q1", LEI_ONE)])
    emissions = index_emissions([emission(LEI_ONE)])
    names = gleif(**{LEI_ONE: "Fiktive Mutter AG"})

    before = build_chain(holdings, candidates, emissions, names)
    row = before["positions"][0]
    assert row["mapping_confidence"] == "name_mismatch"
    assert row["evidence"][0]["status"] == "position_mapping_unconfirmed"
    queue = review_queue(before["positions"])
    assert [(c["isin"], c["signal"], c["candidates"][0]["legal_name"]) for c in queue] == [
        (ISIN_A, "name_mismatch", "Fiktive Mutter AG")]

    after = build_chain(holdings, candidates, emissions, names,
                              decisions={ISIN_A: {LEI_ONE: "yes"}})
    row = after["positions"][0]
    assert row["mapping_confidence"] == "confirmed_by_decision"
    assert row["mapping_signal"] == "name_mismatch"
    assert row["evidence"][0]["status"] == "confirmed"
    assert after["summary"]["confirmed_coverage"]["positions"] == 1
    assert after["summary"]["with_unique_lei"]["positions"] == 1
    assert review_queue(after["positions"]) == []
    assert "Von Hand bestätigt" in render_html(after, [])


def test_no_rejects_the_only_candidate():
    holdings = fund(("Ganz Anderer Name", ISIN_A, "60"))
    report = build_chain(
        holdings, index_candidates([candidate(ISIN_A, "Q1", LEI_ONE)]),
        index_emissions([emission(LEI_ONE)]), gleif(**{LEI_ONE: "Fiktive Mutter AG"}),
        decisions={ISIN_A: {LEI_ONE: "no"}})
    row = report["positions"][0]
    assert row["mapping_confidence"] == "rejected_by_decision" and not row["evidence"]
    assert row["company"]["rejected_leis"] == [LEI_ONE]
    assert report["summary"]["confirmed_coverage"]["positions"] == 0
    assert review_queue(report["positions"]) == []


def test_decisions_resolve_ambiguity_step_by_step():
    holdings = fund(("Fiktive Mutter AG", ISIN_B, "30"))
    candidates = index_candidates([candidate(ISIN_B, "Q2", LEI_ONE, LEI_TWO)])
    names = gleif(**{LEI_ONE: "Fiktive Mutter AG", LEI_TWO: "Fiktive Schwester AG"})

    open_case = build_chain(holdings, candidates, {}, names)
    assert open_case["positions"][0]["mapping_confidence"] == "ambiguous"
    assert [c["lei"] for c in review_queue(open_case["positions"])[0]["candidates"]] == [
        LEI_ONE, LEI_TWO]

    # Ein «nein» streicht einen Kandidaten; bleibt genau einer, läuft die normale Prüfung.
    one_left = build_chain(holdings, candidates, {}, names,
                                 decisions={ISIN_B: {LEI_TWO: "no"}})
    assert one_left["positions"][0]["mapping_confidence"] == "consistent"

    chosen = build_chain(holdings, candidates, {}, names,
                               decisions={ISIN_B: {LEI_TWO: "yes"}})
    row = chosen["positions"][0]
    assert row["mapping_confidence"] == "confirmed_by_decision"
    assert row["mapping_signal"] == "ambiguous"


def test_decision_can_supply_a_company_wikidata_does_not_know():
    holdings = fund(("Fiktive Unbekannt AG", ISIN_C, "20"))
    report = build_chain(holdings, {}, index_emissions([emission(LEI_ONE)]),
                               gleif(**{LEI_ONE: "Fiktive Unbekannt AG"}),
                               decisions={ISIN_C: {LEI_ONE: "yes"}})
    row = report["positions"][0]
    assert row["mapping_confidence"] == "confirmed_by_decision"
    assert row["company"]["source"].startswith("eigener Entscheid")
    assert row["evidence"][0]["status"] == "confirmed"


def test_decision_cannot_override_a_lei_unknown_to_gleif():
    holdings = fund(("Fiktive Mutter AG", ISIN_A, "60"))
    report = build_chain(
        holdings, index_candidates([candidate(ISIN_A, "Q1", LEI_ONE)]),
        index_emissions([emission(LEI_ONE)]),
        {"names": {}, "names_checked": [LEI_ONE], "parents": []},
        decisions={ISIN_A: {LEI_ONE: "yes"}})
    row = report["positions"][0]
    assert row["mapping_confidence"] == "lei_not_in_gleif" and not row["evidence"]


# ------------------------------------------------------------------ Frage-Skript
def test_review_script_stores_answers_and_stops_after_yes(reviewer, tmp_path):
    cases = [
        {"isin": ISIN_B, "position_name": "Fiktive Mutter AG", "weight_percent": 30.0,
         "signal": "ambiguous", "wikidata_names": ["Fiktiv Q2"],
         "candidates": [{"lei": LEI_TWO, "legal_name": "Fiktive Schwester AG",
                         "registration_status": "ISSUED", "other_names": []},
                        {"lei": LEI_ONE, "legal_name": "Fiktive Mutter AG",
                         "registration_status": "ISSUED", "other_names": ["Alt AG"]},
                        {"lei": make_lei("FIKT00000000000009"), "legal_name": "Nie gefragt",
                         "registration_status": "ISSUED", "other_names": []}]},
        {"isin": ISIN_A, "position_name": "Ganz Anderer Name", "weight_percent": None,
         "signal": "name_mismatch", "wikidata_names": [],
         "candidates": [{"lei": LEI_ONE, "legal_name": None, "registration_status": None,
                         "other_names": []}]},
        {"isin": ISIN_C, "position_name": "Nicht erreicht", "weight_percent": 1.0,
         "signal": "name_mismatch", "wikidata_names": [],
         "candidates": [{"lei": LEI_TWO, "legal_name": "X", "registration_status": "ISSUED",
                         "other_names": []}]}]
    replies = iter(["n", "J", "", "q"])
    shown: list[str] = []
    path = tmp_path / "decisions.csv"
    counts = reviewer.review(cases, path, ask=lambda _: next(replies), show=shown.append,
                             today=DAY)
    assert counts == {"yes": 1, "no": 1, "skipped": 1}
    assert index_decisions(load_decisions(path)) == {ISIN_B: {LEI_TWO: "no", LEI_ONE: "yes"}}
    assert len(shown) == 4 and "Alt AG" in shown[1] and "Nie gefragt" not in "".join(shown)
    assert [d.signal for d in load_decisions(path)] == ["ambiguous", "ambiguous"]
