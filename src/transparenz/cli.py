"""Kommandozeile: ``python -m transparenz <befehl>`` bzw. ``transparenz <befehl>``.

Befehle:
  init-db                         Datenbankschema anlegen
  update [--source KEY] [--force] Datenquellen aktualisieren (Update-Pipeline)
  validate [--source KEY]         Quelle(n) abrufen und prüfen, ohne zu schreiben
  status                          Aktualität aller Quellen anzeigen
  screen --fund ISIN [--out DATEI] Fonds auswerten, optional Markdown-Bericht schreiben
  build-site [--out site] [--update] statische Website erzeugen (Schnappschuss)
  mapping --fund ISIN             Zuordnungsquote Wertpapier → Unternehmen messen
  swiss-update                    Schweizer Rohdaten lokal aktualisieren (separate DB)
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from transparenz.config.licensing import SourceBlockedError
from transparenz.entities.enums import UpdateStatus
from transparenz.entities.labels import label
from transparenz.ingestion.fetchers import FetchError
from transparenz.reports.fund_report import to_markdown
from transparenz.services.context import create_context
from transparenz.utils.logging_setup import setup_logging
from transparenz.utils.timeutil import format_date, format_datetime

log = logging.getLogger("transparenz.cli")


def _cmd_init_db(_: argparse.Namespace) -> int:
    ctx = create_context()
    print(f"Datenbank bereit: {ctx.settings.database_url}")
    return 0


def _cmd_update(args: argparse.Namespace) -> int:
    ctx = create_context()
    if args.source:
        outcomes = [ctx.updates.run_source(args.source, force=args.force, trigger=args.trigger)]
    else:
        outcomes = ctx.updates.run_all(force=args.force, trigger=args.trigger)
    failed = 0
    for o in outcomes:
        print(f"{o.source_key:35s} {label(o.status):35s} {o.message}")
        for e in o.errors[:10]:
            print(f"    {e}")
        if o.status in (UpdateStatus.FEHLGESCHLAGEN, UpdateStatus.GESPERRT):
            failed += 1
    return 1 if failed else 0


def _cmd_validate(args: argparse.Namespace) -> int:
    ctx = create_context()
    keys = [args.source] if args.source else [s.key for s in ctx.catalog.sources]
    bad = 0
    for key in keys:
        try:
            parsed = ctx.updates.validate_source(key)
        except FetchError as exc:
            print(f"{key:35s} ABRUF FEHLGESCHLAGEN: {exc}")
            bad += 1
            continue
        except SourceBlockedError as exc:
            print(f"{key:35s} GESPERRT: {'; '.join(exc.reasons)}")
            bad += 1
            continue
        state = "gültig" if parsed.is_valid else "UNGÜLTIG"
        print(
            f"{key:35s} {state:9s} {parsed.record_count:5d} Datensätze, "
            f"{len(parsed.errors)} Fehler, {len(parsed.warnings)} Warnungen"
        )
        for issue in parsed.issues[:20]:
            print(f"    {issue}")
        bad += 0 if parsed.is_valid else 1
    return 1 if bad else 0


def _cmd_status(_: argparse.Namespace) -> int:
    ctx = create_context()
    for f in ctx.updates.freshness():
        last = f.last_run
        print(
            f"{f.config.key:35s} Datenstand {format_date(f.data_as_of):10s} "
            f"geprüft {format_datetime(f.last_check_at):20s} "
            f"{'VERALTET' if f.is_stale else 'aktuell':8s} "
            f"letzter Lauf: {label(UpdateStatus(last.status)) if last else '–'}"
        )
    return 0


def _cmd_screen(args: argparse.Namespace) -> int:
    ctx = create_context()
    data = ctx.active_data()
    result = ctx.analyze_fund(args.fund, data=data)
    if result is None:
        print(f"Fonds {args.fund} nicht im aktiven Datenstand. Verfügbar: {', '.join(data.funds)}")
        return 1
    md = to_markdown(
        result, ctx.settings.display_name, ctx.data_version_lines(data), ctx.source_names
    )
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
        print(f"Bericht geschrieben: {args.out}")
    else:
        sys.stdout.write(md)
    return 0


def _cmd_mapping(args: argparse.Namespace) -> int:
    from transparenz.entities.resolution import EntityResolver
    from transparenz.services.mapping_quality import STEP_LABELS, measure_mapping_quality

    ctx = create_context()
    data = ctx.active_data()
    snap = data.funds.get(args.fund)
    if snap is None:
        print(f"Fonds {args.fund} nicht im aktiven Datenstand. Verfügbar: {', '.join(data.funds)}")
        return 1
    gleif_sources = {s.key for s in ctx.catalog.sources if s.format == "gleif_json"}
    gleif_leis = {
        c.lei for c in data.companies
        if c.lei and data.company_sources.get(c.company_key) in gleif_sources
    }
    q = measure_mapping_quality(
        snap.positions, EntityResolver(data.companies, data.securities), gleif_leis
    )
    print(f"Zuordnungsquote {snap.fund.name} ({snap.fund.isin}), Stichtag "
          f"{format_date(snap.fund.as_of_date)}")
    print(f"Alle Positionen: {q.total_positions} ({q.total_weight_pct:.2f} % Gewicht)")
    for step in q.steps:
        by_count, by_weight = q.share(step.key)
        share = (
            f"{by_count:5.1f} % der Anzahl, {by_weight:5.1f} % des Gewichts"
            if by_count is not None and by_weight is not None else "–"
        )
        print(f"  {STEP_LABELS[step.key]:32s} {step.count:4d}  {step.weight_pct:7.2f} %  {share}")
    if not gleif_leis:
        print("Hinweis: kein aktiver GLEIF-Datenstand – letzte Stufe ist deshalb 0.")
    if q.gaps:
        print("Lücken (grösstes Gewicht zuerst):")
        for g in q.gaps[: args.limit]:
            where = g.isin or "ohne ISIN"
            print(f"  {g.weight_pct:6.2f} %  {g.position_name} ({where}): {g.reason}")
    return 0


def _cmd_build_site(args: argparse.Namespace) -> int:
    from transparenz.site.builder import SiteBuildError, build_site

    ctx = create_context()
    if args.update:
        for o in ctx.updates.run_all(trigger="build-site"):
            print(f"{o.source_key:35s} {label(o.status):35s} {o.message}")
    out = Path(args.out)
    if not out.is_absolute():
        out = ctx.settings.project_root / out
    try:
        result = build_site(ctx, out)
    except SiteBuildError as exc:
        print(f"Fehler: {exc}")
        return 1
    print(f"Website erzeugt: {len(result.files)} Dateien in {out}")
    print(f"Öffnen: {out / 'index.html'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="transparenz", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)
    swiss = sub.add_parser("swiss-update", help="Lokales Schweizer Rohdatenfundament")
    swiss.add_argument("--source")
    swiss.add_argument("--force", action="store_true")
    swiss.add_argument("--export-only", action="store_true", help="Ohne Netzwerk neu exportieren")
    swiss.set_defaults(func=_cmd_swiss_update)
    sub.add_parser("init-db").set_defaults(func=_cmd_init_db)
    up = sub.add_parser("update")
    up.add_argument("--source")
    up.add_argument("--force", action="store_true", help="Intervall ignorieren")
    up.add_argument("--trigger", default="manuell", help="z. B. manuell, geplant, ci")
    up.set_defaults(func=_cmd_update)
    va = sub.add_parser("validate")
    va.add_argument("--source")
    va.set_defaults(func=_cmd_validate)
    sub.add_parser("status").set_defaults(func=_cmd_status)
    sc = sub.add_parser("screen")
    sc.add_argument("--fund", required=True, help="ISIN des Fonds")
    sc.add_argument("--out", help="Markdown-Datei")
    sc.set_defaults(func=_cmd_screen)
    mp = sub.add_parser("mapping")
    mp.add_argument("--fund", required=True, help="ISIN des Fonds")
    mp.add_argument("--limit", type=int, default=20, help="höchstens so viele Lücken zeigen")
    mp.set_defaults(func=_cmd_mapping)
    bs = sub.add_parser("build-site")
    bs.add_argument("--out", default="site", help="Zielordner (Standard: site)")
    bs.add_argument("--update", action="store_true", help="vorher fällige Quellen aktualisieren")
    bs.set_defaults(func=_cmd_build_site)
    return p


def _cmd_swiss_update(args: argparse.Namespace) -> int:
    from transparenz.services.swiss_foundation import update_foundation

    _, failed = update_foundation(args.force, args.source, args.export_only)
    return int(failed)


def main(argv: list[str] | None = None) -> int:
    from transparenz.config.settings import get_settings

    # Windows-Konsolen nutzen oft cp1252 – Umlaute, «», → würden sonst abstürzen.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    setup_logging(get_settings().log_level)
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
