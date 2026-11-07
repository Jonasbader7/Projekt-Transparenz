"""Screening-Engine: Beweisstatus statt Quellenanzahl, keine Verrechnung, Datenlücken sichtbar."""

from __future__ import annotations

from datetime import date

from transparenz.entities.enums import (
    AssessmentStatus as S,
)
from transparenz.entities.enums import (
    AssetClass,
    Confidence,
    EvidenceType,
    ProceedingStatus,
    PublisherType,
    RelationshipType,
    VerificationLevel,
)
from transparenz.entities.identifiers import make_isin, make_lei
from transparenz.entities.models import FundInfo, Position, RelationshipRecord
from transparenz.screening.engine import ScreeningEngine

from conftest import company, coverage_for, criterion, evidence, security

AS_OF = date(2026, 11, 1)


def run(
    evidences, *, criteria=None, coverage=(), issuer_conf=Confidence.HOCH,
    relationships=(), extra_companies=(),
):  # type: ignore[no-untyped-def]
    c = company("A", "Alpha Energie AG")
    eng = ScreeningEngine(
        criteria=criteria or [criterion("kohle")],
        companies=[c, *extra_companies],
        securities=[security(c, issuer_conf)],
        relationships=list(relationships),
        evidence=evidences(c) if callable(evidences) else evidences,
        coverage=coverage(c) if callable(coverage) else coverage,
    )
    pos = Position(isin=security(c).isin, name=c.name, asset_class=AssetClass.AKTIE, weight_pct=100)
    return eng.screen_position(pos, AS_OF).assessments


def court(c, **kw):  # type: ignore[no-untyped-def]
    defaults = dict(etype=EvidenceType.GERICHTSURTEIL, ptype=PublisherType.GERICHT,
                    publisher="Testgericht", status=ProceedingStatus.ABGESCHLOSSEN,
                    verification=VerificationLevel.DOKUMENT_GEPRUEFT)
    return evidence(c, **(defaults | kw))


class TestEvidenceLevels:
    def test_single_final_verified_court_ruling_is_sufficient(self) -> None:
        a = run(lambda c: [court(c)])["kohle"]
        assert a.status == S.FESTGESTELLT
        assert a.decisive is not None

    def test_final_ruling_not_yet_checked_by_us_is_not_established(self) -> None:
        a = run(lambda c: [court(c, verification=VerificationLevel.UNGEPRUEFT)])["kohle"]
        assert a.status == S.PRUEFUNG_AUSSTEHEND

    def test_ongoing_or_unknown_proceeding(self) -> None:
        assert run(lambda c: [court(c, status=ProceedingStatus.LAUFEND)])["kohle"].status == (
            S.VERFAHREN_LAUFEND
        )
        a = run(lambda c: [court(c, status=ProceedingStatus.UNBEKANNT)])["kohle"]
        assert a.status == S.VERFAHREN_LAUFEND
        assert any("unbekannt" in f for f in a.flags)

    def test_authority_allegation_is_proceeding_not_finding(self) -> None:
        a = run(lambda c: [evidence(c, ptype=PublisherType.BEHOERDE, publisher="Staatsanwalt",
                                    status=ProceedingStatus.LAUFEND)])["kohle"]
        assert a.status == S.VERFAHREN_LAUFEND

    def test_ngo_research_is_documented_allegation(self) -> None:
        assert run(lambda c: [evidence(c)])["kohle"].status == S.DOKUMENTIERT

    def test_many_media_reports_do_not_upgrade(self) -> None:
        """Zwei (oder drei) Artikel, die denselben Vorwurf wiederholen, sind kein Beweis."""
        a = run(lambda c: [
            evidence(c, ptype=PublisherType.MEDIEN, publisher="Zeitung A"),
            evidence(c, ptype=PublisherType.MEDIEN, publisher="Zeitung B"),
            evidence(c, ptype=PublisherType.MEDIEN, publisher="Portal C"),
        ])["kohle"]
        assert a.status == S.MEDIENBERICHT
        assert len(a.independent_publishers) == 3
        assert any("ändert den Beweisstatus nicht" in f for f in a.flags)

    def test_strongest_evidence_decides(self) -> None:
        a = run(lambda c: [
            evidence(c, ptype=PublisherType.MEDIEN, publisher="Zeitung"),
            court(c),
            evidence(c),
        ])["kohle"]
        assert a.status == S.FESTGESTELLT
        assert a.decisive is not None and a.decisive.record.publisher == "Testgericht"

    def test_company_self_report_does_not_count(self) -> None:
        a = run(lambda c: [evidence(c, ptype=PublisherType.UNTERNEHMEN, publisher=c.name)],
                coverage=lambda c: [coverage_for(c)])["kohle"]
        assert a.status == S.KEINE_HINWEISE
        assert len(a.not_counted) == 1


class TestContextDoesNotNetOut:
    def test_statement_and_remediation_are_shown_but_do_not_change_status(self) -> None:
        a = run(lambda c: [
            court(c),
            evidence(c, etype=EvidenceType.UNTERNEHMENSSTELLUNGNAHME,
                     ptype=PublisherType.UNTERNEHMEN, publisher=c.name),
            evidence(c, etype=EvidenceType.ABHILFE, ptype=PublisherType.UNTERNEHMEN,
                     publisher=c.name),
        ])["kohle"]
        assert a.status == S.FESTGESTELLT
        assert len(a.context) == 2
        assert any("nicht verrechnet" in f for f in a.flags)

    def test_no_netting_between_criteria(self) -> None:
        crits = [criterion("kohle"), criterion("zwangs_kinderarbeit")]
        res = run(
            lambda c: [court(c, crit="zwangs_kinderarbeit")],
            criteria=crits,
            coverage=lambda c: [coverage_for(c, "kohle"), coverage_for(c, "zwangs_kinderarbeit")],
        )
        assert res["zwangs_kinderarbeit"].status == S.FESTGESTELLT
        assert res["kohle"].status == S.KEINE_HINWEISE  # unabhängig voneinander


class TestMissingData:
    def test_no_coverage_means_unknown_not_clean(self) -> None:
        assert run([])["kohle"].status == S.UNBEKANNT

    def test_coverage_without_evidence_means_no_hints(self) -> None:
        a = run([], coverage=lambda c: [coverage_for(c)])["kohle"]
        assert a.status == S.KEINE_HINWEISE
        assert a.covered_by

    def test_coverage_matched_only_by_name_does_not_count(self) -> None:
        assert run([], coverage=lambda c: [coverage_for(c, by_name=True)])["kohle"].status == (
            S.UNBEKANNT
        )

    def test_position_with_unknown_isin(self) -> None:
        c = company("A")
        eng = ScreeningEngine([criterion()], [c], [security(c)], [], [], [coverage_for(c)])
        pos = Position(isin=make_isin("ZZNICHTDA01"), name="?", asset_class=AssetClass.AKTIE,
                       weight_pct=5)
        r = eng.screen_position(pos, AS_OF)
        assert r.company is None
        assert r.assessments["kohle"].status == S.UNBEKANNT
        assert "nicht identifiziert" in r.assessments["kohle"].flags[0]

    def test_cash_is_not_applicable(self) -> None:
        eng = ScreeningEngine([criterion()], [], [], [], [], [])
        r = eng.screen_position(
            Position(name="Barmittel", asset_class=AssetClass.BARMITTEL, weight_pct=2), AS_OF
        )
        assert not r.applicable
        assert r.assessments["kohle"].status == S.NICHT_ANWENDBAR


class TestWrongMappings:
    def test_evidence_matched_only_by_name(self) -> None:
        a = run(lambda c: [court(c, use_lei=False, name="Alpha Energie")])["kohle"]
        assert a.status == S.ZUORDNUNG_UNSICHER
        assert any("nur über den Namen" in f for f in a.flags)

    def test_uncertain_security_mapping_blocks_findings(self) -> None:
        a = run(lambda c: [court(c)], issuer_conf=Confidence.TIEF)["kohle"]
        assert a.status == S.ZUORDNUNG_UNSICHER

    def test_evidence_for_namesake_with_other_lei_is_ignored(self) -> None:
        c = company("A", "Alpha Energie AG")
        other = make_lei("FIKT00ANDERSWO0001")
        eng = ScreeningEngine([criterion()], [c], [security(c)], [],
                              [court(None, name="Alpha Energie AG", lei=other)], [])
        pos = Position(isin=security(c).isin, name=c.name, asset_class=AssetClass.AKTIE,
                       weight_pct=100)
        assert eng.screen_position(pos, AS_OF).assessments["kohle"].status == S.UNBEKANNT
        assert len(eng.unresolved_evidence) == 1


class TestGroupStructure:
    def make(self, verified: bool):  # type: ignore[no-untyped-def]
        parent = company("P", "Mutter Holding AG")
        rel = RelationshipRecord(parent_key="P", child_key="A",
                                 relationship_type=RelationshipType.DIREKTE_MUTTER,
                                 verified=verified, source="Test")
        return run(lambda c: [court(parent)], relationships=[rel], extra_companies=[parent],
                   coverage=lambda c: [coverage_for(c)])["kohle"]

    def test_verified_parent_evidence_is_inherited(self) -> None:
        a = self.make(verified=True)
        assert a.status == S.FESTGESTELLT
        assert a.decisive is not None and a.decisive.via_parent is not None
        assert any("Muttergesellschaft" in f for f in a.flags)

    def test_unverified_parent_evidence_is_shown_not_inherited(self) -> None:
        a = self.make(verified=False)
        assert a.status == S.KEINE_HINWEISE
        assert len(a.unverified_parent_evidence) == 1
        assert any("nicht verifiziert" in f for f in a.flags)


class TestThresholds:
    def test_open_threshold_shows_metric_with_flag(self) -> None:
        crit = criterion("kohle", metric="umsatzanteil_kohle")
        a = run(lambda c: [evidence(c, metric=("umsatzanteil_kohle", 4.0))], criteria=[crit])
        assert a["kohle"].status == S.DOKUMENTIERT
        assert any("Schwellenwert aber noch nicht festgelegt" in f for f in a["kohle"].flags)

    def test_below_threshold_is_not_counted(self) -> None:
        crit = criterion("kohle", threshold=5.0, metric="umsatzanteil_kohle")
        a = run(lambda c: [evidence(c, metric=("umsatzanteil_kohle", 4.0))], criteria=[crit])
        assert a["kohle"].status == S.KEINE_HINWEISE
        assert any("unter dem festgelegten Schwellenwert" in f for f in a["kohle"].flags)

    def test_above_threshold_counts(self) -> None:
        crit = criterion("kohle", threshold=5.0, metric="umsatzanteil_kohle")
        a = run(lambda c: [evidence(c, metric=("umsatzanteil_kohle", 32.0))], criteria=[crit])
        assert a["kohle"].status == S.DOKUMENTIERT


class TestFundLevel:
    def test_summary_weights_add_up_per_criterion(self) -> None:
        a, b = company("A"), company("B")
        eng = ScreeningEngine(
            [criterion("kohle"), criterion("entwaldung")], [a, b], [security(a), security(b)], [],
            [court(a)], [coverage_for(b)],
        )
        fund = FundInfo(isin=make_isin("ZZFONDS0001"), name="F", provider="P",
                        as_of_date=date(2026, 9, 30))
        positions = [
            Position(isin=security(a).isin, name="A", asset_class=AssetClass.AKTIE, weight_pct=60),
            Position(isin=security(b).isin, name="B", asset_class=AssetClass.AKTIE, weight_pct=35),
            Position(name="Cash", asset_class=AssetClass.BARMITTEL, weight_pct=5),
        ]
        res = eng.screen_fund(fund, positions, AS_OF)
        for s in res.summaries.values():
            assert round(sum(s.weight_by_status.values()), 6) == 100.0
        assert res.summaries["kohle"].weight_by_status[S.FESTGESTELLT] == 60
        assert res.summaries["kohle"].weight_by_status[S.KEINE_HINWEISE] == 35
        assert res.summaries["entwaldung"].weight_by_status[S.UNBEKANNT] == 95
        assert res.positions[0].position.name == "A"  # stärkster Befund zuerst
