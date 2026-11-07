"""Lizenzsperre: Echte Quellen ohne geprüfte, kommerziell nutzbare Lizenz werden nie abgerufen."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from transparenz.config.catalog import Catalog, SourceConfig, UpdateDefaults
from transparenz.config.licensing import (
    LICENSE_REVIEW_MAX_DAYS,
    SourceBlockedError,
    is_license_cleared,
    license_block_reasons,
)
from transparenz.config.settings import get_settings
from transparenz.database.models import DatasetVersion, UpdateRun
from transparenz.entities.enums import CommercialUse, DatasetKind, UpdateStatus
from transparenz.ingestion.adapters import SourceAdapter
from transparenz.ingestion.fetchers import FetchResult
from transparenz.ingestion.gleif import read_lei_list
from transparenz.services.update_manager import DataUpdateManager

from conftest import ROOT

TODAY = date(2026, 11, 7)


def real_source(**overrides: object) -> SourceConfig:
    values: dict[str, object] = {
        "key": "echte_quelle", "name": "Echte Quelle", "kind": DatasetKind.EVIDENCE,
        "publisher": "Behörde", "fetcher": "http", "format": "csv",
        "location": "https://example.org/daten.csv", "interval_hours": 24, "max_age_days": 30,
        "license": "CC0 1.0", "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "terms_url": "https://example.org/terms", "license_checked_on": TODAY,
        "commercial_use": CommercialUse.JA, "redistribution": CommercialUse.JA,
        "is_fictional": False,
    }
    values.update(overrides)
    return SourceConfig(**values)  # type: ignore[arg-type]


class TestBlockReasons:
    def test_fully_registered_source_is_cleared(self) -> None:
        assert license_block_reasons(real_source(), TODAY) == []
        assert is_license_cleared(real_source(), TODAY)

    @pytest.mark.parametrize(
        ("overrides", "fragment"),
        [
            ({"commercial_use": CommercialUse.UNKLAR}, "kommerzielle Nutzung"),
            ({"commercial_use": CommercialUse.NEIN}, "kommerzielle Nutzung"),
            ({"redistribution": CommercialUse.UNKLAR}, "Weiterveröffentlichung"),
            ({"redistribution": CommercialUse.NEIN}, "Weiterveröffentlichung"),
            ({"terms_url": None}, "terms_url"),
            ({"license": "  "}, "Lizenzbezeichnung"),
            ({"license_checked_on": None}, "Prüfdatum"),
            ({"license_checked_on": date(2026, 12, 1)}, "Zukunft"),
        ],
    )
    def test_each_missing_piece_blocks(self, overrides: dict[str, object], fragment: str) -> None:
        reasons = license_block_reasons(real_source(**overrides), TODAY)
        assert len(reasons) == 1
        assert fragment in reasons[0]

    def test_redistribution_defaults_to_unclear(self) -> None:
        cfg = real_source()
        data = cfg.model_dump()
        data.pop("redistribution")
        assert not is_license_cleared(SourceConfig(**data), TODAY)

    def test_review_expires_after_a_year(self) -> None:
        checked = date(2025, 11, 7)
        assert (TODAY - checked).days == LICENSE_REVIEW_MAX_DAYS
        assert is_license_cleared(real_source(license_checked_on=checked), TODAY)
        old = real_source(license_checked_on=date(2025, 11, 6))
        assert "Tage alt" in license_block_reasons(old, TODAY)[0]

    def test_fictional_sources_are_exempt(self) -> None:
        cfg = real_source(is_fictional=True, commercial_use=CommercialUse.UNKLAR,
                          terms_url=None, license_checked_on=None)
        assert is_license_cleared(cfg, TODAY)


class CountingFetcher:
    def __init__(self) -> None:
        self.calls = 0

    def fetch(self, etag: str | None = None, last_modified: str | None = None) -> FetchResult:
        self.calls += 1
        return FetchResult(origin="test", content=b"")


def manager(session_factory, tmp_path: Path, cfg: SourceConfig, fetcher):  # type: ignore[no-untyped-def]
    cat = Catalog(defaults=UpdateDefaults(), sources=(cfg,), criteria=())
    adapter = SourceAdapter(cfg, fetcher, cat.criterion_keys)
    return DataUpdateManager(
        session_factory, cat, tmp_path, tmp_path / "raw", adapters={cfg.key: adapter},
        sleep=lambda _: None, clock=lambda: datetime(2026, 11, 7, 12, 0),
    )


class TestUpdateManagerBlocks:
    def test_blocked_source_is_not_fetched_and_run_is_logged(
        self, session_factory, tmp_path: Path
    ) -> None:  # type: ignore[no-untyped-def]
        fetcher = CountingFetcher()
        cfg = real_source(redistribution=CommercialUse.UNKLAR)
        out = manager(session_factory, tmp_path, cfg, fetcher).run_source(cfg.key, force=True)
        assert out.status == UpdateStatus.GESPERRT
        assert fetcher.calls == 0
        assert any("Weiterveröffentlichung" in e for e in out.errors)
        assert not (tmp_path / "raw").exists()
        with session_factory() as s:
            assert s.scalars(select(DatasetVersion)).all() == []
            run = s.scalars(select(UpdateRun)).one()
            assert run.status == UpdateStatus.GESPERRT.value
            assert "Weiterveröffentlichung" in run.errors_json

    def test_dry_run_is_blocked_too(self, session_factory, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
        fetcher = CountingFetcher()
        cfg = real_source(commercial_use=CommercialUse.UNKLAR)
        with pytest.raises(SourceBlockedError, match="kommerzielle Nutzung"):
            manager(session_factory, tmp_path, cfg, fetcher).validate_source(cfg.key)
        assert fetcher.calls == 0

    def test_cleared_source_is_fetched(self, session_factory, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
        fetcher = CountingFetcher()
        cfg = real_source()
        out = manager(session_factory, tmp_path, cfg, fetcher).run_source(cfg.key, force=True)
        assert fetcher.calls == 1
        assert out.status == UpdateStatus.FEHLGESCHLAGEN  # leere Datei – aber abgerufen


def test_disabled_source_is_not_reported_as_stale(session_factory, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    cfg = real_source(enabled=False)
    (fresh,) = manager(session_factory, tmp_path, cfg, CountingFetcher()).freshness()
    assert fresh.active_version is None
    assert fresh.is_stale is False
    enabled = real_source()
    (fresh,) = manager(session_factory, tmp_path, enabled, CountingFetcher()).freshness()
    assert fresh.is_stale is True


class TestConfiguredSources:
    """Alarm: Jede echte Quelle in sources.toml muss heute freigegeben sein.

    Schlägt dieser Test fehl, ist eine Lizenzprüfung abgelaufen oder unvollständig:
    Originalseite erneut prüfen, docs/DATA_SOURCES.md und `license_checked_on` nachführen.
    """

    def test_all_real_sources_are_license_cleared(self, catalog: Catalog) -> None:
        real = [s for s in catalog.sources if not s.is_fictional]
        assert real, "Erwartet mindestens eine echte Quelle (GLEIF)."
        for cfg in real:
            assert license_block_reasons(cfg, date.today()) == [], cfg.key
            assert cfg.license_url or cfg.terms_url
            assert cfg.attribution, f"{cfg.key}: Quellenangabe festhalten"

    def test_gleif_source_is_registered_with_cc0(self, catalog: Catalog) -> None:
        cfg = catalog.source("gleif_lei")
        assert cfg.license_url == "https://creativecommons.org/publicdomain/zero/1.0/"
        assert cfg.terms_url == "https://www.gleif.org/en/meta/lei-data-terms-of-use"
        assert cfg.enabled is False  # bis ein echter Fonds LEIs liefert
        lei_list = get_settings().project_root / str(cfg.lei_list)
        assert read_lei_list(lei_list)

    def test_gleif_fetcher_needs_lei_list(self) -> None:
        with pytest.raises(ValidationError, match="lei_list"):
            real_source(fetcher="gleif_api", format="gleif_json", kind=DatasetKind.ENTITIES)

    def test_data_sources_doc_mentions_every_real_source(self, catalog: Catalog) -> None:
        doc = (ROOT / "docs" / "DATA_SOURCES.md").read_text(encoding="utf-8")
        for cfg in catalog.sources:
            if not cfg.is_fictional:
                assert cfg.terms_url and cfg.terms_url in doc, cfg.key
