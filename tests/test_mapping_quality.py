"""Zuordnungsquote Wertpapier → Unternehmen (stufenweise, nach Anzahl und Gewicht)."""

from __future__ import annotations

from transparenz.entities.enums import AssetClass, Confidence, MappingMethod
from transparenz.entities.identifiers import make_isin, make_lei
from transparenz.entities.models import CompanyRecord, Position, SecurityRecord
from transparenz.entities.resolution import EntityResolver
from transparenz.services.mapping_quality import measure_mapping_quality

LEI_GLEIF = make_lei("FIKT00MAPGLEIF0001")
LEI_OTHER = make_lei("FIKT00MAPANDERS001")
ISIN = {k: make_isin(f"ZZMAP{k}00000"[:11]) for k in ("A", "B", "C", "D", "E")}


def pos(name: str, weight: float, isin: str | None = None,
        asset_class: AssetClass = AssetClass.AKTIE) -> Position:
    return Position(isin=isin, name=name, asset_class=asset_class, weight_pct=weight)


def sec(isin: str, issuer: str | None) -> SecurityRecord:
    return SecurityRecord(
        isin=isin, name=f"Wertpapier {isin}", issuer_company_key=issuer,
        mapping_method=MappingMethod.MANUELL if issuer else MappingMethod.KEINE,
        mapping_confidence=Confidence.HOCH, mapping_source="Test (fiktiv)",
    )


def resolver() -> EntityResolver:
    companies = [
        CompanyRecord(company_key="g", name="Muster Gleif AG (fiktiv)", lei=LEI_GLEIF),
        CompanyRecord(company_key="o", name="Muster Anders AG (fiktiv)", lei=LEI_OTHER),
        CompanyRecord(company_key="n", name="Muster Ohne LEI AG (fiktiv)"),
    ]
    securities = [
        sec(ISIN["A"], "g"), sec(ISIN["B"], "o"), sec(ISIN["C"], "n"), sec(ISIN["D"], None),
    ]
    return EntityResolver(companies, securities)


def test_steps_count_and_weight() -> None:
    positions = [
        pos("A", 30, ISIN["A"]),  # bis GLEIF
        pos("B", 20, ISIN["B"]),  # LEI, aber nicht bei GLEIF
        pos("C", 15, ISIN["C"]),  # Emittent ohne LEI
        pos("D", 10, ISIN["D"]),  # Emittent nicht zugeordnet
        pos("E", 10, ISIN["E"]),  # ISIN unbekannt
        pos("F", 5),  # ohne ISIN
        pos("Bar", 6, asset_class=AssetClass.BARMITTEL),  # nicht relevant
        pos("Swap", 4, asset_class=AssetClass.DERIVAT),  # nicht relevant
    ]
    q = measure_mapping_quality(positions, resolver(), gleif_leis={LEI_GLEIF})
    assert q.total_positions == 8
    assert q.total_weight_pct == 100
    got = {s.key: (s.count, s.weight_pct) for s in q.steps}
    assert got == {
        "relevant": (6, 90),
        "with_isin": (5, 85),
        "resolved": (3, 65),
        "with_lei": (2, 50),
        "lei_in_gleif": (1, 30),
    }
    by_count, by_weight = q.share("lei_in_gleif")
    assert round(by_count or 0, 1) == 16.7
    assert round(by_weight or 0, 1) == 33.3
    assert [g.position_name for g in q.gaps] == ["B", "C", "D", "E", "F"]  # nach Gewicht
    reasons = {g.position_name: g.reason for g in q.gaps}
    assert reasons["B"] == "LEI nicht in GLEIF-Datenstand"
    assert reasons["C"] == "Emittent ohne LEI"
    assert reasons["F"] == "keine ISIN"


def test_share_is_none_without_relevant_positions() -> None:
    q = measure_mapping_quality(
        [pos("Bar", 100, asset_class=AssetClass.BARMITTEL)], resolver(), gleif_leis=set()
    )
    assert q.share("lei_in_gleif") == (None, None)


def test_fictional_demo_fund_has_no_gleif_confirmation(isolated_project) -> None:  # type: ignore[no-untyped-def]
    """Beispieldaten: fiktive LEIs (FIKT00…) können nie bei GLEIF gefunden werden."""
    from transparenz.services.context import create_context

    from conftest import FUND_ISIN

    ctx = create_context()
    ctx.updates.run_all(force=True)
    data = ctx.active_data()
    q = measure_mapping_quality(
        data.funds[FUND_ISIN].positions, EntityResolver(data.companies, data.securities),
        gleif_leis=set(),
    )
    assert q.step("with_lei").count > 0
    assert q.step("lei_in_gleif").count == 0
