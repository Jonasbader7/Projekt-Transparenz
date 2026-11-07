"""Statische Website aus dem aktiven Datenstand erzeugen.

Die Website ist ein **Schnappschuss**: Python berechnet alles (deterministisch), die
HTML-Seiten zeigen nur an. Keine Server-Logik, kein JavaScript nötig (nur ein kleiner
optionaler Filter). Dadurch:

* per Doppelklick auf ``site/index.html`` lokal nutzbar,
* unverändert auf GitHub Pages o. ä. veröffentlichbar (nur mit Zustimmung).

Seiten: ``index.html`` (Übersicht), ``fonds-<isin>.html`` (Fondsanalyse),
``methodik.html``, ``datenquellen.html``; dazu je Fonds ``bericht-<isin>.md`` und
``belege-<isin>.csv``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import markdown
from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape

from transparenz.database.repository import recent_runs
from transparenz.entities.enums import (
    FINDING_STATUSES,
    AssessmentStatus,
    UpdateStatus,
)
from transparenz.entities.labels import SHORT_STATUS, label
from transparenz.reports.fund_report import DISCLAIMER, findings_table, issuer_text, to_markdown
from transparenz.reports.texts import finding_sentence, provenance, status_explanation
from transparenz.screening.engine import FundScreeningResult
from transparenz.services.context import AppContext
from transparenz.utils.timeutil import format_date, format_datetime, utcnow

log = logging.getLogger(__name__)

METHODOLOGY_DOCS = (
    ("validierung.md", "Belegmodell und Validierung"),
    ("quellen-hierarchie.md", "Quellen-Hierarchie"),
    ("ausschlusskriterien.md", "Ausschlusskriterien"),
)


class SiteBuildError(RuntimeError):
    pass


@dataclass
class BuildResult:
    out_dir: Path
    files: list[Path] = field(default_factory=list)


def fund_slug(isin: str) -> str:
    return isin.lower()


def _pct(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f} %"


def _environment() -> Environment:
    env = Environment(
        loader=PackageLoader("transparenz.site", "templates"),
        autoescape=select_autoescape(["html"]),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.globals.update(
        label=label,
        short_status=lambda s: SHORT_STATUS[s],
        status_explanation=status_explanation,
        finding_sentence=finding_sentence,
        issuer_text=issuer_text,
        format_date=format_date,
        format_datetime=format_datetime,
        pct=_pct,
        fund_slug=fund_slug,
        S=AssessmentStatus,
        FINDING_STATUSES=FINDING_STATUSES,
        UpdateStatus=UpdateStatus,
    )
    return env


def _render_markdown(path: Path) -> str:
    if not path.exists():
        raise SiteBuildError(f"Methodik-Dokument fehlt: {path}")
    # Eigene, versionierte Dokumente – kein Fremdinhalt.
    html = markdown.markdown(path.read_text(encoding="utf-8"), extensions=["tables"])
    # Verweise zwischen den Methodik-Dokumenten auf Abschnitte der Methodik-Seite umleiten
    for index, (filename, _title) in enumerate(METHODOLOGY_DOCS, start=1):
        html = html.replace(f'href="{filename}"', f'href="#doc-{index}"')
    return html


def _gap_hints(result: FundScreeningResult) -> list[tuple[str, str, str]]:
    return [
        (p.position.name, c.name, flag)
        for p in result.positions
        for c in result.criteria
        if p.company is not None
        and not (a := p.assessments[c.key]).has_finding
        for flag in a.flags
    ]


def build_site(ctx: AppContext, out_dir: Path, as_of: date | None = None) -> BuildResult:
    """Erzeugt alle Seiten in ``out_dir`` (wird angelegt, bestehende Seiten überschrieben)."""
    data = ctx.active_data()
    if not data.funds:
        raise SiteBuildError(
            "Keine Fondsdaten im aktiven Datenstand. Zuerst «python -m transparenz update» "
            "ausführen."
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    env = _environment()
    built_at = utcnow()
    names = ctx.source_names
    versions = ctx.data_version_lines(data)
    funds = sorted(data.funds.values(), key=lambda s: s.fund.name)
    common = {
        "display_name": ctx.settings.display_name,
        "disclaimer": DISCLAIMER,
        "built_at": built_at,
        "funds": funds,
        "data_versions": versions,
    }
    result_files: list[Path] = []

    def write(name: str, content: str | bytes) -> None:
        path = out_dir / name
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        result_files.append(path)

    results: dict[str, FundScreeningResult] = {}
    for snap in funds:
        result = ctx.analyze_fund(snap.fund.isin, as_of=as_of, data=data)
        assert result is not None
        results[snap.fund.isin] = result
        slug = fund_slug(snap.fund.isin)
        write(f"bericht-{slug}.md", to_markdown(result, ctx.settings.display_name, versions, names))
        write(
            f"belege-{slug}.csv",
            findings_table(result, names).to_csv(index=False).encode("utf-8-sig"),
        )
        write(
            f"fonds-{slug}.html",
            env.get_template("fund.html").render(
                **common,
                page="fonds",
                title=snap.fund.name,
                r=result,
                slug=slug,
                statuses=[s for s in AssessmentStatus if s != AssessmentStatus.NICHT_ANWENDBAR],
                with_findings=[p for p in result.positions if p.has_finding],
                unknown=[p for p in result.positions if p.applicable and p.company is None],
                hints=_gap_hints(result),
                provenance=lambda m: provenance(m, names),
            ),
        )

    freshness = ctx.updates.freshness()
    write(
        "index.html",
        env.get_template("index.html").render(
            **common, page="index", title="Übersicht", results=results,
            stale=[f for f in freshness if f.is_stale],
            legend=[s for s in AssessmentStatus if s != AssessmentStatus.NICHT_ANWENDBAR],
        ),
    )
    docs = ctx.settings.docs_dir / "methodik"
    write(
        "methodik.html",
        env.get_template("methodology.html").render(
            **common, page="methodik", title="Methodik", criteria=ctx.catalog.criteria,
            documents=[(t, _render_markdown(docs / f)) for f, t in METHODOLOGY_DOCS],
        ),
    )
    with ctx.session_factory() as session:
        runs = recent_runs(session, limit=30)
    write(
        "datenquellen.html",
        env.get_template("sources.html").render(
            **common, page="datenquellen", title="Datenquellen & Aktualität",
            freshness=freshness, runs=runs,
        ),
    )
    log.info("Website mit %d Dateien erzeugt in %s", len(result_files), out_dir)
    return BuildResult(out_dir, result_files)
