"""Kriterienmodell (criteria.toml, Schema 2) und seine Wirkung in der Engine."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from test_screening import AS_OF, court, run
from transparenz.config.catalog import (
    CRITERION_GROUPS,
    Criterion,
    load_catalog,
    load_criteria,
    load_criteria_model,
)
from transparenz.entities.enums import AssessmentStatus as S
from transparenz.entities.enums import AssetClass
from transparenz.entities.identifiers import make_isin
from transparenz.entities.models import FundInfo, Position
from transparenz.screening.engine import ScreeningEngine

from conftest import CONFIG_DIR, company, criterion, evidence, security

CRITERIA = CONFIG_DIR / "criteria.toml"
BASE_KEYS = {"kohle", "fossile_expansion", "waffen", "zwangs_kinderarbeit", "entwaldung",
             "korruption"}
EXTENDED_KEYS = {"biodiversitaet_oekosysteme", "wasser_meeresressourcen",
                 "umweltverschmutzung_gefahrstoffe", "ressourcen_abfall_kreislauf",
                 "arbeitsrechte_arbeitsschutz", "menschenrechte_landrechte"}
HEADER = ('[model]\nschema_version = 2\nprofile_key = "test"\nprofile_name = "Testprofil"\n'
          'profile_version = "0.1"\ndecided_on = 2099-01-01\nstatement = "Testaussage"\n')
MINIMAL = ('[[criterion]]\nkey = "kohle"\nname = "Kohle"\ndescription = "x"\n'
           'severity = "hoch"\n')


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "criteria.toml"
    path.write_text(text, encoding="utf-8")
    return path


# ------------------------------------------------------------------ echtes Modell
def test_real_model_is_versioned_and_complete() -> None:
    model = load_criteria_model(CRITERIA)
    assert model.schema_version == 2 and model.profile_key == "streng"
    assert "Bewertungsentscheidung" in model.statement
    assert {c.key for c in model.active} == BASE_KEYS | EXTENDED_KEYS
    for c in model.active:
        assert c.rule and c.group in CRITERION_GROUPS, c.key
        assert c.conflict_statuses, f"{c.key}: Konfliktregel fehlt"
        assert c.categories, f"{c.key}: Kategorien fehlen"
        # Ohne freigegebene Quelle muss die Lücke benannt sein, statt Abdeckung vorzutäuschen.
        assert c.sources or c.source_gap, c.key
    assert [label for label, _ in model.grouped()] == list(CRITERION_GROUPS.values())
    assert sum(len(items) for _, items in model.grouped()) == len(model.active)


def test_user_decisions_are_marked_decided_and_proposals_stay_proposals() -> None:
    by_key = {c.key: c for c in load_criteria_model(CRITERIA).criteria}
    assert by_key["kohle"].decision == "decided"
    assert by_key["kohle"].is_conflict(S.DOKUMENTIERT)  # jede bestätigte Beteiligung
    assert not by_key["zwangs_kinderarbeit"].is_conflict(S.VERFAHREN_LAUFEND)  # nur bestätigt
    assert by_key["korruption"].conflict_expiry_years == 5
    weapons = {k.key: k for k in by_key["waffen"].categories}
    assert set(weapons) == {"geaechtete_waffen", "kernwaffen", "konventionelle_waffen",
                            "zivile_schusswaffen", "handel_zivile_schusswaffen", "dual_use"}
    # Ausschlüsse je Waffenart sind Vorschlag; «Dual-Use ohne Waffenbestimmung: kein Konflikt»
    # stand schon vorher als entschiedene Abgrenzung im Kriterium.
    assert all(k.decision == "proposed" and k.reason for k in weapons.values()
               if k.key != "dual_use")
    assert weapons["dual_use"].effect == "separate"
    youth = next(k for k in by_key["zwangs_kinderarbeit"].categories
                 if k.key == "jugendbeschaeftigung")
    assert youth.effect == "separate"


def test_emissions_are_metrics_without_exclusion_threshold() -> None:
    model = load_criteria_model(CRITERIA)
    ghg = next(m for m in model.metrics if m.key == "treibhausgas_emissionen")
    assert not ghg.exclusion_threshold_set and len(ghg.required_fields) >= 5
    assert not any(m.exclusion_threshold_set for m in model.metrics)
    assert "emission" not in " ".join(c.key for c in model.criteria)
    assert model.sanctions.role == "evidence" and "Sanktionsgrund" in model.sanctions.rule


def test_proposed_criteria_are_not_active_anywhere() -> None:
    model = load_criteria_model(CRITERIA)
    proposed = {c.key for c in model.proposed}
    assert proposed and proposed.isdisjoint({c.key for c in load_criteria(CRITERIA)})
    catalog = load_catalog(CONFIG_DIR / "sources.toml", CRITERIA)
    assert proposed.isdisjoint(catalog.criterion_keys)
    assert catalog.criteria_model is not None


# ------------------------------------------------------------------ Validierung
@pytest.mark.parametrize(("text", "message"), [
    (MINIMAL, r"\[model\] fehlt"),
    (HEADER.replace("schema_version = 2", "schema_version = 1") + MINIMAL, "nicht unterstützt"),
])
def test_missing_or_old_header_is_rejected(tmp_path: Path, text: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        load_criteria_model(write(tmp_path, text))


@pytest.mark.parametrize(("extra", "message"), [
    (MINIMAL, "Doppelte Kriterien"),
    ('conflict_statuses = ["keine_hinweise"]\n', "kann keinen Konflikt auslösen"),
    ('[[criterion.category]]\nkey = "a"\nname = "A"\neffect = "conflict"\n'
     '[[criterion.category]]\nkey = "a"\nname = "B"\neffect = "separate"\n',
     "doppelte Kategorien"),
    ('[[metric]]\nkey = "m"\nname = "M"\nunit = "t"\ncriterion = "gibt_es_nicht"\n',
     "unbekanntes Kriterium"),
    ('status = "vielleicht"\n', "status"),
])
def test_invalid_models_are_rejected(tmp_path: Path, extra: str, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        load_criteria_model(write(tmp_path, HEADER + MINIMAL + extra))


# ------------------------------------------------------------------ Wirkung in der Engine
def test_activity_criterion_counts_documented_ownership_as_conflict() -> None:
    crit = criterion("kohle", conflict_statuses=("festgestellt", "dokumentiert"))
    a = run(lambda c: [evidence(c)], criteria=[crit])["kohle"]
    assert a.status == S.DOKUMENTIERT and a.profile_conflict


def test_conduct_criterion_needs_a_confirmed_finding() -> None:
    crit = criterion("korruption", conflict_statuses=("festgestellt",))
    suspicion = run(lambda c: [evidence(c, crit="korruption")], criteria=[crit])["korruption"]
    assert suspicion.status == S.DOKUMENTIERT and not suspicion.profile_conflict
    confirmed = run(lambda c: [court(c, crit="korruption")], criteria=[crit])["korruption"]
    assert confirmed.status == S.FESTGESTELLT and confirmed.profile_conflict


def test_without_profile_rule_nothing_is_a_conflict() -> None:
    a = run(lambda c: [court(c)])["kohle"]
    assert a.status == S.FESTGESTELLT and not a.profile_conflict and a.profile_note == ""


def test_historic_case_keeps_its_status_but_loses_conflict_effect() -> None:
    crit = criterion("korruption", conflict_statuses=("festgestellt",), conflict_expiry_years=5)
    old = run(lambda c: [court(c, crit="korruption", published=date(2019, 2, 28))],
              criteria=[crit])["korruption"]
    assert old.status == S.FESTGESTELLT and not old.profile_conflict
    assert "Historischer Fall" in old.profile_note and "28.02.2019" in old.profile_note
    recent = run(lambda c: [court(c, crit="korruption", published=date(2021, 11, 1))],
                 criteria=[crit])["korruption"]
    assert recent.profile_conflict  # genau fünf Jahre: Wirkung gilt noch am Stichtag


def test_fund_summary_reports_conflict_weight_per_criterion() -> None:
    a, b = company("A"), company("B")
    kohle = criterion("kohle", conflict_statuses=("festgestellt", "dokumentiert"))
    engine = ScreeningEngine([kohle, criterion("entwaldung")], [a, b],
                             [security(a), security(b)], [], [evidence(a)], [])
    fund = FundInfo(isin=make_isin("ZZFONDS0001"), name="F", provider="P",
                    as_of_date=date(2026, 9, 30))
    positions = [
        Position(isin=security(a).isin, name="A", asset_class=AssetClass.AKTIE, weight_pct=60),
        Position(isin=security(b).isin, name="B", asset_class=AssetClass.AKTIE, weight_pct=40)]
    result = engine.screen_fund(fund, positions, AS_OF)
    assert (result.summaries["kohle"].conflict_weight,
            result.summaries["kohle"].conflict_count) == (60, 1)
    assert result.summaries["entwaldung"].conflict_weight == 0
    assert result.weight_with_profile_conflict == 60
    assert result.positions[0].profile_conflicts == ["kohle"]


def test_criterion_model_is_frozen() -> None:
    with pytest.raises(ValidationError):
        Criterion(key="x", name="X", description="x", severity="hoch").rule = "neu"
