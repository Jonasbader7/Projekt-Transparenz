"""Vergleichslauf für den Pilot: rechnet die sechs Pilotfonds offline und vergleicht zwei Läufe.

Zweck: Ein Umbau des Codes darf kein Ergebnis verändern. Beide Läufe starten von derselben
eingefrorenen Kopie der gespeicherten Abfragen (Wikidata, GLEIF, Referenzfälle), damit nur der
Code den Unterschied machen kann. Es wird nichts aus dem Netz geladen.

    python scripts/pilot_regression.py freeze           # Eingangsstand einfrieren (einmal)
    python scripts/pilot_regression.py run vorher       # sechs Fonds rechnen
    python scripts/pilot_regression.py run nachher
    python scripts/pilot_regression.py compare vorher nachher
    python scripts/pilot_regression.py compare vorher neu --ignore-key provenance --json-only
    python scripts/pilot_regression.py run nport --security-master --passes 2   # D-058

Mit ``--security-master`` dient der Wertpapierstamm (processed/security_master.sqlite) als
Kennungsweg ISIN → LEI (D-059) und als Referenz der Namenssuche (D-058). Die Freigabe hängt
vom fondsübergreifenden Referenzspeicher ab, der im ersten Durchgang erst Fonds für Fonds
entsteht; ``--passes 2`` rechnet deshalb alle Fonds
ein zweites Mal mit vollständigem Speicher.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from transparenz.config.settings import local_data_dir  # noqa: E402

DATA = local_data_dir(ROOT)
PILOT = DATA / "processed/pilot_fund_chain"
BASE = DATA / "processed/pilot_regression"
FROZEN = BASE / "eingang"
EXTERNAL = DATA / "raw/external"

# Reihenfolge wie am 14.11.2026: zuerst die Entwicklungsfonds, dann die Testfonds.
FUNDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("SEB Global Sustainable Companies Fund", ("US5949181045", "US46625H1005", "BMG491BT1088")),
    ("Handelsbanken Global High Dividend Low Volatility Criteria", ()),
    ("Storebrand Global Multifactor", ()),
    ("Lannebo Emerging Markets", ()),
    ("Swedbank Robur Access Asien", ()),
    ("Handelsbanken Norden Index Criteria", ()),
)
# Eingaben, die sich zwischen zwei Läufen nicht unterscheiden dürfen, aber Uhrzeit oder
# absolute Pfade enthalten können.
VOLATILE_KEYS = {"generated_at", "run_at", "created_at"}


def inputs() -> list[str]:
    return [
        "--zip", str(EXTERNAL / "fi_se_fondinnehav/2026Q2/Fondinnehav_2026Q2.zip"),
        "--ets-dir", str(EXTERNAL / "eu_ets_union_registry/2026-11-11"),
        "--gleif-rr", str(EXTERNAL / "gleif_rr_golden_copy/2026-11-11/gleif-goldencopy-rr.csv.zip"),
        "--gem-dir", str(EXTERNAL / "gem/2026-11-11/extracted"),
    ]


def freeze() -> None:
    if FROZEN.exists():
        raise SystemExit(f"{FROZEN} existiert bereits; eingefrorener Stand bleibt unverändert.")
    FROZEN.mkdir(parents=True)
    for path in PILOT.glob("*.json"):
        shutil.copy2(path, FROZEN / path.name)
    print(f"Eingefroren: {len(list(FROZEN.iterdir()))} Dateien nach {FROZEN}")


SECURITY_MASTER = DATA / "processed/security_master.sqlite"


def run(label: str, security_master: bool = False, passes: int = 1) -> None:
    if not FROZEN.exists():
        raise SystemExit("Zuerst 'freeze' ausführen.")
    out = BASE / label
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(FROZEN, out)
    extra = ["--security-master", str(SECURITY_MASTER)] if security_master else []
    for number in range(1, passes + 1):
        for fund, cases in FUNDS:
            argv = [sys.executable, str(ROOT / "scripts/pilot_fund_chain.py"), *inputs(),
                    *extra, "--fund", fund, "--out", str(out),
                    "--decisions", str(out / "keine_entscheide.csv")]
            for case in cases:
                argv += ["--case", case]
            print(f"-> Durchgang {number}: {fund}", flush=True)
            subprocess.run(argv, check=True, cwd=ROOT)


def _strip(value: Any, ignore: frozenset[str] = frozenset()) -> Any:
    if isinstance(value, dict):
        return {k: _strip(v, ignore) for k, v in value.items()
                if k not in VOLATILE_KEYS and k not in ignore}
    if isinstance(value, list):
        return [_strip(v, ignore) for v in value]
    return value


def _first_difference(a: Any, b: Any, path: str = "",
                      names: tuple[str, str] = ("links", "rechts")) -> str | None:
    if type(a) is not type(b):
        return f"{path}: Typ {type(a).__name__} ≠ {type(b).__name__}"
    if isinstance(a, dict):
        for key in sorted(set(a) | set(b), key=str):
            if key not in a or key not in b:
                return f"{path}/{key}: nur in {names[0] if key in a else names[1]}"
            found = _first_difference(a[key], b[key], f"{path}/{key}", names)
            if found:
                return found
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return f"{path}: Länge {len(a)} ≠ {len(b)}"
        for i, (x, y) in enumerate(zip(a, b, strict=True)):
            found = _first_difference(x, y, f"{path}[{i}]", names)
            if found:
                return found
        return None
    return None if a == b else f"{path}: {a!r} ≠ {b!r}"


def compare(left: str, right: str, ignore: frozenset[str] = frozenset(),
            json_only: bool = False) -> int:
    a_dir, b_dir = BASE / left, BASE / right
    names = sorted({p.name for p in a_dir.iterdir()} | {p.name for p in b_dir.iterdir()})
    if json_only:
        names = [n for n in names if n.endswith(".json")]
    failures = 0
    for name in names:
        a, b = a_dir / name, b_dir / name
        if not a.exists() or not b.exists():
            print(f"FEHLT  {name}: nur in {left if a.exists() else right}")
            failures += 1
            continue
        if name.endswith(".json"):
            diff = _first_difference(_strip(json.loads(a.read_bytes()), ignore),
                                     _strip(json.loads(b.read_bytes()), ignore),
                                     names=(left, right))
        else:
            diff = None if a.read_bytes() == b.read_bytes() else "Inhalt verschieden"
        if diff:
            print(f"ANDERS {name}: {diff}")
            failures += 1
    print(f"{len(names)} Dateien verglichen, {failures} Abweichungen.")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows-Konsole: Umlaute und ≠ ausgeben
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("freeze")
    run_parser = sub.add_parser("run")
    run_parser.add_argument("label")
    run_parser.add_argument("--security-master", action="store_true",
                            help="Wertpapierstamm als Kennungsweg und Referenz (D-058, D-059)")
    run_parser.add_argument("--passes", type=int, default=1,
                            help="alle Fonds so oft rechnen (Freigabe mit vollem Speicher)")
    cmp = sub.add_parser("compare")
    cmp.add_argument("left")
    cmp.add_argument("right")
    cmp.add_argument("--ignore-key", action="append", default=[],
                     help="JSON-Schlüssel, der bewusst neu ist (z. B. provenance)")
    cmp.add_argument("--json-only", action="store_true",
                     help="nur JSON vergleichen (HTML/Markdown ändern sich mit neuen Abschnitten)")
    args = parser.parse_args(argv)
    if args.command == "freeze":
        freeze()
    elif args.command == "run":
        run(args.label, args.security_master, max(1, args.passes))
    else:
        return compare(args.left, args.right, frozenset(args.ignore_key), args.json_only)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
