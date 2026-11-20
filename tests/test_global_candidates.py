"""Synthetic fixtures only: the global Wikidata ticker/exchange research snapshot.

Every fixture item/exchange id and company name is fictional ("(fiktiv)", Qfiktiv...);
exchange labels/countries are pre-seeded offline so tests never touch the network.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from transparenz.config.settings import get_settings
from transparenz.services import global_candidates as gc


def binding(qid: str, name: str, exchange: str, ticker: str) -> dict:
    return {"item": {"value": f"http://www.wikidata.org/entity/{qid}"},
            "name": {"value": name, "xml:lang": "en"},
            "exchange": {"value": f"http://www.wikidata.org/entity/{exchange}"},
            "ticker": {"value": ticker}}


def write_snapshot(tmp_path: Path, bindings: list[dict]) -> None:
    folder = tmp_path / "data" / gc.SNAPSHOT_DIR  # Zeiger im alten Format "data/raw/…"
    raw = folder / "objects" / "fiktiv.json"
    raw.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps({"results": {"bindings": bindings}}).encode("utf-8")
    raw.write_bytes(content)
    pointer = {
        "source": "wikidata_global", "source_url": "https://query.wikidata.org/sparql",
        "retrieved_at": "2026-11-11T00:00:00+00:00",
        "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content),
        "rows": len(bindings), "license": "CC0 structured data",
        "license_url": "https://www.wikidata.org/wiki/Wikidata:Licensing",
        "file": str(raw.relative_to(tmp_path)), "status": "unverified_research_snapshot",
        "complete_world": False}
    (folder / "current.json").write_text(json.dumps(pointer), encoding="utf-8")


def seed_exchange_labels(tmp_path: Path, exchanges: dict[str, dict]) -> None:
    path = tmp_path / "data/processed/global_candidates/exchange_labels.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"exchanges": exchanges}), encoding="utf-8")


@pytest.fixture
def project(tmp_path, monkeypatch):
    settings = replace(get_settings(), project_root=tmp_path)
    monkeypatch.setattr(gc, "get_settings", lambda: settings)
    return tmp_path


EX_A = {"label_en": "Alpha Exchange (fiktiv)", "label_de": None,
        "countries": [["Qfiktiv_land_a", "Alphaland (fiktiv)"]]}
EX_B = {"label_en": "Beta Exchange (fiktiv)", "label_de": None,
        "countries": [["Qfiktiv_land_b", "Betaland (fiktiv)"]]}


def test_build_and_search_basic(project):
    write_snapshot(project, [binding("Qfiktiv1", "Muster AG (fiktiv)", "Qex_a", "MUST")])
    seed_exchange_labels(project, {"Qex_a": EX_A})
    report = gc.build()
    assert report["counts"] == {
        "entries": 1, "unique_companies": 1, "distinct_exchanges": 1, "distinct_countries": 1,
        "companies_with_multiple_tickers": 0, "rows_missing_exchange_label": 0,
        "rows_missing_exchange_country": 0, "possible_duplicate_name_groups": 0}
    hits = gc.search("Muster")
    assert len(hits) == 1
    assert hits[0]["name"] == "Muster AG (fiktiv)"
    assert hits[0]["exchange_label"] == "Alpha Exchange (fiktiv)"
    assert hits[0]["country_labels"] == ["Alphaland (fiktiv)"]
    assert hits[0]["item_url"] == "https://www.wikidata.org/wiki/Qfiktiv1"


def test_same_item_multiple_exchanges_is_one_company_not_a_duplicate(project):
    write_snapshot(project, [
        binding("Qfiktiv1", "Doppelt AG (fiktiv)", "Qex_a", "DOPA"),
        binding("Qfiktiv1", "Doppelt AG (fiktiv)", "Qex_b", "DOPB")])
    seed_exchange_labels(project, {"Qex_a": EX_A, "Qex_b": EX_B})
    report = gc.build()
    assert report["counts"]["entries"] == 2
    assert report["counts"]["unique_companies"] == 1
    assert report["counts"]["companies_with_multiple_tickers"] == 1
    assert report["counts"]["possible_duplicate_name_groups"] == 0
    hits = gc.search("Doppelt")
    assert len(hits) == 2
    assert {h["ticker"] for h in hits} == {"DOPA", "DOPB"}


def test_same_name_different_items_is_a_possible_duplicate_never_merged(project):
    write_snapshot(project, [
        binding("Qfiktiv1", "Zwilling AG (fiktiv)", "Qex_a", "ZWA"),
        binding("Qfiktiv2", "Zwilling AG (fiktiv)", "Qex_b", "ZWB")])
    seed_exchange_labels(project, {"Qex_a": EX_A, "Qex_b": EX_B})
    report = gc.build()
    assert report["counts"]["unique_companies"] == 2
    assert report["counts"]["companies_with_multiple_tickers"] == 0
    assert report["counts"]["possible_duplicate_name_groups"] == 1
    group = report["possible_duplicates"][0]
    assert group["wikidata_ids"] == ["Qfiktiv1", "Qfiktiv2"]
    hits = gc.search("Zwilling")
    assert {h["wikidata_id"] for h in hits} == {"Qfiktiv1", "Qfiktiv2"}


def test_search_ranks_name_match_over_incidental_substring(project):
    write_snapshot(project, [
        binding("Qfiktiv1", "Lorochemie Holding (fiktiv)", "Qex_a", "LORO"),
        binding("Qfiktiv2", "Roche Nachbau AG (fiktiv)", "Qex_a", "RONA")])
    seed_exchange_labels(project, {"Qex_a": EX_A})
    gc.build()
    hits = gc.search("Roche")
    assert hits[0]["name"] == "Roche Nachbau AG (fiktiv)"


def test_search_is_accent_insensitive(project):
    write_snapshot(project, [binding("Qfiktiv1", "Café Industries (fiktiv)", "Qex_a", "CAFE")])
    seed_exchange_labels(project, {"Qex_a": EX_A})
    gc.build()
    assert len(gc.search("cafe")) == 1
    assert len(gc.search("café")) == 1


def test_country_and_exchange_filters(project):
    write_snapshot(project, [
        binding("Qfiktiv1", "Nordfirma AG (fiktiv)", "Qex_a", "NORD"),
        binding("Qfiktiv2", "Südfirma AG (fiktiv)", "Qex_b", "SUED")])
    seed_exchange_labels(project, {"Qex_a": EX_A, "Qex_b": EX_B})
    gc.build()
    by_country = gc.search("firma", country="Betaland (fiktiv)")
    assert [h["name"] for h in by_country] == ["Südfirma AG (fiktiv)"]
    by_exchange = gc.search("firma", exchange="Qex_a")
    assert [h["name"] for h in by_exchange] == ["Nordfirma AG (fiktiv)"]


def test_changed_snapshot_is_rejected(project):
    from transparenz.services.provenance import ProvenanceError

    write_snapshot(project, [binding("Qfiktiv1", "Muster AG (fiktiv)", "Qex_a", "MUST")])
    raw = project / "data" / gc.SNAPSHOT_DIR / "objects" / "fiktiv.json"
    raw.write_bytes(raw.read_bytes().replace(b"MUST", b"MUSX"))
    with pytest.raises(ProvenanceError, match="weicht"):
        gc.load_snapshot_rows()


def test_missing_snapshot_raises_clear_error(project):
    with pytest.raises(FileNotFoundError, match="download_global_candidates"):
        gc.build()
    with pytest.raises(ValueError, match="global-candidates-build"):
        gc.search("irrelevant")


def test_cache_already_covering_all_ids_never_hits_the_network(project, monkeypatch):
    write_snapshot(project, [binding("Qfiktiv1", "Offline AG (fiktiv)", "Qex_a", "OFFL")])
    seed_exchange_labels(project, {"Qex_a": EX_A})

    def fail(*_args, **_kwargs):
        raise AssertionError("fetch_exchange_labels must not be called when fully cached")

    monkeypatch.setattr(gc, "fetch_exchange_labels", fail)
    report = gc.build()
    assert report["counts"]["entries"] == 1


def test_lock_rejects_simultaneous_builds(project):
    with (gc.global_candidates_lock(), pytest.raises(RuntimeError, match="läuft bereits"),
          gc.global_candidates_lock()):
        pytest.fail("A second writer must not run")
