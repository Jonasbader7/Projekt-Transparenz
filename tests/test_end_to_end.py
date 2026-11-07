"""End-to-End: CSV-Import → Validierung → Datenbank → Screening → Bericht → Streamlit-Anzeige.

Läuft vollständig in einem temporären Ordner (Kopie der fiktiven Beispieldaten).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from transparenz.entities.enums import AssessmentStatus as S
from transparenz.entities.enums import UpdateStatus
from transparenz.reports.fund_report import findings_table, to_markdown
from transparenz.services.context import create_context

from conftest import FUND_ISIN, ROOT

APP = str(ROOT / "app" / "main.py")

# Erwartete Belegstatus der fiktiven Beispieldaten (siehe docs/DATA_MODEL.md)
EXPECTED = {
    ("Tiefsee Öl & Gas Beispiel SA", "oel_gas_expansion"): S.FESTGESTELLT,
    ("Waldland Agrar Beispiel Ltd", "entwaldung"): S.FESTGESTELLT,
    ("Präzisionstechnik Beispiel AG", "geaechtete_waffen"): S.PRUEFUNG_AUSSTEHEND,
    ("Muster Textil Gruppe AG", "zwangs_kinderarbeit"): S.VERFAHREN_LAUFEND,
    ("Alpenstrom Muster AG", "kohle"): S.DOKUMENTIERT,
    ("Alpenstrom Muster AG 1.5 % 2031", "kohle"): S.DOKUMENTIERT,
    ("Nordkohle Beispiel plc", "kohle"): S.DOKUMENTIERT,
    ("Kakao Handel Beispiel SA", "zwangs_kinderarbeit"): S.ZUORDNUNG_UNSICHER,
    ("Bahnbau Beispiel AG", "zwangs_kinderarbeit"): S.ZUORDNUNG_UNSICHER,
    ("Grüne Logistik Beispiel AG", "zwangs_kinderarbeit"): S.KEINE_HINWEISE,
    ("Datenwolke Beispiel Inc", "kohle"): S.UNBEKANNT,
    ("Unbekannte Beteiligung Beispiel AG", "kohle"): S.UNBEKANNT,
    ("Barmittel CHF", "kohle"): S.NICHT_ANWENDBAR,
    ("Sonnenpark Beispiel AG", "entwaldung"): S.KEINE_HINWEISE,
}


@pytest.fixture
def imported(isolated_project: Path):  # type: ignore[no-untyped-def]
    ctx = create_context()
    outcomes = ctx.updates.run_all(force=True, trigger="test")
    assert all(o.status == UpdateStatus.ERFOLGREICH for o in outcomes), [
        (o.source_key, o.message, o.errors) for o in outcomes
    ]
    yield ctx
    ctx.engine.dispose()


def test_import_and_screening_produce_expected_statuses(imported) -> None:  # type: ignore[no-untyped-def]
    result = imported.analyze_fund(FUND_ISIN)
    assert result is not None
    by_name = {p.position.name: p for p in result.positions}
    for (name, crit), status in EXPECTED.items():
        assert by_name[name].assessments[crit].status == status, (name, crit)
    # Sachverhalte zu unbekannter Firma und zu Namensvetter mit anderem LEI: nicht zugeordnet
    unresolved = {ev.record.evidence_id for ev, _ in result.unresolved_evidence}
    assert unresolved == {"BEL-017", "BEL-018"}
    assert round(result.total_weight, 6) == 100.0


def test_every_displayed_finding_has_source_and_data_version(imported) -> None:  # type: ignore[no-untyped-def]
    data = imported.active_data()
    result = imported.analyze_fund(FUND_ISIN, data=data)
    table = findings_table(result, imported.source_names)
    assert len(table) > 0
    for _, row in table.iterrows():
        assert row["URL"].startswith("https://")
        assert row["Herausgeber"] and row["Veröffentlicht"] != "–"
        assert "Version #" in row["Datenstand"] and "Hash" in row["Datenstand"]
        assert "importiert" in row["Datenstand"]
    md = to_markdown(result, "Test", imported.data_version_lines(data), imported.source_names)
    assert md.count("Datenquelle:") >= 10
    assert "Laut Gerichtsurteil (Fiktives Verwaltungsgericht Musterkanton, 12.03.2025)" in md


def test_failed_update_keeps_displayed_data(imported, isolated_project: Path) -> None:  # type: ignore[no-untyped-def]
    before = imported.analyze_fund(FUND_ISIN)
    path = isolated_project / "fiktiv_etf_positionen.csv"
    path.write_text(path.read_text(encoding="utf-8").replace(",10.0,", ",95.0,", 1),
                    encoding="utf-8")  # Gewichtssumme 185 % → ungültig
    out = imported.updates.run_source("fiktiv_etf", force=True)
    assert out.status == UpdateStatus.FEHLGESCHLAGEN
    after = imported.analyze_fund(FUND_ISIN)
    assert [p.position.weight_pct for p in after.positions] == [
        p.position.weight_pct for p in before.positions
    ]


def _all_text(at: AppTest) -> str:
    parts: list[str] = []
    for kind in ("title", "subheader", "markdown", "caption", "info", "warning", "error"):
        parts += [str(getattr(el, "value", "")) for el in getattr(at, kind)]
    parts += [str(e.label) for e in at.expander]
    return "\n".join(parts)


def test_streamlit_shows_imported_csv_data(imported) -> None:  # type: ignore[no-untyped-def]
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert not at.exception, at.exception
    at.switch_page("views/fund_analysis.py")
    at.run()
    assert not at.exception, at.exception
    text = _all_text(at)
    assert "Muster Nachhaltigkeit Welt ETF (fiktiv)" in text
    assert "Fiktive Demodaten" in text
    assert "Waldland Agrar Beispiel Ltd" in text
    assert "Laut Gerichtsurteil (Fiktives Verwaltungsgericht Musterkanton, 12.03.2025)" in text
    assert "Version #" in text  # Datenstand bei der Feststellung
    assert "BEL-018" in _dataframes_text(at)  # nicht zugeordneter Sachverhalt sichtbar
    positions = at.dataframe[1].value
    assert len(positions) == 19
    assert "Festgestellt" in positions.to_string()


def _dataframes_text(at: AppTest) -> str:
    return "\n".join(df.value.to_string() for df in at.dataframe)


@pytest.mark.parametrize("page", ["views/methodology.py", "views/data_sources.py"])
def test_other_pages_render(imported, page: str) -> None:  # type: ignore[no-untyped-def]
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    at.switch_page(page)
    at.run()
    assert not at.exception, at.exception


def test_empty_database_offers_manual_import(isolated_project: Path) -> None:
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert not at.exception, at.exception
    assert "Noch keine Daten importiert" in _all_text(at)
    at.button[0].click()
    at.run()
    assert not at.exception, at.exception
    assert "Muster Nachhaltigkeit Welt ETF (fiktiv)" in _all_text(at)
