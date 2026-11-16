"""Pilot: eine echte Fondsanalyse «Position → Unternehmen → Beleg», ausschliesslich lokal.

Seit 15.11.2026 nur noch Befehlszeile; die Logik liegt im Paket ``transparenz``:

- Positionen: ``ingestion/fi_holdings.py`` (Finansinspektionen, Register «Fondinnehav»)
- Wertpapier → Unternehmen: ``ingestion/wikidata_isin.py``, ``ingestion/gleif_lookup.py``,
  ``services/entity_matching.py`` (Zuordnung mit gemessener Präzision, D-046)
- Belege: ``ingestion/eu_ets.py``, ``ingestion/gem.py``, SwissPRTR aus dem Schweizer Fundament
- Kette und Befunde: ``services/fund_chain.py``, ``services/fund_findings.py``,
  ``services/ownership.py`` (Beziehungstypen, D-045)
- Messung der Zuordnung: ``services/mapping_reference.py``
- Bericht: ``reports/fund_chain_report.py`` mit ``reports/templates/fund_chain_report.html.j2``

Das Skript erfindet nichts: nicht zugeordnete Positionen bleiben «unbekannt». Emissionen sind
amtlich gemeldete Jahreswerte und kein Nachweis eines Rechtsverstosses. Kein Einbau ins
Screening oder in die Website; Ausgabe nur in den Datenordner unter
``processed/pilot_fund_chain/``.

Aufruf (Windows PowerShell, im Projektordner)::

    .venv\\Scripts\\python scripts\\pilot_fund_chain.py --zip <Fondinnehav_….zip> `
        --fund "<exakter Fondsname>" --fetch-wikidata --fetch-gleif `
        --ets-dir <Ordner mit operators_daily.csv.gz> --gleif-rr <…-rr-golden-copy.csv.zip>

Ohne die ``--fetch``-Schalter läuft das Skript offline mit den gespeicherten Abfragen.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from transparenz.config.catalog import load_criteria_model  # noqa: E402
from transparenz.config.settings import get_settings, local_data_dir, resolve_data_path  # noqa: E402
from transparenz.entities.identifiers import is_valid_lei  # noqa: E402
from transparenz.ingestion.eu_ets import ETS_ACTIVITY_FILE, ETS_OPERATORS_FILE, load_ets  # noqa: E402
from transparenz.ingestion.fi_holdings import find_fund  # noqa: E402
from transparenz.ingestion.gem import GEM_OWNERSHIP_GLOB, load_gem  # noqa: E402
from transparenz.ingestion.gleif_lookup import (  # noqa: E402
    GLEIF_MIN_INTERVAL,
    fetch_gleif,
    fetch_gleif_search,
    load_group_links,
)
from transparenz.ingestion.wikidata_isin import (  # noqa: E402
    fetch_wikidata_isins,
    fetch_wikidata_profiles,
    index_profiles,
    wikidata_candidates,
)
from transparenz.reports.fund_chain_report import render_html, render_markdown  # noqa: E402
from transparenz.services.fund_chain import (  # noqa: E402
    auto_match,
    build_chain,
    index_candidates,
    index_emissions,
    review_queue,
    search_plan,
)
from transparenz.services.mapping_reference import (  # noqa: E402
    DISPUTES_FILE,
    REFERENCE_FILE,
    REFERENCE_FILE_NPORT,
    SEARCH_CACHE_FILE,
    dispute_queue,
    evaluate_methods,
    reference_cases,
)
from transparenz.services.provenance import describe_file, describe_generated  # noqa: E402
from transparenz.services.review_decisions import index_decisions, load_decisions  # noqa: E402
from transparenz.services.security_master import confirmed_details  # noqa: E402

DATA = local_data_dir(ROOT)  # Datenordner (TRANSPARENZ_DATA_DIR, sonst data/)

DEFAULT_DECISIONS = DATA / "review/mapping_decisions.csv"

log = logging.getLogger("pilot_fund_chain")


def criteria_rules(model: Any) -> dict[str, Any]:
    """Schwelle und Wirkung der Kategorien je Kriterium (aus criteria.toml) für den Pilot."""
    return {c.key: {"min_share": c.min_own_account_share_percent,
                    "effects": {cat.key: cat.effect for cat in c.categories}}
            for c in model.active}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--zip", required=True, type=Path, help="FI-Quartalsarchiv (ZIP)")
    parser.add_argument("--fund", required=True, help="exakter Fondsname laut FI-Datei")
    parser.add_argument("--generation", type=Path, default=None,
                        help="Schweizer Exportgeneration (Standard: current.json)")
    parser.add_argument("--out", type=Path, default=DATA / "processed/pilot_fund_chain")
    parser.add_argument("--fetch-gleif", action="store_true",
                        help="Rechtsnamen und Mutterbeziehungen live bei GLEIF abrufen")
    parser.add_argument("--fetch-wikidata", action="store_true",
                        help="ISINs, Branche und Registernummern live bei Wikidata abfragen")
    parser.add_argument("--fetch-gleif-search", action="store_true",
                        help="GLEIF-Namens- und Registernummernsuche für fehlende Einträge "
                             "abrufen (Zwischenspeicher wird fondsübergreifend genutzt)")
    parser.add_argument("--ets-dir", type=Path, default=None,
                        help=f"Ordner mit {ETS_OPERATORS_FILE} und {ETS_ACTIVITY_FILE}")
    parser.add_argument("--gem-dir", type=Path, default=None,
                        help="Ordner mit dem entpackten Global Energy Ownership Tracker (xlsx)")
    parser.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS,
                        help="Datei mit gespeicherten Ja/Nein-Entscheiden zu Zuordnungen")
    parser.add_argument("--gleif-rr", type=Path, default=None,
                        help="lokale GLEIF-Beziehungsdatei (…-rr-golden-copy.csv.zip); "
                             "ersetzt die Mutterbeziehungs-Abfragen über die API")
    parser.add_argument("--security-master", type=Path, default=None,
                        help="Wertpapierstamm (processed/security_master.sqlite): N-PORT-Konsens "
                             "als Kennungsweg ISIN → LEI (D-059) und Referenz der "
                             "Namenssuche (D-058)")
    parser.add_argument("--case", action="append", default=[],
                        help="ISIN einer Position, deren Belegkette vollständig gezeigt wird "
                             "(mehrfach möglich)")
    args = parser.parse_args(argv)
    for name in ("zip", "generation", "out", "ets_dir", "gem_dir", "decisions", "gleif_rr",
                 "security_master"):
        value = getattr(args, name)
        if value is not None and not value.is_absolute() and value.parts[:1] == ("data",):
            setattr(args, name, resolve_data_path(value, ROOT))  # alte Befehle mit data\…
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    user_agent = get_settings().http_user_agent

    # Herkunft (D-052): Rohdateien vor jeder Verarbeitung gegen ihre Begleitdatei prüfen.
    provenance: list[dict[str, Any]] = []

    def verify(path: Path, source_key: str) -> None:
        provenance.append(describe_file(path, DATA, source_key).as_dict())

    def record(path: Path, source_key: str, origin: str) -> None:
        if path.exists():
            provenance.append(describe_generated(path, DATA, source_key, origin).as_dict())

    verify(args.zip, "fi_se_fondinnehav")
    if args.ets_dir:
        verify(args.ets_dir / ETS_OPERATORS_FILE, "eu_ets_union_registry")
        verify(args.ets_dir / ETS_ACTIVITY_FILE, "eu_ets_union_registry")
    if args.gleif_rr:
        verify(args.gleif_rr, "gleif_rr_golden_copy")

    generation = args.generation
    if generation is None:
        pointer = json.loads((DATA / "processed/swiss/current.json").read_text("utf-8"))
        generation = DATA / "processed/swiss" / pointer["generation"]
    for name in ("security_candidates.json", "emissions.json"):
        record(generation / name, "swiss_export",
               f"Schweizer Export {generation.name}; Quellen-Prüfsummen in quality_report.json")
    local = json.loads((generation / "security_candidates.json").read_text("utf-8"))
    emissions = index_emissions(json.loads((generation / "emissions.json").read_text("utf-8")))
    member, fund = find_fund(args.zip, args.fund)
    log.info("Fonds: %s (%s), %d Positionen, Quartalsende %s", fund.fund_name, member,
             len(fund.positions), fund.quarter_end)
    stem = "".join(ch if ch.isalnum() else "_" for ch in fund.fund_name).strip("_")
    args.out.mkdir(parents=True, exist_ok=True)

    def cached(path: Path, fetch: bool, fetcher: Any, label: str) -> dict[str, Any] | None:
        if fetch:
            data = fetcher()
            path.write_text(json.dumps(data, ensure_ascii=False, indent=1), "utf-8")
            return data
        if path.exists():
            data = json.loads(path.read_text("utf-8"))
            log.info("%s: gespeicherte Abfrage vom %s verwendet.", label, data.get("fetched_at"))
            return data
        log.info("%s: nicht abgefragt.", label)
        return None

    wikidata = cached(args.out / f"{stem}_wikidata_isin.json", args.fetch_wikidata,
                      lambda: fetch_wikidata_isins([p.isin for p in fund.positions if p.isin],
                                                   user_agent), "Wikidata (ISIN)")
    candidates = index_candidates(local + wikidata_candidates(wikidata))
    items = sorted({hit["wikidata_id"] for p in fund.positions
                    for hit in candidates.get(p.isin or "", [])})
    profiles = index_profiles(cached(
        args.out / f"{stem}_wikidata_profile.json", args.fetch_wikidata,
        lambda: fetch_wikidata_profiles(items, user_agent), "Wikidata (Branche, Register)"))
    decision_list = load_decisions(args.decisions)
    decisions = index_decisions(decision_list)
    log.info("Entscheide: %d gespeichert (%s).", len(decision_list), args.decisions)

    cache_path = args.out / SEARCH_CACHE_FILE
    cache: dict[str, Any] = (json.loads(cache_path.read_text("utf-8"))
                             if cache_path.exists() else {})
    plan = search_plan(fund, candidates, profiles)
    if args.fetch_gleif_search:
        for field_name, queries in plan.items():
            missing = [q for q in queries if f"{field_name}:{q}" not in cache]
            log.info("GLEIF-Suche %s: %d Suchtexte, davon %d neu (ca. %.0f min).", field_name,
                     len(queries), len(missing), len(missing) * GLEIF_MIN_INTERVAL / 60)
            try:
                fetch_gleif_search(missing, cache, user_agent, field=field_name)
            finally:
                cache_path.write_text(json.dumps(cache, ensure_ascii=False), "utf-8")
    missing_searches = sum(1 for f, qs in plan.items() for q in qs if f"{f}:{q}" not in cache)
    if missing_searches:
        log.info("GLEIF-Suche: %d Suchtexte fehlen im Zwischenspeicher (--fetch-gleif-search).",
                 missing_searches)
    parent_of: dict[str, set[str]] = defaultdict(set)
    if args.gleif_rr:
        found = {r["lei"] for f, qs in plan.items() for q in qs
                 for r in cache.get(f"{f}:{q}", {}).get("records", [])}
        for link in load_group_links(args.gleif_rr, found, found):
            if link["verified"]:
                parent_of[link["child_lei"]].add(link["parent_lei"])
    auto = auto_match(fund, candidates, profiles, cache, parent_of)

    position_leis = {
        lei.upper() for p in fund.positions for hit in candidates.get(p.isin or "", [])
        for lei in hit["claims"].get("P1278", []) if is_valid_lei(lei)}
    position_leis |= {lei for p in fund.positions
                      for lei, answer in decisions.get(p.isin or "", {}).items()
                      if answer == "yes"}
    position_leis |= {m["lei"] for result in auto.values()
                      for m in (result["name"], result["register"])
                      if m["status"] == "accepted" and m["lei"]}

    # N-PORT-Konsens (D-059): Kennungsweg ISIN → LEI und Referenz der Namenssuche (D-058).
    nport_reference: dict[str, str] | None = None
    nport_details: dict[str, dict[str, Any]] | None = None
    reference_info: dict[str, Any] | None = None
    if args.security_master:
        nport_reference, reference_info, nport_details = confirmed_details(
            args.security_master, [p.isin for p in fund.positions if p.isin])
        log.info("Wertpapierstamm (Regelversion %s, erstellt %s): %d Positionen mit "
                 "N-PORT-Konsens.", reference_info["rule_version"], reference_info["built_at"],
                 len(nport_reference))
        position_leis |= set(nport_reference.values())
    reporters = sorted(k[4:] for k in emissions if k.startswith("lei:"))

    ets: dict[str, Any] | None = None
    if args.ets_dir:
        ets = load_ets(args.ets_dir / ETS_OPERATORS_FILE, args.ets_dir / ETS_ACTIVITY_FILE)
        log.info("EU-Emissionshandel (Stand %s): %s", ets["snapshot_date"],
                 json.dumps(ets["stats"], ensure_ascii=False))
    evidence_leis = set(reporters) | set((ets or {}).get("by_lei", {}))

    group_links: list[dict[str, Any]] | None = None
    if args.gleif_rr:
        group_links = load_group_links(args.gleif_rr, evidence_leis, position_leis)
        log.info("GLEIF-Beziehungsdatei: %d Beziehungen von Rechtsträgern mit Beleg zu "
                 "Fondsunternehmen, davon %d vollständig bestätigt.", len(group_links),
                 sum(1 for link in group_links if link["verified"]))

    linked_children = {link["child_lei"] for link in group_links or []}
    gleif = cached(args.out / f"{stem}_gleif.json", args.fetch_gleif, lambda: fetch_gleif(
        sorted(set(reporters) | position_leis | linked_children),
        [] if group_links is not None else reporters, user_agent), "GLEIF (Rechtsnamen)")

    gem: dict[str, Any] | None = None
    if args.gem_dir:
        files = sorted(args.gem_dir.glob(GEM_OWNERSHIP_GLOB))
        if len(files) != 1:
            raise SystemExit(f"{args.gem_dir}: genau eine Datei {GEM_OWNERSHIP_GLOB} erwartet, "
                             f"{len(files)} gefunden.")
        verify(files[0], "gem_trackers")
        started = time.monotonic()
        gem = load_gem(files[0], position_leis, args.gem_dir)
        for name in gem.get("tracker_files") or []:
            verify(args.gem_dir / name, "gem_trackers")
        log.info("GEM (%s): %d Fonds-LEIs als Eigentümer erfasst, %d Anlagenzeilen, %.0f s.",
                 gem["release"], len(gem["entities"]),
                 sum(len(v) for v in gem["assets"].values()), time.monotonic() - started)

    model = load_criteria_model(get_settings().criteria_config)
    rules = criteria_rules(model)

    def chain(released: bool | frozenset[str]) -> dict[str, Any]:
        return build_chain(fund, candidates, emissions, gleif, ets, group_links, gem, decisions,
                           auto, released, profiles, rules, nport_reference, nport_details)

    # Erst messen (Namenssuche nicht wirksam), dann entscheiden, wo sie wirken darf.
    report = chain(False)
    store_path = args.out / (REFERENCE_FILE_NPORT if args.security_master else REFERENCE_FILE)
    store = json.loads(store_path.read_text("utf-8")) if store_path.exists() else {}
    store = {k: v for k, v in store.items() if v.get("fund") != fund.fund_name}
    store.update(reference_cases(report["positions"], fund.fund_name, nport_reference))
    store_path.write_text(json.dumps(store, ensure_ascii=False, indent=1), "utf-8")
    evaluation = evaluate_methods(store)
    if reference_info is not None:
        evaluation["reference"] = {"kind": "nport_consensus", **reference_info}
    released = evaluation["name"]["released_regions"]
    log.info("Namenssuche: %s Referenzfälle, %s mit Ergebnis, %s falsch, Präzision %s, untere "
             "95-%%-Grenze %s; freigegeben in: %s.", evaluation["name"]["reference_cases"],
             evaluation["name"]["answered"], evaluation["name"]["wrong"],
             evaluation["name"]["precision"], evaluation["name"]["precision_lower_bound_95"],
             ", ".join(released) or "keiner Region")
    if released:
        report = chain(frozenset(released))
    report["mapping_evaluation"] = evaluation
    report["rules"] = rules
    report["cases"] = [c.upper() for c in args.case]
    report["relationship_rules"] = [
        {**r.model_dump(mode="json"), "data_status_label": r.data_status_label}
        for r in model.relationship_rules]

    entities = {r["lei"]: r for result in cache.values() for r in result.get("records", [])}
    entities.update({lei: {"lei": lei, **entry} for lei, entry in
                     ((gleif or {}).get("names") or {}).items() if entry})
    disputes = dispute_queue(evaluation, entities)
    (args.out / DISPUTES_FILE).write_text(json.dumps(
        {"fund": "Abweichungen zwischen Referenz und automatischen Verfahren (alle Fonds)",
         "cases": disputes}, ensure_ascii=False, indent=1), "utf-8")
    log.info("Abweichungen Referenz ↔ Verfahren: %d (%s). Antworten wirken als Referenzfälle: "
             "python scripts\\review_mapping.py --queue %s", len(disputes),
             args.out / DISPUTES_FILE, args.out / DISPUTES_FILE)
    queue = review_queue(report["positions"])
    queue_path = args.out / f"{stem}_review_queue.json"
    queue_path.write_text(json.dumps(
        {"fund": fund.fund_name, "quarter_end": fund.quarter_end, "cases": queue},
        ensure_ascii=False, indent=1), "utf-8")
    log.info("Offene Ja/Nein-Fragen: %d (%s). Freiwillig beantworten: "
             "python scripts\\review_mapping.py", len(queue), queue_path)
    report["inputs"] = {"decisions": len(decision_list), "open_review_cases": len(queue),
                        "zip": args.zip.name, "member": member, "generation": generation.name,
                        "wikidata_fetched_at": (wikidata or {}).get("fetched_at"),
                        "gleif_fetched_at": (gleif or {}).get("fetched_at"),
                        "ets_snapshot_date": (ets or {}).get("snapshot_date"),
                        "ets_stats": (ets or {}).get("stats"),
                        "gleif_rr": args.gleif_rr.name if args.gleif_rr else None,
                        "gem_release": (gem or {}).get("release"),
                        "gem_tracker_files": (gem or {}).get("tracker_files"),
                        "swissprtr_data_as_of": next(
                            (r[0].get("data_as_of") for r in emissions.values() if r), None)}
    criteria = [{**c.model_dump(mode="json"), "data_status_label": c.data_status_label}
                for c in model.active]
    report["profile"] = model.profile_label
    for path, key, data in (
            (args.out / f"{stem}_wikidata_isin.json", "wikidata", wikidata),
            (args.out / f"{stem}_gleif.json", "gleif_api", gleif)):
        record(path, key, f"gespeicherte Abfrage vom {(data or {}).get('fetched_at') or '–'}")
    record(args.out / f"{stem}_wikidata_profile.json", "wikidata",
           "gespeicherte Abfrage (Branche, Registernummern)")
    record(cache_path, "gleif_api", "Zwischenspeicher der GLEIF-Namens- und Registersuche, "
                                    "fondsübergreifend")
    if args.security_master and reference_info is not None:
        record(args.security_master, "security_master",
               f"Wertpapierstamm aus N-PORT, Regelversion {reference_info['rule_version']}, "
               f"erstellt {reference_info['built_at']}; Eingaben in build_info")
    report["provenance"] = provenance
    (args.out / f"{stem}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), "utf-8")
    (args.out / f"{stem}.md").write_text(render_markdown(report), "utf-8")
    (args.out / f"{stem}.html").write_text(render_html(report, criteria), "utf-8")
    log.info("Bericht: %s (technisch: %s)", args.out / f"{stem}.html", args.out / f"{stem}.md")
    log.info("%s", json.dumps({k: v for k, v in report["summary"].items()
                               if not k.startswith("by_issuer")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
