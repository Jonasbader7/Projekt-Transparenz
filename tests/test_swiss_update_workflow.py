"""Default updates stay cheap and manual access failures stay visible."""
from __future__ import annotations

import json
from dataclasses import replace

import pytest

from test_swiss_foundation import gleif_records, original
from transparenz.config.settings import get_settings
from transparenz.entities.enums import UpdateStatus
from transparenz.ingestion.adapters import build_adapter
from transparenz.ingestion.fetchers import FetchResult
from transparenz.services import swiss_foundation as swiss
from transparenz.services.update_manager import UpdateOutcome


@pytest.fixture
def context(tmp_path):
    ctx = swiss.create_swiss_context(replace(get_settings(), project_root=tmp_path))
    try:
        yield ctx
    finally:
        ctx.engine.dispose()


def import_synthetic(ctx, tmp_path, body=None):
    cfg = ctx.catalog.source("gleif_ch")
    content = original(tmp_path, cfg, body or gleif_records(), 2)
    adapter = build_adapter(cfg, ctx.catalog, tmp_path, "synthetic")

    class Fetcher:
        def fetch(self, **kwargs):
            return FetchResult(origin="https://example.org/fiktiv", content=content)

    adapter.fetcher = Fetcher()
    ctx.updates._adapters[cfg.key] = adapter
    outcome = ctx.updates.run_source(cfg.key, force=True)
    assert outcome.status == UpdateStatus.ERFOLGREICH
    return adapter


def test_unchanged_export_keeps_generation_and_does_not_parse(context, tmp_path, monkeypatch):
    adapter = import_synthetic(context, tmp_path)
    before = swiss.export_foundation(context)
    output = context.settings.processed_dir / "swiss"
    pointer = (output / "current.json").read_bytes()
    generation = output / json.loads(pointer)["generation"]
    report_bytes = (generation / "quality_report.json").read_bytes()
    skipped = context.updates.run_source("gleif_ch")
    assert skipped.status == UpdateStatus.UEBERSPRUNGEN
    monkeypatch.setattr(adapter, "parse", lambda _: pytest.fail("unchanged data must not reparse"))
    after = swiss.export_foundation(context)
    assert after["reused_export"] is True
    assert after["counts"] == before["counts"]
    assert (output / "current.json").read_bytes() == pointer
    assert (generation / "quality_report.json").read_bytes() == report_bytes
    assert len(list((output / "generations").iterdir())) == 1
    status = json.loads((output / "latest_status.json").read_bytes())
    assert status["sources"]["gleif_ch"]["latest_update_status"] == "uebersprungen"
    assert status["sources"]["wikidata_ch"]["enabled"] is True


def test_new_data_version_rebuilds_export(context, tmp_path):
    import_synthetic(context, tmp_path)
    swiss.export_foundation(context)
    output = context.settings.processed_dir / "swiss"
    old_pointer = (output / "current.json").read_bytes()
    body = gleif_records()
    body["data"][0]["attributes"]["entity"]["legalName"]["name"] = "Neue Musterfirma (fiktiv)"
    import_synthetic(context, tmp_path, body)
    after = swiss.export_foundation(context)
    assert not after.get("reused_export")
    assert (output / "current.json").read_bytes() != old_pointer
    generation = output / json.loads((output / "current.json").read_bytes())["generation"]
    companies = json.loads((generation / "companies.json").read_bytes())
    assert companies[0]["name"] == "Neue Musterfirma (fiktiv)"


@pytest.mark.parametrize("cause", ["schema", "missing_file", "explicit_rebuild"])
def test_export_rebuilds_when_reuse_is_unsafe_or_explicit(context, tmp_path, monkeypatch, cause):
    adapter = import_synthetic(context, tmp_path)
    swiss.export_foundation(context)
    output = context.settings.processed_dir / "swiss"
    generation = output / json.loads((output / "current.json").read_bytes())["generation"]
    if cause == "schema":
        monkeypatch.setattr(swiss, "EXPORT_SCHEMA_VERSION", swiss.EXPORT_SCHEMA_VERSION + 1)
    elif cause == "missing_file":
        (generation / "funds.json").unlink()
    parse = adapter.parse
    calls = []

    def tracked_parse(content):
        calls.append(True)
        return parse(content)

    monkeypatch.setattr(adapter, "parse", tracked_parse)
    swiss.export_foundation(context, reuse_existing=cause != "explicit_rebuild")
    assert calls
    assert len(list((output / "generations").iterdir())) == 2


def test_default_skips_disabled_source_but_manual_attempt_still_fails(
    context, monkeypatch, capsys
):
    # No real swiss source is disabled any more (wikidata_ch's HTTP 403 turned out to be a
    # query bug, now fixed); exercise the skip logic with a synthetic disabled source.
    disabled = tuple(
        s.model_copy(update={"enabled": False, "disabled_reason": "HTTP 403"})
        if s.key == "swissprtr" else s for s in context.catalog.sources)
    monkeypatch.setattr(context, "catalog", context.catalog.model_copy(
        update={"sources": disabled}))
    calls = []
    monkeypatch.setattr(swiss, "create_swiss_context", lambda: context)

    def run_source(key, **kwargs):
        calls.append(key)
        if key == "swissprtr":
            return UpdateOutcome(key, UpdateStatus.FEHLGESCHLAGEN, "HTTP 403", errors=["HTTP 403"])
        return UpdateOutcome(key, UpdateStatus.UEBERSPRUNGEN, "Noch nicht fällig")

    monkeypatch.setattr(context.updates, "run_source", run_source)
    monkeypatch.setattr(swiss, "export_foundation", lambda *a, **kw: {"counts": {}})
    _, failed = swiss._update_foundation(False, None, False)
    assert not failed
    assert set(calls) == {"gleif_ch", "zefix_lindas", "wikidata_ch"}
    assert "swissprtr: deaktiviert: HTTP 403" in capsys.readouterr().out
    calls.clear()
    _, failed = swiss._update_foundation(False, "swissprtr", False)
    assert failed
    assert calls == ["swissprtr"]


def test_export_only_explicitly_requests_full_rebuild(context, monkeypatch):
    monkeypatch.setattr(swiss, "create_swiss_context", lambda: context)
    monkeypatch.setattr(context.updates, "run_source", lambda *a, **kw: pytest.fail("no fetch"))
    calls = []

    def export(ctx, **kwargs):
        calls.append(kwargs)
        return {"counts": {}}

    monkeypatch.setattr(swiss, "export_foundation", export)
    swiss._update_foundation(False, None, True)
    assert calls == [{"reuse_existing": False}]
