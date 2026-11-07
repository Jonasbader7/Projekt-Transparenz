"""Import-Validierung: fehlende Angaben, ungültige Werte, Duplikate."""

from __future__ import annotations

import json

import pytest

from transparenz.config.catalog import Catalog
from transparenz.entities.identifiers import make_isin, make_lei
from transparenz.ingestion.parsing import (
    COVERAGE_COLUMNS,
    EVIDENCE_COLUMNS,
    HOLDINGS_COLUMNS,
    PARSERS,
    parse_coverage_csv,
    parse_entities_json,
    parse_evidence_csv,
    parse_holdings_csv,
)

from conftest import SAMPLE

CRITERIA = {"kohle", "entwaldung"}
FUND = make_isin("ZZFONDS0001")


def csv_bytes(columns: tuple[str, ...], rows: list[dict[str, object]], sep: str = ",") -> bytes:
    lines = [sep.join(columns)]
    for r in rows:
        lines.append(sep.join("" if r.get(c) is None else str(r.get(c)) for c in columns))
    return ("\n".join(lines) + "\n").encode("utf-8")


def holding(isin_body: str | None, weight: object, **kw: object) -> dict[str, object]:
    row: dict[str, object] = {
        "fund_isin": FUND, "fund_name": "Testfonds", "fund_provider": "Test",
        "fund_as_of_date": "2026-09-30", "fund_currency": "CHF", "fund_is_fictional": "ja",
        "position_isin": make_isin(isin_body) if isin_body else None,
        "position_name": f"Position {isin_body}", "asset_class": "aktie", "weight_pct": weight,
    }
    row.update(kw)
    return row


def ev_row(eid: str, **kw: object) -> dict[str, object]:
    row: dict[str, object] = {
        "evidence_id": eid, "company_name": "Testfirma AG", "criterion": "kohle",
        "description": "Ein ausreichend langer Beschreibungstext.", "evidence_type": "vorwurf",
        "proceeding_status": "nicht_anwendbar", "publisher": "Test-NGO", "publisher_type": "ngo",
        "source_title": "Bericht", "source_url": "https://example.org/x",
        "published_date": "2026-01-01", "verification_level": "ungeprueft",
    }
    row.update(kw)
    return row


class TestSampleData:
    def test_all_sample_sources_are_valid(self, catalog: Catalog) -> None:
        for src in catalog.sources:
            content = (SAMPLE.parent.parent / src.location).read_bytes()
            ds = PARSERS[(src.kind, src.format)](content, catalog.criterion_keys)
            assert ds.is_valid, (src.key, [str(e) for e in ds.errors])
            assert ds.record_count > 0

    def test_sample_duplicate_is_detected_and_removed(self, catalog: Catalog) -> None:
        ds = parse_evidence_csv((SAMPLE / "fiktiv_belegsammlung.csv").read_bytes(),
                                catalog.criterion_keys)
        assert any("exaktes Duplikat" in str(w) for w in ds.warnings)
        ids = [r.evidence_id for r in ds.records["evidence"]]
        assert len(ids) == len(set(ids))


class TestHoldings:
    def test_valid_file_with_decimal_comma_and_semicolon(self) -> None:
        rows = [holding("ZZAAAAAAA01", "60,5"), holding("ZZBBBBBBB01", "39,5")]
        ds = parse_holdings_csv(csv_bytes(HOLDINGS_COLUMNS, rows, sep=";"))
        assert ds.is_valid, ds.errors
        assert [p.weight_pct for p in ds.records["positions"]] == [60.5, 39.5]
        assert ds.records["funds"][0].is_fictional is True

    def test_invalid_isin_check_digit_rejects_file(self) -> None:
        bad = holding("ZZAAAAAAA01", 100)
        bad["position_isin"] = bad["position_isin"][:-1] + (
            "0" if bad["position_isin"][-1] != "0" else "1"
        )
        ds = parse_holdings_csv(csv_bytes(HOLDINGS_COLUMNS, [bad]))
        assert not ds.is_valid
        assert any("Prüfziffer" in str(e) for e in ds.errors)

    def test_weight_sum_far_off_is_error_slightly_off_is_warning(self) -> None:
        ds = parse_holdings_csv(csv_bytes(HOLDINGS_COLUMNS, [holding("ZZAAAAAAA01", 80)]))
        assert not ds.is_valid
        ds = parse_holdings_csv(csv_bytes(HOLDINGS_COLUMNS, [holding("ZZAAAAAAA01", 99)]))
        assert ds.is_valid and ds.warnings

    def test_missing_required_column(self) -> None:
        cols = tuple(c for c in HOLDINGS_COLUMNS if c != "weight_pct")
        ds = parse_holdings_csv(csv_bytes(cols, [holding("ZZAAAAAAA01", 100)]))
        assert any("Pflichtspalten fehlen" in str(e) for e in ds.errors)

    def test_missing_weight_value(self) -> None:
        ds = parse_holdings_csv(csv_bytes(HOLDINGS_COLUMNS, [holding("ZZAAAAAAA01", None)]))
        assert not ds.is_valid

    def test_mixed_fund_metadata_rejected(self) -> None:
        rows = [
            holding("ZZAAAAAAA01", 50),
            holding("ZZBBBBBBB01", 50, fund_as_of_date="2026-08-31"),
        ]
        ds = parse_holdings_csv(csv_bytes(HOLDINGS_COLUMNS, rows))
        assert any("abweichende Fondsangaben" in str(e) for e in ds.errors)

    def test_exact_duplicate_position_removed_conflicting_rejected(self) -> None:
        rows = [holding("ZZAAAAAAA01", 50), holding("ZZAAAAAAA01", 50), holding("ZZBBBBBBB01", 50)]
        ds = parse_holdings_csv(csv_bytes(HOLDINGS_COLUMNS, rows))
        assert ds.is_valid and len(ds.records["positions"]) == 2
        rows = [holding("ZZAAAAAAA01", 50), holding("ZZAAAAAAA01", 40), holding("ZZBBBBBBB01", 10)]
        ds = parse_holdings_csv(csv_bytes(HOLDINGS_COLUMNS, rows))
        assert any("widersprüchliche" in str(e) for e in ds.errors)

    def test_unknown_asset_class(self) -> None:
        ds = parse_holdings_csv(
            csv_bytes(HOLDINGS_COLUMNS, [holding("ZZAAAAAAA01", 100, asset_class="krypto")])
        )
        assert not ds.is_valid

    def test_empty_and_non_utf8_files(self) -> None:
        assert not parse_holdings_csv(b"").is_valid
        assert not parse_holdings_csv("fund_isin\nÄ".encode("latin-1")).is_valid


class TestEvidence:
    def test_valid_row(self) -> None:
        ds = parse_evidence_csv(csv_bytes(EVIDENCE_COLUMNS, [ev_row("E1")]), CRITERIA)
        assert ds.is_valid, ds.errors

    @pytest.mark.parametrize(
        ("field", "value", "hint"),
        [
            ("criterion", "tabak", "unbekanntes Kriterium"),
            ("source_url", "example.org/x", "http"),
            ("published_date", "2099-01-01", "Zukunft"),
            ("lei", "FIKT00KAPUTT", "LEI"),
            ("evidence_type", "geruecht", "evidence_type"),
            ("description", "kurz", "description"),
        ],
    )
    def test_invalid_values_reject_file(self, field: str, value: str, hint: str) -> None:
        ds = parse_evidence_csv(csv_bytes(EVIDENCE_COLUMNS, [ev_row("E1", **{field: value})]),
                                CRITERIA)
        assert not ds.is_valid
        assert any(hint in str(e) for e in ds.errors), [str(e) for e in ds.errors]

    def test_court_ruling_must_come_from_court(self) -> None:
        row = ev_row("E1", evidence_type="gerichtsurteil", proceeding_status="abgeschlossen")
        ds = parse_evidence_csv(csv_bytes(EVIDENCE_COLUMNS, [row]), CRITERIA)
        assert any("Gericht" in str(e) for e in ds.errors)

    def test_missing_publisher_is_error(self) -> None:
        ds = parse_evidence_csv(csv_bytes(EVIDENCE_COLUMNS, [ev_row("E1", publisher=None)]),
                                CRITERIA)
        assert not ds.is_valid

    def test_duplicates(self) -> None:
        ds = parse_evidence_csv(csv_bytes(EVIDENCE_COLUMNS, [ev_row("E1"), ev_row("E1")]),
                                CRITERIA)
        assert ds.is_valid and len(ds.records["evidence"]) == 1 and ds.warnings
        ds = parse_evidence_csv(
            csv_bytes(EVIDENCE_COLUMNS, [ev_row("E1"), ev_row("E1", publisher="Andere NGO")]),
            CRITERIA,
        )
        assert any("widersprüchliche" in str(e) for e in ds.errors)
        ds = parse_evidence_csv(csv_bytes(EVIDENCE_COLUMNS, [ev_row("E1"), ev_row("E2")]),
                                CRITERIA)
        assert ds.is_valid
        assert any("inhaltliches Duplikat" in str(w) for w in ds.warnings)

    def test_coverage_unknown_criterion(self) -> None:
        rows = [{"company_name": "X AG", "criterion": "tabak", "reviewed_date": "2026-01-01"}]
        assert not parse_coverage_csv(csv_bytes(COVERAGE_COLUMNS, rows), CRITERIA).is_valid


class TestEntities:
    def base(self) -> dict[str, object]:
        return {
            "companies": [
                {"company_key": "A", "name": "A AG", "lei": make_lei("FIKT00AAAAAAAAAA01")},
                {"company_key": "B", "name": "B AG"},
            ],
            "securities": [
                {"isin": make_isin("ZZAAAAAAA01"), "name": "A Aktie", "issuer_company_key": "A",
                 "mapping_method": "register", "mapping_confidence": "hoch",
                 "mapping_source": "Test"}
            ],
            "relationships": [
                {"parent_key": "A", "child_key": "B", "relationship_type": "direkte_mutter",
                 "verified": True, "source": "Test"}
            ],
        }

    def parse(self, data: dict[str, object]):  # type: ignore[no-untyped-def]
        return parse_entities_json(json.dumps(data).encode("utf-8"))

    def test_valid(self) -> None:
        assert self.parse(self.base()).is_valid

    def test_security_with_unknown_issuer(self) -> None:
        d = self.base()
        d["securities"][0]["issuer_company_key"] = "X"  # type: ignore[index]
        assert any("Emittent X unbekannt" in str(e) for e in self.parse(d).errors)

    def test_duplicate_lei(self) -> None:
        d = self.base()
        d["companies"][1]["lei"] = d["companies"][0]["lei"]  # type: ignore[index]
        assert any("mehreren Unternehmen" in str(e) for e in self.parse(d).errors)

    def test_cycle(self) -> None:
        d = self.base()
        d["relationships"].append(  # type: ignore[attr-defined]
            {"parent_key": "B", "child_key": "A", "relationship_type": "direkte_mutter",
             "verified": True, "source": "Test"}
        )
        assert any("Zirkuläre" in str(e) for e in self.parse(d).errors)

    def test_invalid_json(self) -> None:
        assert not parse_entities_json(b"{kein json").is_valid
