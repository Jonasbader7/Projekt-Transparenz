"""Beziehungstypen in Besitzketten (services/ownership.py, D-045). Nur fiktive Namen."""
from __future__ import annotations

import pytest

from transparenz.services.ownership import (
    ASSET_MANAGEMENT,
    CUSTODY,
    FINANCIAL_STAKE,
    OWN_ACCOUNT,
    Hop,
    classify_chain,
    is_financial_sector,
    parse_path,
    stake_tier,
)


def test_parse_path_keeps_share_per_hop_and_unknown_as_none() -> None:
    hops = parse_path("Fiktiv Holding -> Fiktiv Tochter [100.0%] -> Fiktiv Versorger "
                      "[unknown %] -> Werk 1 [5.8%]")
    assert hops == [Hop("Fiktiv Holding", "Fiktiv Tochter", 100.0),
                    Hop("Fiktiv Tochter", "Fiktiv Versorger", None),
                    Hop("Fiktiv Versorger", "Werk 1", 5.8)]
    assert parse_path("nur ein Name") == [] and parse_path(None) == []


@pytest.mark.parametrize(("share", "tier"), [
    (100.0, "control"), (50.0, "control"), (20.0, "significant"), (19.9, "small"),
    (None, "unknown")])
def test_stake_tier(share, tier) -> None:  # type: ignore[no-untyped-def]
    assert stake_tier(share) == tier


def classify(path: str, financial: bool | None = True, listed=None):  # type: ignore[no-untyped-def]
    return classify_chain(parse_path(path), holder_is_financial=financial, listed=listed or {})


def test_bank_and_asset_manager_chains_are_not_ownership() -> None:
    listed = {"Fiktiv Strom AG": True}
    # Verwahrung: Kette über eine Nominee-Gesellschaft.
    custody = classify("Fiktivbank -> Fiktivbank Nominees Pty [100.0%] -> Fiktiv Strom AG "
                       "[14.4%] -> Werk [100.0%]", listed=listed)
    assert custody.relationship == CUSTODY and "Nominee" in custody.reason
    assert classify("Fiktivbank -> Fiktiv Bank and Trust Co [100.0%] -> Werk [100.0%]"
                    ).relationship == CUSTODY
    # Vermögensverwaltung: Kette über eine Fonds- oder Verwaltungsgesellschaft.
    for name in ("Fiktiv Asset Management LP", "Fiktiv Infrastructure Fund",
                 "Fiktiv Trust Corporation", "PTE Fiktiv SA", "Fiktiv SGR SpA",
                 "Fiktiv Global Advisors"):
        result = classify(f"Fiktivbank -> {name} [100.0%] -> Fiktiv Strom AG [6.0%] -> "
                          "Werk [100.0%]", listed=listed)
        assert result.relationship == ASSET_MANAGEMENT, name
    # Finanzbeteiligung: Finanzinstitut mit 5.8 % an einer börsenkotierten Gesellschaft.
    stake = classify("Fiktivbank -> Fiktiv Strom AG [5.8%] -> Werk [100.0%]", listed=listed)
    assert stake.relationship == FINANCIAL_STAKE and "5.8 %" in stake.reason
    assert stake.deciding_hop == 0
    # Auch nach einer eigenen Minderheitsbeteiligung, wenn danach ein kotierter Anteil folgt.
    deep = classify("Fiktiv Versicherung -> Fiktiv Pensionsverwalter [10.4%] -> Fiktiv Strom AG "
                    "[6.0%] -> Werk [100.0%]", listed=listed)
    assert deep.relationship in (FINANCIAL_STAKE, ASSET_MANAGEMENT)


def test_name_patterns_do_not_misread_legal_forms_or_listed_partnerships() -> None:
    listed = {"Fiktiv Infrastructure Partners LP": True}
    # «Pte Ltd» ist die Rechtsform in Singapur, keine Pensionsgesellschaft.
    assert classify("Fiktiv Telecom -> Fiktiv Interactive Pte Ltd [100.0%] -> Werk [100.0%]",
                    financial=False).relationship == OWN_ACCOUNT
    # Eine kotierte Infrastrukturgesellschaft ist kein Vermögensverwalter: 5.9 % einer Bank
    # daran sind eine Finanzbeteiligung.
    assert classify("Fiktivbank -> Fiktiv Infrastructure Partners LP [5.9%] -> Werk [25.0%]",
                    listed=listed).relationship == FINANCIAL_STAKE


def test_own_account_stays_own_account() -> None:
    listed = {"Fiktiv Strom AG": True}
    # Direkt oder über 100-%-Töchter.
    own = classify("Fiktiv Software Corp -> Fiktiv Software Ireland [100.0%] -> Werk [100.0%]",
                   financial=False)
    assert own.relationship == OWN_ACCOUNT and own.group_exit_hop is None
    # Ein Nicht-Finanzunternehmen mit 5 % an einer kotierten Gesellschaft: eigene Beteiligung.
    assert classify("Fiktiv Industrie -> Fiktiv Strom AG [5.0%] -> Werk [100.0%]",
                    financial=False, listed=listed).relationship == OWN_ACCOUNT
    # Ein Finanzinstitut mit eigener Projektbeteiligung (nicht kotiert): eigene Rechnung.
    project = classify("Fiktivbank -> Fiktiv Projekt GmbH [60.0%] -> Werk [100.0%]",
                       listed=listed)
    assert project.relationship == OWN_ACCOUNT
    # Branche unbekannt: keine Annahme zu Gunsten des Unternehmens.
    assert classify("Fiktivbank -> Fiktiv Strom AG [5.8%] -> Werk [100.0%]", financial=None,
                    listed=listed).relationship == OWN_ACCOUNT


def test_financial_sector_from_industry_labels() -> None:
    assert is_financial_sector(["bank", "public company"]) is True
    assert is_financial_sector(["insurance company"]) is True
    assert is_financial_sector(["software industry", "public company"]) is False
    assert is_financial_sector([]) is None and is_financial_sector(None) is None
