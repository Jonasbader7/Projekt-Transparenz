"""Kennungen (ISIN ≠ LEI) und Schutz vor falschen Unternehmenszuordnungen."""

from __future__ import annotations

from transparenz.entities.enums import Confidence, MappingMethod
from transparenz.entities.identifiers import (
    is_fictional_isin,
    is_valid_isin,
    is_valid_lei,
    make_isin,
    make_lei,
    normalize_company_name,
)
from transparenz.entities.models import CompanyRecord
from transparenz.entities.resolution import EntityResolver

from conftest import company, security


class TestIdentifiers:
    def test_known_real_isin_is_valid(self) -> None:
        # Öffentlich dokumentiertes Beispiel für die ISIN-Prüfziffer
        assert is_valid_isin("US0378331005")

    def test_tampered_isin_is_invalid(self) -> None:
        assert not is_valid_isin("US0378331006")
        assert not is_valid_isin("US037833100")
        assert not is_valid_isin(None)

    def test_fictional_isin_roundtrip(self) -> None:
        isin = make_isin("ZZTEST00001")
        assert is_valid_isin(isin)
        assert is_fictional_isin(isin)

    def test_lei_roundtrip_and_tampering(self) -> None:
        lei = make_lei("FIKT00ABCDEFGHIJ12")
        assert is_valid_lei(lei)
        tampered = lei[:-3] + ("X" if lei[-3] != "X" else "Y") + lei[-2:]
        assert not is_valid_lei(tampered)
        assert not is_valid_lei(lei[:-1])

    def test_isin_is_not_a_lei(self) -> None:
        assert not is_valid_lei("US0378331005")
        assert not is_valid_isin(make_lei("FIKT00ABCDEFGHIJ12"))

    def test_name_normalisation(self) -> None:
        assert normalize_company_name("Kakao Handel Beispiel S.A.") == normalize_company_name(
            "Kakao Handel Beispiel SA"
        )
        assert normalize_company_name("Tiefsee Öl & Gas AG") == "tiefsee ol gas"


class TestResolution:
    def setup_method(self) -> None:
        self.a = company("A", "Alpha Energie AG")
        self.b = company("B", "Beta Handel AG")
        self.no_lei = company("C", "Gamma Bau AG", lei=False)
        self.twin1 = company("D", "Zwilling AG")
        self.twin2 = CompanyRecord(company_key="E", name="Zwilling SA", lei=None)
        self.r = EntityResolver(
            [self.a, self.b, self.no_lei, self.twin1, self.twin2],
            [security(self.a), security(self.no_lei, Confidence.MITTEL)],
        )

    def test_lei_match_is_high_confidence(self) -> None:
        res = self.r.resolve("irgendein Name", lei=self.a.lei)
        assert res.company_key == "A"
        assert res.method == MappingMethod.LEI
        assert res.confidence == Confidence.HOCH

    def test_lei_wins_over_misleading_name(self) -> None:
        res = self.r.resolve("Beta Handel AG", lei=self.a.lei)
        assert res.company_key == "A"

    def test_isin_resolves_via_security_with_its_confidence(self) -> None:
        res = self.r.resolve("x", isin=security(self.no_lei).isin)
        assert res.company_key == "C"
        assert res.method == MappingMethod.ISIN
        assert res.confidence == Confidence.MITTEL

    def test_name_only_is_low_confidence(self) -> None:
        res = self.r.resolve("Alpha Energie")
        assert res.company_key == "A"
        assert res.confidence == Confidence.TIEF

    def test_conflicting_lei_blocks_name_match(self) -> None:
        """Gleicher Name, aber anderer LEI = anderer Rechtsträger → keine Zuordnung."""
        other_lei = make_lei("FIKT00ANDERSWO0001")
        res = self.r.resolve("Alpha Energie AG", lei=other_lei)
        assert res.company_key is None
        assert "LEI" in res.note

    def test_unknown_lei_may_match_company_without_lei_by_name(self) -> None:
        res = self.r.resolve("Gamma Bau AG", lei=make_lei("FIKT00ANDERSWO0001"))
        assert res.company_key == "C"
        assert res.confidence == Confidence.TIEF

    def test_ambiguous_name_is_not_resolved(self) -> None:
        res = self.r.resolve("Zwilling")
        assert res.company_key is None
        assert "mehrdeutig" in res.note

    def test_unknown_company_is_not_resolved(self) -> None:
        assert self.r.resolve("Gibt es nicht GmbH").company_key is None

    def test_security_without_mapping(self) -> None:
        res = self.r.resolve_security(make_isin("ZZNICHTDA01"))
        assert res.company_key is None
        assert "nicht in Stammdaten" in res.note
