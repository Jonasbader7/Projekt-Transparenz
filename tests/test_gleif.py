"""GLEIF-Adapter: Abfrageliste, Abruf (simuliert), Validierung, Übersetzung, Update-Lauf.

Alle Testdaten in tests/fixtures/gleif/ sind FIKTIV (LEI-Präfix FIKT00), aber im Aufbau
echter GLEIF-API-Antworten (geprüft am 07.11.2026 an api.gleif.org).
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select

from transparenz.config.catalog import Catalog, SourceConfig, UpdateDefaults
from transparenz.database.models import CompanyRow, RelationshipRow
from transparenz.database.repository import load_active_data
from transparenz.entities.enums import (
    CommercialUse,
    DatasetKind,
    RelationshipType,
    UpdateStatus,
)
from transparenz.ingestion.adapters import SourceAdapter
from transparenz.ingestion.fetchers import FetchError
from transparenz.ingestion.gleif import (
    BUNDLE_FORMAT,
    GleifApiFetcher,
    company_key_for_lei,
    parse_gleif_bundle,
    read_lei_list,
)
from transparenz.services.update_manager import DataUpdateManager

FIX = Path(__file__).resolve().parent / "fixtures" / "gleif"
TOCHTER = "FIKT00GLTOCHTER00130"
MUTTER = "FIKT00GLMUTTER000119"
OBERSTE = "FIKT00GLOBERST000177"
LAPSED = "FIKT00GLLAPSED000122"
ANNULLED = "FIKT00GLANNULL000110"
FEHLT = "FIKT00GLFEHLT0000114"
BASE = "https://api.gleif.org/api/v1"


def fixture(name: str) -> dict:  # type: ignore[type-arg]
    return json.loads((FIX / name).read_text(encoding="utf-8"))


class FakeGleif:
    """Simulierte GLEIF-API auf Basis der fiktiven Testdateien."""

    def __init__(self, fail_with: int | None = None) -> None:
        self.requests: list[httpx.Request] = []
        self.fail_with = fail_with

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.fail_with:
            return httpx.Response(self.fail_with)
        path = request.url.path
        if path.endswith("/lei-records"):
            leis = set(request.url.params["filter[lei]"].split(","))
            if TOCHTER in leis:
                return httpx.Response(200, json=fixture("api_lei_records_abfrage.json"))
            if leis == {MUTTER, OBERSTE}:
                return httpx.Response(200, json=fixture("api_lei_records_muetter.json"))
            return httpx.Response(200, json={"meta": {}, "data": []})
        if path.endswith(f"/{TOCHTER}/direct-parent-relationship"):
            return httpx.Response(200, json=fixture("api_direct_parent_relationship.json"))
        if path.endswith(f"/{TOCHTER}/ultimate-parent-relationship"):
            return httpx.Response(200, json=fixture("api_ultimate_parent_relationship.json"))
        return httpx.Response(404)


def make_fetcher(api: FakeGleif, sleeps: list[float] | None = None) -> GleifApiFetcher:
    return GleifApiFetcher(
        FIX / "abfrageliste_fiktiv.txt",
        base_url=BASE,
        user_agent="transparenz-test/0.1",
        client=httpx.Client(transport=httpx.MockTransport(api)),
        sleep=(sleeps.append if sleeps is not None else lambda _: None),
    )


def bundle() -> bytes:
    content = make_fetcher(FakeGleif()).fetch().content
    assert content is not None
    return content


# ------------------------------------------------------------------ Abfrageliste
class TestLeiList:
    def test_reads_comments_dedupes_and_sorts(self) -> None:
        leis = read_lei_list(FIX / "abfrageliste_fiktiv.txt")
        assert leis == sorted({TOCHTER, LAPSED, ANNULLED, FEHLT})

    def test_invalid_lei_stops_everything(self, tmp_path: Path) -> None:
        f = tmp_path / "liste.txt"
        f.write_text(f"{TOCHTER}\nFIKT00GLTOCHTER00131\n", encoding="utf-8")
        with pytest.raises(FetchError, match="Zeile 2") as exc:
            read_lei_list(f)
        assert exc.value.transient is False

    def test_empty_or_missing_list(self, tmp_path: Path) -> None:
        f = tmp_path / "leer.txt"
        f.write_text("# nur Kommentar\n", encoding="utf-8")
        with pytest.raises(FetchError, match="keine LEIs"):
            read_lei_list(f)
        with pytest.raises(FetchError, match="nicht gefunden"):
            read_lei_list(tmp_path / "fehlt.txt")

    def test_real_project_list_is_valid(self) -> None:
        root = Path(__file__).resolve().parents[1]
        assert read_lei_list(root / "data" / "gleif" / "abfrageliste.txt") == [
            "506700GE1G29325QX363"  # GLEIF selbst (Funktionsprobe)
        ]


# ------------------------------------------------------------------------ Abruf
class TestFetcher:
    def test_requests_records_parents_and_respects_rate_limit(self) -> None:
        api = FakeGleif()
        sleeps: list[float] = []
        result = make_fetcher(api, sleeps).fetch()
        paths = [r.url.path for r in api.requests]
        assert paths == [
            "/api/v1/lei-records",
            f"/api/v1/lei-records/{TOCHTER}/direct-parent-relationship",
            f"/api/v1/lei-records/{TOCHTER}/ultimate-parent-relationship",
            "/api/v1/lei-records",  # Muttergesellschaften nachladen
        ]
        assert api.requests[0].url.params["filter[lei]"] == ",".join(
            sorted({TOCHTER, LAPSED, ANNULLED, FEHLT})
        )
        assert sleeps == [1.1, 1.1, 1.1]  # zwischen den Anfragen, < 60 pro Minute
        assert all(r.headers["User-Agent"] == "transparenz-test/0.1" for r in api.requests)
        assert all(r.headers["Accept"] == "application/vnd.api+json" for r in api.requests)
        data = json.loads(result.content or b"")
        assert data["_format"] == BUNDLE_FORMAT
        assert data["golden_copy_publish_date"] == "2026-11-07T16:00:00Z"
        assert [r["id"] for r in data["lei_records"]] == sorted(
            [TOCHTER, LAPSED, ANNULLED, MUTTER, OBERSTE]
        )
        assert len(data["relationship_records"]) == 2

    def test_bundle_is_deterministic(self) -> None:
        assert bundle() == bundle()

    def test_rate_limit_answer_is_transient(self) -> None:
        with pytest.raises(FetchError) as exc:
            make_fetcher(FakeGleif(fail_with=429)).fetch()
        assert exc.value.transient is True

    def test_not_found_is_permanent(self) -> None:
        with pytest.raises(FetchError) as exc:
            make_fetcher(FakeGleif(fail_with=404)).fetch()
        assert exc.value.transient is False


# ------------------------------------------------------- Validierung/Übersetzung
class TestParser:
    def test_translates_companies_and_relationships(self) -> None:
        ds = parse_gleif_bundle(bundle())
        assert ds.is_valid, ds.errors
        assert ds.kind == DatasetKind.ENTITIES
        assert ds.data_as_of == date(2026, 11, 7)
        companies = {c.lei: c for c in ds.records["companies"]}
        assert set(companies) == {TOCHTER, LAPSED, MUTTER, OBERSTE}  # ANNULLED fehlt
        assert companies[TOCHTER].company_key == company_key_for_lei(TOCHTER)
        assert companies[TOCHTER].name == "Muster Tochter Beispiel AG (fiktiv)"
        assert companies[OBERSTE].country == "LU"
        assert ds.records["securities"] == []  # kein ISIN-LEI-Mapping (ausgeschlossen)

        rels = {r.relationship_type: r for r in ds.records["relationships"]}
        direct = rels[RelationshipType.DIREKTE_MUTTER]
        assert (direct.child_key, direct.parent_key) == (f"lei:{TOCHTER}", f"lei:{MUTTER}")
        assert direct.verified is True  # FULLY_CORROBORATED
        ultimate = rels[RelationshipType.OBERSTE_MUTTER]
        assert ultimate.parent_key == f"lei:{OBERSTE}"
        assert ultimate.verified is False  # ENTITY_SUPPLIED_ONLY → nur Hinweis
        assert "ENTITY_SUPPLIED_ONLY" in ultimate.source

    def test_warnings_for_status_and_missing_leis(self) -> None:
        warnings = " | ".join(str(w) for w in parse_gleif_bundle(bundle()).warnings)
        assert f"LEI {LAPSED}: Registrierungsstatus LAPSED" in warnings
        assert f"LEI {ANNULLED}: Registrierungsstatus ANNULLED – nicht übernommen" in warnings
        assert f"LEI {FEHLT}: bei GLEIF nicht gefunden" in warnings

    def test_same_direct_and_ultimate_parent_is_stored_once(self) -> None:
        data = json.loads(bundle())
        for rel in data["relationship_records"]:
            rel["attributes"]["relationship"]["endNode"]["id"] = MUTTER
        ds = parse_gleif_bundle(json.dumps(data).encode())
        assert ds.is_valid, ds.errors
        (rel,) = ds.records["relationships"]
        assert rel.relationship_type == RelationshipType.DIREKTE_MUTTER
        assert "direkte und oberste Mutter" in rel.source

    @pytest.mark.parametrize(
        ("mutate", "fragment"),
        [
            (lambda d: d.update(_format="anderes"), "Unbekanntes Bündelformat"),
            (lambda d: d["lei_records"][0]["attributes"].update(lei="FIKT00GLTOCHTER00131"),
             "Ungültiger LEI"),
            (lambda d: d["lei_records"][0]["attributes"]["entity"]["legalName"].update(name=""),
             "GLEIF-LEI-Datensatz"),
            (lambda d: d.update(lei_records=[r for r in d["lei_records"] if r["id"] != MUTTER]),
             "unbekanntes Unternehmen"),
            (lambda d: d["relationship_records"].append(d["relationship_records"][0]),
             "mehrere aktive Beziehungen"),
        ],
    )
    def test_invalid_bundle_is_rejected(self, mutate, fragment: str) -> None:  # type: ignore[no-untyped-def]
        data = json.loads(bundle())
        mutate(data)
        ds = parse_gleif_bundle(json.dumps(data).encode())
        assert not ds.is_valid
        assert any(fragment in str(e) for e in ds.errors), ds.errors

    def test_inactive_relationship_is_ignored(self) -> None:
        data = json.loads(bundle())
        for rel in data["relationship_records"]:
            rel["attributes"]["relationship"]["status"] = "INACTIVE"
        ds = parse_gleif_bundle(json.dumps(data).encode())
        assert ds.is_valid
        assert ds.records["relationships"] == []


# ------------------------------------------------------------------- Update-Lauf
def gleif_config() -> SourceConfig:
    return SourceConfig(
        key="gleif_test", name="GLEIF (Test)", kind=DatasetKind.ENTITIES, publisher="GLEIF",
        fetcher="gleif_api", format="gleif_json", location=BASE,
        lei_list=str(FIX / "abfrageliste_fiktiv.txt"), interval_hours=168, max_age_days=30,
        license="CC0 1.0 Universal", license_url="https://creativecommons.org/publicdomain/zero/1.0/",
        terms_url="https://www.gleif.org/en/meta/lei-data-terms-of-use",
        license_checked_on=date(2026, 11, 7), commercial_use=CommercialUse.JA,
        redistribution=CommercialUse.JA, attribution="Quelle: GLEIF", is_fictional=False,
    )


def test_update_run_writes_versioned_gleif_data(session_factory, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    cfg = gleif_config()
    cat = Catalog(defaults=UpdateDefaults(), sources=(cfg,), criteria=())
    adapter = SourceAdapter(cfg, make_fetcher(FakeGleif()), cat.criterion_keys)
    mgr = DataUpdateManager(
        session_factory, cat, tmp_path, tmp_path / "raw", adapters={cfg.key: adapter},
        sleep=lambda _: None, clock=lambda: datetime(2026, 11, 7, 20, 0),
    )
    out = mgr.run_source(cfg.key, force=True)
    assert out.status == UpdateStatus.ERFOLGREICH, out.errors
    assert len(out.warnings) == 3
    raw = list((tmp_path / "raw" / cfg.key).glob("*.json"))
    assert len(raw) == 1  # Rohdaten-Schnappschuss als .json
    with session_factory() as s:
        assert {r.lei for r in s.scalars(select(CompanyRow))} == {TOCHTER, LAPSED, MUTTER, OBERSTE}
        assert len(s.scalars(select(RelationshipRow)).all()) == 2
        data = load_active_data(s)
    assert data.company_sources[f"lei:{TOCHTER}"] == cfg.key
    # zweiter Lauf mit gleichem Inhalt: unverändert, keine neue Version
    assert mgr.run_source(cfg.key, force=True).status == UpdateStatus.UNVERAENDERT
