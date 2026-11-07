"""Statische Website: vollständig, nachvollziehbar, eigenständig (ohne externe Ressourcen)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from transparenz.cli import main as cli_main
from transparenz.entities.enums import UpdateStatus
from transparenz.services.context import create_context
from transparenz.site.builder import PRIVACY_URL, SiteBuildError, build_site, fund_slug

from conftest import FUND_ISIN

SLUG = fund_slug(FUND_ISIN)
ANALYTICS_FILES = ("analytics-config.js", "analytics-client.js")


@pytest.fixture
def site(isolated_project: Path, tmp_path: Path):  # type: ignore[no-untyped-def]
    ctx = create_context()
    assert all(o.status == UpdateStatus.ERFOLGREICH for o in ctx.updates.run_all(force=True))
    out = tmp_path / "site"
    result = build_site(ctx, out)
    yield out, result
    ctx.engine.dispose()


def read(out: Path, name: str) -> str:
    return (out / name).read_text(encoding="utf-8")


def test_all_pages_and_downloads_exist(site) -> None:  # type: ignore[no-untyped-def]
    out, result = site
    expected = {"index.html", "methodik.html", "datenquellen.html", f"fonds-{SLUG}.html",
                f"bericht-{SLUG}.md", f"belege-{SLUG}.csv",
                "analytics-config.js", "analytics-client.js"}
    assert expected == {p.name for p in result.files}
    assert all((out / name).stat().st_size > 0 for name in expected)


def test_fund_page_shows_findings_with_source_and_data_version(site) -> None:  # type: ignore[no-untyped-def]
    out, _ = site
    html = read(out, f"fonds-{SLUG}.html")
    assert "Muster Nachhaltigkeit Welt ETF (fiktiv)" in html
    assert "Fiktive Demodaten." in html
    assert "Laut Gerichtsurteil (Fiktives Verwaltungsgericht Musterkanton, 12.03.2025)" in html
    blocks = re.findall(r'<div class="evidence">(.*?)</div>\s*</div>', html, flags=re.S)
    assert len(blocks) >= 15
    for block in blocks:
        assert "Quelle: <a href=\"https://example.org/" in block
        assert "Version #" in block and "Hash" in block and "importiert" in block
    # Datenlücken und nicht zugeordnete Sachverhalte sind sichtbar
    assert "Unbekannte Beteiligung Beispiel AG" in html
    assert "BEL-018" in html and "BEL-017" in html
    assert html.count('data-finding="') == 19


def test_pages_are_self_contained_and_links_resolve(site) -> None:  # type: ignore[no-untyped-def]
    out, _ = site
    for page in out.glob("*.html"):
        html = page.read_text(encoding="utf-8")
        # Nur die zwei lokalen Dateien der Besuchszählung, keine fremden Skripte
        assert re.findall(r'<script src="([^"]+)"', html) == list(ANALYTICS_FILES)
        assert not re.search(r'<link[^>]+href="https?://', html)
        for href in re.findall(r'href="([^"]+)"', html):
            if href.startswith(("http://", "https://", "#")):
                continue
            assert (out / href.split("#")[0]).exists(), (page.name, href)


def test_analytics_is_documented_local_and_free_of_secrets(site) -> None:  # type: ignore[no-untyped-def]
    out, _ = site
    for page in out.glob("*.html"):
        html = page.read_text(encoding="utf-8")
        assert 'data-analytics-site="transparenz"' in html
        assert f'href="{PRIVACY_URL}"' in html
    config = read(out, "analytics-config.js")
    endpoints = re.findall(r'endpoint:\s*"([^"]*)"', config)
    assert len(endpoints) == 1
    assert endpoints[0] == "" or re.fullmatch(r"https://[a-z0-9.-]+/collect", endpoints[0])
    assert not re.search(r"token|secret|bearer|password", config, flags=re.I)
    client = read(out, "analytics-client.js")
    # Lokal (Doppelklick, localhost, Tests) wird nichts gesendet
    assert 'location.hostname !== "jonasbader7.github.io"' in client
    assert "localStorage" not in client and "sessionStorage" not in client
    assert "document.cookie" not in client


def test_methodology_is_rendered_from_docs(site) -> None:  # type: ignore[no-untyped-def]
    html = read(site[0], "methodik.html")
    assert "<table>" in html  # Markdown-Tabellen wurden umgewandelt
    assert "Beweisstatus statt Quellenanzahl" in html
    assert "offen" in html  # Schwellenwerte sind (noch) offen


def test_sources_page_shows_licenses_and_update_log(site) -> None:  # type: ignore[no-untyped-def]
    html = read(site[0], "datenquellen.html")
    assert "Kommerziell nutzbar" in html
    assert "erfolgreich (neuer Datenstand)" in html


def test_untrusted_text_is_escaped(isolated_project: Path, tmp_path: Path) -> None:
    path = isolated_project / "fiktiv_belegsammlung.csv"
    text = path.read_text(encoding="utf-8")
    injected = "<script>alert(1)</script> Satellitenanalyse zeigt"
    path.write_text(text.replace("Satellitenanalyse zeigt", injected), encoding="utf-8")
    ctx = create_context()
    ctx.updates.run_all(force=True)
    out = tmp_path / "site"
    build_site(ctx, out)
    html = read(out, f"fonds-{SLUG}.html")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    ctx.engine.dispose()


def test_empty_database_gives_clear_error(isolated_project: Path, tmp_path: Path) -> None:
    ctx = create_context()
    with pytest.raises(SiteBuildError, match="update"):
        build_site(ctx, tmp_path / "site")
    ctx.engine.dispose()


def test_cli_build_site_with_update(isolated_project: Path, tmp_path: Path) -> None:
    out = tmp_path / "web"
    assert cli_main(["build-site", "--update", "--out", str(out)]) == 0
    assert (out / "index.html").exists()
