"""Synthetic fixtures only: licensing, raw integrity and identifier-only joins."""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import date
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select

from transparenz.config.catalog import Catalog, UpdateDefaults, load_catalog
from transparenz.config.licensing import license_block_reasons
from transparenz.config.settings import CONFIG_DIR
from transparenz.database.models import DatasetVersion, UpdateRun
from transparenz.entities.enums import UpdateStatus
from transparenz.entities.identifiers import make_isin, make_lei
from transparenz.ingestion.external import (
    FORMAT,
    ExternalFetcher,
    RawClient,
    build_external_adapter,
    encoded,
    normalize_uid,
    parse_external,
)
from transparenz.services.swiss_foundation import foundation_lock, resolve_companies
from transparenz.services.update_manager import DataUpdateManager

ROOT = Path(__file__).resolve().parents[1]


def config(key="gleif_ch"):
    return load_catalog(CONFIG_DIR / "swiss_sources.toml", CONFIG_DIR / "criteria.toml").source(key)


def original(tmp_path, cfg, body, total=None):
    raw = encoded(body)
    digest = hashlib.sha256(raw).hexdigest()
    folder = tmp_path / "data/raw/external" / cfg.key / "objects"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{digest}.json").write_bytes(raw)
    return encoded({"format": FORMAT, "source_key": cfg.key, "mode": cfg.external_mode,
                    "data_as_of": "2026-11-07", "coverage": {"api_total": total},
                    "pages": [{"path": f"objects/{digest}.json", "sha256": digest,
                               "bytes": len(raw), "url": "https://example.org/fiktiv"}]})


def gleif_records():
    body = json.loads((ROOT / "tests/fixtures/gleif/api_lei_records_abfrage.json").read_bytes())
    # Avoid the deliberately invalid/cancelled fixture; vary one synthetic record.
    first = body["data"][0]
    fund = copy.deepcopy(first)
    fund["id"] = fund["attributes"]["lei"] = make_lei("FIKT00FUND".ljust(18, "0"))
    fund["attributes"]["entity"]["category"] = "FUND"
    return {"data": [first, fund]}


def test_all_swiss_sources_have_five_cleared_rights():
    cat = load_catalog(CONFIG_DIR / "swiss_sources.toml", CONFIG_DIR / "criteria.toml")
    for cfg in cat.sources:
        assert license_block_reasons(cfg, date(2026, 11, 8)) == []
        assert cfg.attribution


def test_uid_checksum_and_format():
    # Constructed test identifier; no claim about a real registered business.
    assert normalize_uid("CHE-123.456.788") == "CHE123456788"
    assert normalize_uid("CHE123456789") is None
    assert normalize_uid("CH123456788") is None


def test_fund_is_not_company_or_holding(tmp_path):
    cfg = config()
    parsed = parse_external(original(tmp_path, cfg, gleif_records(), 2), cfg, tmp_path)
    assert parsed.is_valid, parsed.errors
    assert len(parsed.records["companies"]) == 1
    assert len(parsed.extra["funds"]) == 1
    assert parsed.extra["funds"][0]["isin"] is None
    assert not parsed.records["securities"]
    assert not parsed.records["relationships"]
    assert all(not x["verified"] for x in parsed.extra["unresolved_relationships"])


def test_raw_hash_failure_rejects_entire_version(tmp_path):
    cfg = config()
    manifest = original(tmp_path, cfg, gleif_records(), 2)
    entry = json.loads(manifest)["pages"][0]
    (tmp_path / "data/raw/external" / cfg.key / entry["path"]).write_bytes(b"tampered")
    assert not parse_external(manifest, cfg, tmp_path).is_valid


def test_path_traversal_rejected(tmp_path):
    cfg = config()
    manifest = json.loads(original(tmp_path, cfg, gleif_records(), 2))
    manifest["pages"][0]["path"] = "../../../../outside.json"
    parsed = parse_external(encoded(manifest), cfg, tmp_path)
    assert not parsed.is_valid
    assert "ausserhalb" in str(parsed.errors)


def test_invalid_lei_is_quarantined_and_never_imported(tmp_path):
    cfg = config()
    body = gleif_records()
    bad = copy.deepcopy(body["data"][0])
    bad["id"] = bad["attributes"]["lei"] = "FIKT00INVALID00000000"
    body["data"].append(bad)
    parsed = parse_external(original(tmp_path, cfg, body, 3), cfg, tmp_path)
    assert parsed.is_valid, parsed.errors
    assert len(parsed.extra["quarantined_identifiers"]) == 1
    assert len(parsed.records["companies"]) == 1


def wikidata_binding(qid, *, isin=None, lei=None, ticker_qualifier=None,
                      exchange="http://www.wikidata.org/entity/Q661834",
                      country="http://www.wikidata.org/entity/Q39", label_de=None):
    binding = {"item": {"value": f"http://www.wikidata.org/entity/{qid}"}}
    for key, value in (("isin", isin), ("lei", lei), ("tickerQ", ticker_qualifier),
                      ("exchange", exchange), ("country", country), ("labelDe", label_de)):
        if value is not None:
            binding[key] = {"value": value}
    return binding


def test_wikidata_security_candidate_and_shared_lei_quarantine(tmp_path):
    cfg = config("wikidata_ch")
    shared_lei = make_lei("FIKT00SHARED000001")
    isin_q1 = make_isin("ZZ00000000A")
    body = {"results": {"bindings": [
        wikidata_binding("Q1", isin=isin_q1, lei="549300U41AUUVOAAOB37",
                         ticker_qualifier="ROG", label_de="Roche Holding (fiktiv)"),
        wikidata_binding("Q2", isin=make_isin("ZZ00000000B"), lei=shared_lei,
                         label_de="Alpha AG (fiktiv)"),
        wikidata_binding("Q3", isin=make_isin("ZZ00000000C"), lei=shared_lei,
                         label_de="Beta AG (fiktiv)"),
    ]}}
    parsed = parse_external(original(tmp_path, cfg, body, None), cfg, tmp_path)
    assert parsed.is_valid, parsed.errors
    companies = {c.company_key: c for c in parsed.records["companies"]}
    assert set(companies) == {"wikidata:Q1"}
    attributes = {a["company_key"]: a for a in parsed.extra["company_attributes"]}
    assert attributes["wikidata:Q1"]["claims"]["P249"] == ["ROG"]
    candidates = {c["isin"]: c for c in parsed.extra["security_candidates"]}
    assert set(candidates) == {isin_q1}
    assert candidates[isin_q1]["mapping_status"] == "unverified_company_level_claim"
    conflicts = parsed.extra["identifier_conflicts"]
    assert {c["wikidata_id"] for c in conflicts} == {"Q2", "Q3"}
    assert all(c["reason"] == "lei_shared_by_multiple_wikidata_items" for c in conflicts)


def row(key, name="Beispiel AG (fiktiv)", lei=None, uid=None):
    return {"company_key": key, "name": name, "lei": lei, "uid": uid,
            "country": "CH", "source_key": key.split(":")[0]}


def test_exact_uid_merge_and_no_name_merges():
    lei = make_lei("FIKT00COMPANY".ljust(17, "0") + "1")
    records = [row(f"lei:{lei}", lei=lei, uid="CHE123456788"),
               row("uid:CHE123456788", uid="CHE123456788"),
               row("wikidata:QFAKE")]
    companies, conflicts, duplicates = resolve_companies(records)
    assert len(companies) == 2
    assert not conflicts
    assert len(duplicates) == 1
    assert len(next(c for c in companies if c["lei"])["source_records"]) == 2


def test_conflicting_uid_does_not_join_any_lei():
    a = make_lei("FIKT00COMPANY".ljust(17, "0") + "1")
    b = make_lei("FIKT00COMPANY".ljust(17, "0") + "2")
    companies, conflicts, _ = resolve_companies([
        row(f"lei:{a}", lei=a, uid="CHE123456788"),
        row(f"lei:{b}", lei=b, uid="CHE123456788"),
        row("uid:CHE123456788", uid="CHE123456788")])
    assert len(companies) == 3
    assert len(conflicts) == 1
    assert all(c["identity_status"] == "identifier_conflict" for c in companies)


def test_cache_preserves_original_and_avoids_second_request(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, content=b'{"original": true}', headers={"ETag": "one"})

    cfg = config()
    client = httpx.Client(transport=httpx.MockTransport(handler))
    c = RawClient(cfg, tmp_path, "test", client=client,
                  sleep=lambda _: None)
    first = c.get(cfg.location)
    second = c.get(cfg.location)
    assert len(calls) == 1
    assert first == second
    assert (c.folder / first["path"]).read_bytes() == b'{"original": true}'
    assert first["sha256"] == hashlib.sha256(b'{"original": true}').hexdigest()
    assert first["license"]["storage"] == "ja"


def test_http_403_is_not_retried(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(403)

    c = RawClient(config("wikidata_ch"), tmp_path, "test",
                  client=httpx.Client(transport=httpx.MockTransport(handler)), sleep=lambda _: None)
    with pytest.raises(Exception, match="HTTP 403"):
        c.get(config("wikidata_ch").location)
    assert len(calls) == 1


def test_failed_external_update_keeps_last_valid_version(session_factory, tmp_path):
    cfg = config()
    cat = Catalog(defaults=UpdateDefaults(), sources=(cfg,), criteria=())
    adapter = build_external_adapter(cfg, cat, tmp_path, "test")
    manifest = original(tmp_path, cfg, gleif_records(), 2)

    class Fetcher:
        content = manifest

        def fetch(self, **kwargs):
            from transparenz.ingestion.fetchers import FetchResult
            return FetchResult(origin="synthetic", content=self.content)

    fetcher = Fetcher()
    adapter.fetcher = fetcher
    manager = DataUpdateManager(session_factory, cat, tmp_path, tmp_path / "manifests",
                                adapters={cfg.key: adapter})
    good = manager.run_source(cfg.key, force=True)
    assert good.status == UpdateStatus.ERFOLGREICH
    fetcher.content = b"{}"
    bad = manager.run_source(cfg.key, force=True)
    assert bad.status == UpdateStatus.FEHLGESCHLAGEN
    with session_factory() as session:
        versions = session.scalars(select(DatasetVersion)).all()
        assert len(versions) == 1
        assert versions[0].id == good.version_id
        assert versions[0].status == "active"
        assert len(session.scalars(select(UpdateRun)).all()) == 2


def test_cursor_pagination_detects_missing_records(tmp_path, monkeypatch):
    cfg = config()
    body = {"meta": {"pagination": {"total": 3},
                     "goldenCopy": {"publishDate": "2026-11-07T00:00:00Z"}},
            "data": [{"id": "synthetic-one"}], "links": {}}
    monkeypatch.setattr(RawClient, "get", lambda *a, **kw: {})
    monkeypatch.setattr(RawClient, "body", lambda *a: body)
    with pytest.raises(Exception, match="unvollständig"):
        ExternalFetcher(cfg, tmp_path, "test").fetch()


def test_zefix_multilingual_names_are_one_identity(tmp_path):
    cfg = config("zefix_lindas")
    rows = []
    for name, language in (("Beispiel AG (fiktiv)", "de"),
                           ("Exemple SA (fictif)", "fr")):
        rows.append({"company": {"value": "https://example.org/register/fiktiv/1"},
                     "name": {"value": name, "xml:lang": language},
                     "uid": {"value": "CHE123456788"},
                     "legalForm": {"value": "https://example.org/form/AG"}})
    parsed = parse_external(original(tmp_path, cfg, {"results": {"bindings": rows}}), cfg,
                            tmp_path)
    assert parsed.is_valid, parsed.errors
    assert len(parsed.records["companies"]) == 1
    assert len(parsed.extra["company_attributes"][0]["name_variants"]) == 2
    assert parsed.records["companies"][0].name == "Beispiel AG (fiktiv)"


def test_unchanged_external_update_does_not_create_version(session_factory, tmp_path):
    cfg = config()
    cat = Catalog(defaults=UpdateDefaults(), sources=(cfg,), criteria=())
    adapter = build_external_adapter(cfg, cat, tmp_path, "test")
    manifest = original(tmp_path, cfg, gleif_records(), 2)

    class Fetcher:
        def fetch(self, **kwargs):
            from transparenz.ingestion.fetchers import FetchResult
            return FetchResult(origin="synthetic", content=manifest)

    adapter.fetcher = Fetcher()
    manager = DataUpdateManager(session_factory, cat, tmp_path, tmp_path / "manifests",
                                adapters={cfg.key: adapter})
    first = manager.run_source(cfg.key, force=True)
    second = manager.run_source(cfg.key, force=True)
    assert first.status == UpdateStatus.ERFOLGREICH
    assert second.status == UpdateStatus.UNVERAENDERT
    assert first.version_id == second.version_id


def test_unexpected_host_never_requested(tmp_path):
    c = RawClient(config(), tmp_path, "test")
    try:
        with pytest.raises(Exception, match="Unerwarteter Host"):
            c.get("https://example.org/untrusted-next-page")
    finally:
        c.close()


def test_lock_rejects_simultaneous_exports_and_releases_after_error(tmp_path):
    with (foundation_lock(tmp_path), pytest.raises(RuntimeError, match="läuft bereits"),
          foundation_lock(tmp_path)):
        pytest.fail("A second writer must not run")
    with pytest.raises(ValueError), foundation_lock(tmp_path):
        raise ValueError("synthetic failure")
    with foundation_lock(tmp_path):
        pass


def test_duplicate_uid_for_distinct_register_ids_is_quarantined(tmp_path):
    cfg = config("zefix_lindas")
    rows = [{"company": {"value": f"https://example.org/fiktiv/{n}"},
             "name": {"value": f"Beispiel {n} (fiktiv)"},
             "uid": {"value": "CHE123456788"},
             "legalForm": {"value": "https://example.org/form/AG"}} for n in range(2)]
    # Keep an independent valid entity so check_entities can assess the rest.
    rows.append({"company": {"value": "https://example.org/fiktiv/other"},
                 "name": {"value": "Andere Beispiel AG (fiktiv)"},
                 "uid": {"value": "CHE100000006"},
                 "legalForm": {"value": "https://example.org/form/AG"}})
    parsed = parse_external(original(tmp_path, cfg, {"results": {"bindings": rows}}), cfg,
                            tmp_path)
    assert len(parsed.extra["identifier_conflicts"]) == 1
    assert all(c.company_key != "uid:CHE123456788" for c in parsed.records["companies"])
    assert not parsed.is_valid  # two of three records exceeds the quarantine threshold
    assert any(c.company_key == "uid:CHE100000006" for c in parsed.records["companies"])


def test_interrupted_import_is_logged_without_losing_active_version(session_factory, tmp_path):
    cfg = config()
    cat = Catalog(defaults=UpdateDefaults(), sources=(cfg,), criteria=())
    adapter = build_external_adapter(cfg, cat, tmp_path, "test")
    manifest = original(tmp_path, cfg, gleif_records(), 2)

    class Fetcher:
        interrupted = False

        def fetch(self, **kwargs):
            from transparenz.ingestion.fetchers import FetchResult
            if self.interrupted:
                raise KeyboardInterrupt
            return FetchResult(origin="synthetic", content=manifest)

    fetcher = Fetcher()
    adapter.fetcher = fetcher
    manager = DataUpdateManager(session_factory, cat, tmp_path, tmp_path / "manifests",
                                adapters={cfg.key: adapter})
    good = manager.run_source(cfg.key, force=True)
    fetcher.interrupted = True
    with pytest.raises(KeyboardInterrupt):
        manager.run_source(cfg.key, force=True)
    with session_factory() as session:
        assert session.get(DatasetVersion, good.version_id).status == "active"
        runs = session.scalars(select(UpdateRun).order_by(UpdateRun.id)).all()
        assert runs[-1].status == UpdateStatus.FEHLGESCHLAGEN
        assert runs[-1].finished_at is not None
