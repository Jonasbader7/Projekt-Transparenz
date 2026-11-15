"""Unsichere Zuordnungen von Hand entscheiden: je Fall «ja», «nein» oder «überspringen».

Freiwillig: Im normalen Betrieb ordnet der Pilot automatisch zu und lässt Unsicheres offen
(D-046). Antworten hier korrigieren Fehler und dienen als Referenzfälle für die Messung.

Liest die offenen Fragen, die ``pilot_fund_chain.py`` zuletzt geschrieben hat
(``*_review_queue.json``), zeigt je Kandidat die Namen nebeneinander und speichert die Antwort
dauerhaft in ``data/review/mapping_decisions.csv``. Der nächste Pilotlauf wendet die Entscheide
automatisch an, auch bei jedem anderen Fonds mit derselben ISIN.

    .venv\\Scripts\\python scripts\\review_mapping.py

Eingaben: j = ja, n = nein, Enter = überspringen, q = aufhören. Es wird nichts abgerufen.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from transparenz.config.settings import local_data_dir, resolve_data_path  # noqa: E402

DATA = local_data_dir(ROOT)  # Datenordner (TRANSPARENZ_DATA_DIR, sonst data/)

from transparenz.services.review_decisions import (  # noqa: E402
    MappingDecision,
    append_decision,
    decision_stats,
    load_decisions,
)

DEFAULT_DECISIONS = DATA / "review/mapping_decisions.csv"
DEFAULT_QUEUE_DIR = DATA / "processed/pilot_fund_chain"
SIGNAL_TEXT = {"name_mismatch": "Name weicht ab", "ambiguous": "mehrere Kandidaten",
               "name_proposal": "Vorschlag der Namenssuche (Verfahren nicht freigegeben)",
               "reference_dispute": "Referenz und automatisches Verfahren widersprechen sich"}
ANSWERS = {"j": "yes", "ja": "yes", "y": "yes", "n": "no", "nein": "no"}


def newest_queue(directory: Path) -> Path:
    files = sorted(directory.glob("*_review_queue.json"), key=lambda p: p.stat().st_mtime)
    if not files:
        raise SystemExit(f"Keine offene Fragenliste in {directory}. Zuerst den Pilot laufen "
                         "lassen (scripts\\pilot_fund_chain.py).")
    return files[-1]


def describe(case: dict[str, Any], candidate: dict[str, Any]) -> str:
    other = ", ".join(n for n in candidate.get("other_names") or [] if n) or "keine"
    weight = case.get("weight_percent")
    return "\n".join([
        "",
        f"Position im Fonds : {case['position_name']}  (ISIN {case['isin']}, "
        f"{'?' if weight is None else f'{weight:.2f}'} % des Fonds)",
        f"Grund der Frage   : {SIGNAL_TEXT.get(case['signal'], case['signal'])}",
        f"Laut Wikidata     : {', '.join(case.get('wikidata_names') or []) or 'kein Eintrag'}",
        *([f"Fonds             : {case['fund']}"] if case.get("fund") else []),
        f"Kandidat (GLEIF)  : {candidate.get('legal_name') or 'Name nicht geladen'}"
        + (f"  [vorgeschlagen von: {candidate['origin']}]" if candidate.get("origin") else ""),
        f"  frühere Namen   : {other}",
        f"  LEI             : {candidate['lei']}  "
        f"(Status {candidate.get('registration_status') or 'unbekannt'})",
    ])


def review(cases: list[dict[str, Any]], decisions_path: Path,
           ask: Callable[[str], str] = input, show: Callable[[str], None] = print,
           today: date | None = None) -> dict[str, int]:
    """Stellt die Fragen und speichert jede Antwort sofort. Gibt die Zählung zurück."""
    today = today or date.today()
    counts = {"yes": 0, "no": 0, "skipped": 0}
    for case in cases:
        for candidate in case["candidates"]:
            show(describe(case, candidate))
            reply = ask("Gehört die Position zu diesem Unternehmen? [j/n/Enter=später/q] ")
            reply = reply.strip().lower()
            if reply == "q":
                return counts
            answer = ANSWERS.get(reply)
            if answer is None:
                counts["skipped"] += 1
                continue
            append_decision(decisions_path, MappingDecision(
                isin=case["isin"], lei=candidate["lei"], decision=answer, decided_on=today,
                signal=case["signal"], note=case["position_name"]))
            counts[answer] += 1
            if answer == "yes":
                break  # ein Wertpapier hat genau einen Emittenten
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--queue", type=Path, default=None,
                        help="Fragenliste (Standard: die neueste im Pilot-Ausgabeordner)")
    parser.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS)
    args = parser.parse_args(argv)
    for name in ("queue", "decisions"):
        value = getattr(args, name)
        if value is not None and not value.is_absolute() and value.parts[:1] == ("data",):
            setattr(args, name, resolve_data_path(value, ROOT))  # alte Befehle mit data\…
    queue_path = args.queue or newest_queue(DEFAULT_QUEUE_DIR)
    queue = json.loads(queue_path.read_text("utf-8"))
    cases = queue["cases"]
    print(f"{queue.get('fund')}: {len(cases)} offene Fälle aus {queue_path.name}")
    counts = review(cases, args.decisions)
    print(f"\nGespeichert: {counts['yes']} ja, {counts['no']} nein; "
          f"{counts['skipped']} übersprungen. Datei: {args.decisions}")
    for signal, stat in decision_stats(load_decisions(args.decisions)).items():
        print(f"  bisher bei «{SIGNAL_TEXT.get(signal, signal)}»: "
              f"{stat['yes']} ja, {stat['no']} nein")
    print("Jetzt den Pilot neu laufen lassen; die Entscheide wirken automatisch.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
