"""Snapshot replacement must never activate malformed/empty downloads."""
import importlib.util
import json
from pathlib import Path

import httpx
import pytest


@pytest.fixture
def downloader(tmp_path, monkeypatch):
    path = Path(__file__).parents[1] / "scripts/download_global_candidates.py"
    spec = importlib.util.spec_from_file_location("audit_download", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "DATA", tmp_path / "data")
    return module


def response_client(monkeypatch, module, payload):
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    client_type = httpx.Client
    monkeypatch.setattr(module.httpx, "Client", lambda **kwargs: client_type(
        transport=transport, **kwargs))


def test_empty_download_keeps_previous_snapshot(downloader, monkeypatch):
    pointer = downloader.ROOT / "data/raw/external/wikidata_global/current.json"
    pointer.parent.mkdir(parents=True)
    pointer.write_text('{"previous": true}', encoding="utf-8")
    response_client(monkeypatch, downloader, {"results": {"bindings": []}})
    with pytest.raises(ValueError, match="Empty"):
        downloader.download("wikidata_global", force=True)
    assert json.loads(pointer.read_text()) == {"previous": True}


def test_new_snapshot_archives_original_and_respects_interval(downloader, monkeypatch):
    row = {k: {"value": value} for k, value in {
        "item": "https://www.wikidata.org/entity/Q1", "name": "Fictional test company",
        "exchange": "https://www.wikidata.org/entity/Q2", "ticker": "FIKT"}.items()}
    response_client(monkeypatch, downloader, {"results": {"bindings": [row]}})
    result = downloader.download("wikidata_global", force=True)
    assert result["rows"] == 1
    assert (downloader.DATA / result["file"]).is_file()
    assert result["complete_world"] is False
    assert downloader.download("wikidata_global")["status"] == "not_due"


def test_invalid_cvm_schema_not_activated(downloader, monkeypatch):
    response_client(monkeypatch, downloader, {"error": "not csv"})
    with pytest.raises(ValueError, match="schema"):
        downloader.download("cvm_companies", force=True)
    assert not (downloader.ROOT / "data/raw/external/cvm_companies/current.json").exists()
