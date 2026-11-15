"""Automatische Zuordnung ohne Einzelfallfreigabe (services/entity_matching.py, D-046).

Ausschliesslich fiktive Kennungen und Namen.
"""
from __future__ import annotations

import pytest

from transparenz.entities.identifiers import make_lei
from transparenz.services.entity_matching import (
    RELEASE_MIN_CASES,
    GleifCandidate,
    allowed_countries,
    evaluate,
    match_by_name,
    match_by_register,
    name_key,
    precision_lower_bound,
    register_queries,
    security_query,
)

LEI_A = make_lei("FIKT00000000000101")
LEI_B = make_lei("FIKT00000000000102")
LEI_C = make_lei("FIKT00000000000103")


def cand(lei: str, name: str, country: str = "US", **kw) -> GleifCandidate:  # type: ignore[no-untyped-def]
    defaults = {"legal_country": country, "hq_country": country, "entity_status": "ACTIVE",
                "registration_status": "ISSUED", "category": "GENERAL"}
    return GleifCandidate(lei=lei, legal_name=name, **(defaults | kw))


def test_names_are_compared_without_legal_forms_share_classes_and_group_words() -> None:
    assert security_query("Fiktivo B (GBP)") == "fiktivo"
    assert name_key("Fiktivo Reg Shs", security=True) == name_key("FIKTIVO HOLDING AG")
    assert name_key("Fiktivo", security=True) == name_key("THE FIKTIVO GROUP")
    # Branchenwörter bleiben: zwei verschiedene Unternehmen.
    assert name_key("Fiktivo", security=True) != name_key("Fiktivo Energy AG")


def test_name_match_needs_equal_name_country_and_active_entity() -> None:
    names = ["Fiktivo Corp"]
    ok = match_by_name(names, {"US"}, [cand(LEI_A, "FIKTIVO CORPORATION"),
                                       cand(LEI_B, "FIKTIVO SERVICES LLC")])
    assert (ok.status, ok.lei) == ("accepted", LEI_A)
    assert match_by_name(names, {"CH"}, [cand(LEI_A, "FIKTIVO CORPORATION")]).status == \
        "no_candidate"
    for bad in ({"entity_status": "INACTIVE"}, {"category": "FUND"},
                {"registration_status": "RETIRED"}):
        assert match_by_name(names, {"US"}, [cand(LEI_A, "FIKTIVO CORP", **bad)]).status == \
            "no_candidate", bad
    two = match_by_name(names, {"US"}, [cand(LEI_A, "FIKTIVO CORP"),
                                        cand(LEI_B, "Fiktivo Holding Co")])
    assert two.status == "ambiguous" and two.lei is None
    assert match_by_name(names, {"US"}, [], truncated=True).status == "too_many"


def test_name_match_resolves_ties_only_through_gleif_parent() -> None:
    names = ["Fiktivo"]
    tied = [cand(LEI_A, "THE FIKTIVO GROUP"), cand(LEI_B, "FIKTIVO HOLDING COMPANY")]
    parent = match_by_name(names, {"US"}, tied, parent_of={LEI_B: {LEI_A}})
    assert (parent.status, parent.lei) == ("accepted", LEI_A)
    assert "Mutter" in parent.reason
    assert match_by_name(names, {"US"}, tied, parent_of={}).status == "ambiguous"


def test_allowed_countries_use_isin_prefix_and_issuer_country() -> None:
    assert allowed_countries("IE00BFIKTIV0", "GB") == {"IE", "GB"}
    assert allowed_countries("XS0000000000", None) == set()


def test_register_match_uses_number_and_jurisdiction() -> None:
    queries = register_queries({"P1320": ["us_de/1234567"], "P3549": ["000 111 222"]})
    assert queries == [("P1320", "1234567", "US-DE"), ("P3549", "000111222", "AU"),
                       ("P3549", "000 111 222", "AU")]
    found = {"1234567": [cand(LEI_A, "Fiktivo", jurisdiction="US-DE", registered_as="1234567"),
                         cand(LEI_B, "Anderes", "CA", jurisdiction="CA-ON",
                              registered_as="1234567")],
             "000111222": []}
    result = match_by_register(queries, found)
    assert (result.status, result.lei) == ("accepted", LEI_A)
    abn = register_queries({"P3548": ["51 000 111 222"]})
    assert abn == [("P3548", "51000111222", "AU"), ("P3549", "000111222", "AU"),
                   ("P3549", "000 111 222", "AU")]
    assert match_by_register(abn, {"51000111222": [], "000111222": [
        cand(LEI_C, "Fiktivo Pty", "AU", jurisdiction="AU", registered_as="000111222")]}).lei \
        == LEI_C
    assert match_by_register([], {}).status == "not_searched"


@pytest.mark.parametrize(("correct", "total", "low", "high"), [
    (100, 100, 0.97, 0.971), (99, 100, 0.95, 0.96), (0, 0, 0.0, 0.0), (5, 10, 0.2, 0.25)])
def test_precision_lower_bound(correct, total, low, high) -> None:  # type: ignore[no-untyped-def]
    assert low <= precision_lower_bound(correct, total) <= high


def test_evaluate_separates_coverage_from_precision_and_gates_release() -> None:
    cases = [{"reference_lei": LEI_A, "predicted_lei": LEI_A} for _ in range(RELEASE_MIN_CASES)]
    cases += [{"reference_lei": LEI_B, "predicted_lei": None} for _ in range(50)]
    result = evaluate(cases)
    assert result["coverage"] == round(RELEASE_MIN_CASES / (RELEASE_MIN_CASES + 50), 4)
    assert result["precision"] == 1.0 and result["released"] is True
    worse = evaluate([*cases, {"reference_lei": LEI_A, "predicted_lei": LEI_C}])
    assert worse["wrong"] == 1 and worse["wrong_cases"][0]["predicted_lei"] == LEI_C
    assert worse["released"] is False  # untere Grenze fällt unter 97 %
    assert evaluate(cases[:10])["released"] is False  # zu wenige Referenzfälle


def test_legal_forms_and_abbreviated_names_found_in_the_first_fund() -> None:
    """Fehlerursachen aus dem ersten Fonds, mit fiktiven Namen nachgebildet."""
    # «Public Limited Company» ist eine Rechtsform: Mutter und Tochter heissen gleich, die
    # GLEIF-Beziehung entscheidet für die Mutter (vorher wurde die Tochter gewählt).
    group = [cand(LEI_A, "FIKTIVFON GROUP PUBLIC LIMITED COMPANY", "GB"),
             cand(LEI_B, "FIKTIVFON LIMITED", "GB")]
    result = match_by_name(["Fiktivfon Group"], {"GB"}, group, parent_of={LEI_B: {LEI_A}})
    assert (result.status, result.lei) == ("accepted", LEI_A)
    # Italienischer Rechtsname mit Kurzform in Klammern; «S.p.A.» = «SpA».
    long_name = cand(LEI_C, 'FIKTERNA - RETE FIKTIVA SOCIETA\' PER AZIONI (IN FORMA ABBREVIATA '
                     '"FIKTERNA S.P.A.")', "IT")
    assert match_by_name(["Fikterna SpA"], {"IT"}, [long_name]).lei == LEI_C


def test_register_match_rejects_entity_outside_the_issuer_country() -> None:
    queries = register_queries({"P1320": ["fi/1234567-8"]})
    foreign = {"1234567-8": [cand(LEI_A, "Fiktiv Forestry Oy", "FI", jurisdiction="FI",
                                  registered_as="1234567-8")]}
    assert match_by_register(queries, foreign).lei == LEI_A
    assert match_by_register(queries, foreign, {"US"}).status == "no_candidate"


def test_register_numbers_are_searched_in_gleif_spelling() -> None:
    """GLEIF sucht exakt: australische ACN mit Leerzeichen, japanische Nummer zwölfstellig."""
    japan = register_queries({"P3225": ["6120001059662"]})
    assert ("P3225", "1200-01-059662", "JP") in japan
    found = {"1200-01-059662": [cand(LEI_A, "Fiktiv KK", "JP", jurisdiction="JP",
                                     registered_as="1200-01-059662")]}
    assert match_by_register(japan, found, {"JP"}).lei == LEI_A
