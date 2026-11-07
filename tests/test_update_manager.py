"""Update-System: ein fehlgeschlagenes Update darf den letzten gültigen Stand nie verändern."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select

from transparenz.config.catalog import Catalog, SourceConfig, UpdateDefaults
from transparenz.database import writers
from transparenz.database.models import DatasetVersion, EvidenceRow, UpdateRun
from transparenz.entities.enums import CommercialUse, DatasetKind, UpdateStatus, VersionStatus
from transparenz.ingestion.adapters import SourceAdapter
from transparenz.ingestion.fetchers import FetchError, FetchResult, HttpFetcher, LocalFileFetcher
from transparenz.services.update_manager import DataUpdateManager

from conftest import SAMPLE

T0 = datetime(2026, 11, 1, 8, 0, 0)
VALID = (SAMPLE / "fiktiv_belegsammlung.csv").read_bytes()
# Gleicher Inhalt, aber eine Zeile mit ungültiger URL → ganze Datei muss abgelehnt werden
INVALID = VALID.replace(b"https://example.org/fiktiv/bel-003", b"keine-url", 1)
CHANGED = VALID.replace(b"geplante Investitionen von 2 Mrd.", b"geplante Investitionen von 3 Mrd.")


class Clock:
    def __init__(self) -> None:
        self.now = T0

    def __call__(self) -> datetime:
        return self.now


class ScriptedFetcher:
    """Liefert der Reihe nach Inhalte oder wirft Fehler."""

    def __init__(self, *steps: bytes | FetchError) -> None:
        self.steps = list(steps)
        self.calls = 0

    def fetch(self, etag: str | None = None, last_modified: str | None = None) -> FetchResult:
        self.calls += 1
        step = self.steps.pop(0) if len(self.steps) > 1 else self.steps[0]
        if isinstance(step, FetchError):
            raise step
        return FetchResult(origin="test", content=step)


def source_config(key: str = "belege") -> SourceConfig:
    return SourceConfig(
        key=key, name="Testbelege", kind=DatasetKind.EVIDENCE, publisher="Test",
        fetcher="local", format="csv", location="unused.csv", interval_hours=24,
        max_age_days=30, license="Test", commercial_use=CommercialUse.JA, is_fictional=True,
    )


@pytest.fixture
def setup(session_factory, catalog: Catalog, tmp_path: Path):  # type: ignore[no-untyped-def]
    cfg = source_config()
    cat = Catalog(defaults=UpdateDefaults(max_attempts=3, backoff_seconds=1.0),
                  sources=(cfg,), criteria=catalog.criteria)
    clock = Clock()
    sleeps: list[float] = []

    def make(fetcher) -> DataUpdateManager:  # type: ignore[no-untyped-def]
        adapter = SourceAdapter(cfg, fetcher, cat.criterion_keys)
        return DataUpdateManager(session_factory, cat, tmp_path, tmp_path / "raw",
                                 adapters={cfg.key: adapter}, sleep=sleeps.append, clock=clock)

    return make, clock, sleeps, session_factory, tmp_path


def snapshot(session_factory) -> tuple[list[tuple], list[tuple]]:  # type: ignore[no-untyped-def]
    """Vollständiger Abzug der Versionen und Sachverhalte zum Vergleich vorher/nachher."""
    with session_factory() as s:
        versions = [(v.id, v.status, v.content_hash, v.record_count)
                    for v in s.scalars(select(DatasetVersion).order_by(DatasetVersion.id))]
        rows = [(e.id, e.dataset_version_id, e.evidence_id, e.description, e.source_url)
                for e in s.scalars(select(EvidenceRow).order_by(EvidenceRow.id))]
    return versions, rows


def active(session_factory) -> list[DatasetVersion]:  # type: ignore[no-untyped-def]
    with session_factory() as s:
        return list(s.scalars(select(DatasetVersion).where(
            DatasetVersion.status == VersionStatus.ACTIVE.value)))


class TestHappyPath:
    def test_initial_import_then_unchanged_then_skipped(self, setup) -> None:  # type: ignore[no-untyped-def]
        make, clock, _, sf, _ = setup
        mgr = make(ScriptedFetcher(VALID))
        out = mgr.run_source("belege")
        assert out.status == UpdateStatus.ERFOLGREICH
        assert out.warnings  # absichtliches Duplikat in den Beispieldaten
        assert len(active(sf)) == 1

        clock.now += timedelta(hours=1)
        assert mgr.run_source("belege").status == UpdateStatus.UEBERSPRUNGEN
        out = mgr.run_source("belege", force=True)
        assert out.status == UpdateStatus.UNVERAENDERT
        assert len(snapshot(sf)[0]) == 1  # keine neue Version

    def test_new_content_creates_new_version_and_supersedes_old(self, setup) -> None:  # type: ignore[no-untyped-def]
        make, clock, _, sf, _ = setup
        mgr = make(ScriptedFetcher(VALID, CHANGED))
        first = mgr.run_source("belege")
        clock.now += timedelta(days=2)
        second = mgr.run_source("belege")
        assert second.status == UpdateStatus.ERFOLGREICH
        versions, _ = snapshot(sf)
        assert [v[1] for v in versions] == ["superseded", "active"]
        assert active(sf)[0].id == second.version_id != first.version_id

    def test_raw_snapshot_is_kept(self, setup) -> None:  # type: ignore[no-untyped-def]
        make, *_ , tmp = setup
        make(ScriptedFetcher(VALID)).run_source("belege")
        files = list((tmp / "raw" / "belege").glob("*.csv"))
        assert len(files) == 1 and files[0].read_bytes() == VALID


class TestFailuresKeepLastValidState:
    def test_invalid_data_is_rejected_and_state_unchanged(self, setup) -> None:  # type: ignore[no-untyped-def]
        make, clock, _, sf, tmp = setup
        mgr = make(ScriptedFetcher(VALID, INVALID))
        mgr.run_source("belege")
        before = snapshot(sf)
        clock.now += timedelta(days=2)
        out = mgr.run_source("belege")
        assert out.status == UpdateStatus.FEHLGESCHLAGEN
        assert any("source_url" in e for e in out.errors)
        assert snapshot(sf) == before  # Datenbestand exakt unverändert
        rejected = list((tmp / "raw" / "belege" / "abgelehnt").glob("*.csv"))
        assert len(rejected) == 1  # nachvollziehbar aufbewahrt
        with sf() as s:
            run = s.scalars(select(UpdateRun).order_by(UpdateRun.id.desc())).first()
            assert run is not None and run.status == "fehlgeschlagen"
            assert json.loads(run.errors_json)

    def test_failure_while_writing_rolls_back(self, setup, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        make, clock, _, sf, _ = setup
        mgr = make(ScriptedFetcher(VALID, CHANGED))
        mgr.run_source("belege")
        before = snapshot(sf)

        def boom(session, version_id, parsed):  # type: ignore[no-untyped-def]
            session.add(EvidenceRow(dataset_version_id=version_id, evidence_id="HALB",
                                    company_name="x", criterion="kohle", description="x",
                                    evidence_type="vorwurf", proceeding_status="laufend",
                                    publisher="x", publisher_type="ngo", source_title="x",
                                    source_url="https://x", published_date=T0.date(),
                                    verification_level="ungeprueft"))
            session.flush()
            raise RuntimeError("Festplatte voll (simuliert)")

        monkeypatch.setattr("transparenz.services.update_manager.write_dataset", boom)
        clock.now += timedelta(days=2)
        out = mgr.run_source("belege")
        assert out.status == UpdateStatus.FEHLGESCHLAGEN
        assert "Rollback" in out.message
        assert snapshot(sf) == before  # keine halb geschriebenen Daten, alte Version aktiv
        assert writers.write_dataset is not boom

    def test_transient_error_is_retried(self, setup) -> None:  # type: ignore[no-untyped-def]
        make, _, sleeps, *_ = setup
        fetcher = ScriptedFetcher(FetchError("Timeout", transient=True), VALID)
        out = make(fetcher).run_source("belege")
        assert out.status == UpdateStatus.ERFOLGREICH
        assert out.attempts == 2 and sleeps == [1.0]

    def test_retries_are_limited(self, setup) -> None:  # type: ignore[no-untyped-def]
        make, _, sleeps, sf, _ = setup
        fetcher = ScriptedFetcher(FetchError("HTTP 503", transient=True))
        out = make(fetcher).run_source("belege")
        assert out.status == UpdateStatus.FEHLGESCHLAGEN
        assert fetcher.calls == 3 and sleeps == [1.0, 2.0]  # exponentielles Warten
        assert active(sf) == []

    def test_permanent_error_is_not_retried(self, setup) -> None:  # type: ignore[no-untyped-def]
        make, _, sleeps, *_ = setup
        fetcher = ScriptedFetcher(FetchError("HTTP 404", transient=False))
        out = make(fetcher).run_source("belege")
        assert out.status == UpdateStatus.FEHLGESCHLAGEN
        assert fetcher.calls == 1 and sleeps == []

    def test_missing_local_file(self, tmp_path: Path) -> None:
        with pytest.raises(FetchError) as exc:
            LocalFileFetcher(tmp_path / "fehlt.csv").fetch()
        assert exc.value.transient is False


class TestFreshness:
    def test_stale_when_data_older_than_max_age(self, setup) -> None:  # type: ignore[no-untyped-def]
        make, *_ = setup
        mgr = make(ScriptedFetcher(VALID))
        assert mgr.freshness()[0].is_stale  # noch kein gültiger Stand
        mgr.run_source("belege")
        f = mgr.freshness()[0]
        # Datenstand der Beispieldaten: 01.10.2026; Uhr: 01.11.2026; max. 30 Tage
        assert f.age_days == 31 and f.is_stale
        assert f.next_due_at == T0 + timedelta(hours=24)


class TestHttpFetcher:
    def test_conditional_request_and_status_codes(self) -> None:
        seen: list[dict[str, str]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(dict(request.headers))
            path = request.url.path
            if path == "/ok":
                if request.headers.get("if-none-match") == '"v1"':
                    return httpx.Response(304)
                return httpx.Response(200, content=b"daten", headers={"ETag": '"v1"'})
            if path == "/busy":
                return httpx.Response(503)
            return httpx.Response(404)

        client = httpx.Client(transport=httpx.MockTransport(handler))

        def f(path: str) -> HttpFetcher:
            return HttpFetcher(f"https://quelle.test{path}", timeout=5, user_agent="test-agent",
                               client=client)

        first = f("/ok").fetch()
        assert first.content == b"daten" and first.etag == '"v1"'
        second = f("/ok").fetch(etag=first.etag)
        assert second.not_modified and second.content is None
        assert seen[0]["user-agent"] == "test-agent"
        with pytest.raises(FetchError) as busy:
            f("/busy").fetch()
        assert busy.value.transient
        with pytest.raises(FetchError) as missing:
            f("/missing").fetch()
        assert not missing.value.transient
