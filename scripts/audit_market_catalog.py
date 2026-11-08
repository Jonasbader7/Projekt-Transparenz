"""Offline verification of originals, active versions and each single-class ETF proof."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import sqlite3
import zipfile
from pathlib import Path


def audit(root: Path) -> dict:
    output = root / "data/processed/market"
    pointer = json.loads((output / "current.json").read_bytes())
    generation = (output / pointer["generation"]).resolve()
    if not generation.is_relative_to((output / "generations").resolve()):
        raise ValueError("Exportpfad ausserhalb der Generationen")
    items = json.loads((generation / "catalogue.json").read_bytes())
    report = json.loads((generation / "quality_report.json").read_bytes())
    if report["complete_world"] or report["world_coverage_percent"] is not None:
        raise ValueError("Unbelegte Weltabdeckung")
    if len(items) != len({r["catalogue_key"] for r in items}):
        raise ValueError("Doppelte Katalogschlüssel")
    checked, proofs = 0, set()
    for key in report["sources"]:
        for path in (root / "data/raw/external" / key / "objects").glob("*"):
            if path.name.endswith(".metadata.json"):
                continue
            metadata = json.loads(path.with_suffix(path.suffix + ".metadata.json").read_bytes())
            if hashlib.sha256(path.read_bytes()).hexdigest() != metadata["sha256"]:
                raise ValueError(f"Falsche Originalprüfsumme: {path.name}")
            if path.stat().st_size != metadata["bytes"]:
                raise ValueError(f"Falsche Originalgrösse: {path.name}")
            checked += 1
            if key != "sec_ncen" or path.suffix != ".zip":
                continue
            with zipfile.ZipFile(path) as z:
                def rows(name):
                    with z.open(name) as f:
                        yield from csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig"),
                                                  delimiter="\t")
                funds = {r["FUND_ID"]: r for r in rows("FUND_REPORTED_INFO.tsv")}
                members = {}
                for r in rows("SHARES_OUTSTANDING.tsv"):
                    members.setdefault(r["FUND_ID"], []).append(r)
                for fund_id, classes in members.items():
                    f = funds[fund_id]
                    if f["IS_ETF"] == "Y" and len(classes) == 1:
                        proofs.add((metadata["sha256"], f["ACCESSION_NUMBER"],
                                    f["SERIES_ID"], classes[0]["CLASS_ID"]))
    etfs = 0
    for item in items:
        if item["isin"] is not None or item["currently_tradable"] is not None:
            raise ValueError("Nicht belegte ISIN/Handelbarkeit")
        if item["classification"] == "etf_reported_single_class":
            etfs += 1
            if not any((e["original_sha256"], e["accession"], item["series_id"],
                        item["class_id"]) in proofs for e in item["evidence"]):
                raise ValueError(f"ETF ohne passenden Originalnachweis: {item['catalogue_key']}")
    with sqlite3.connect(root / "data/processed/markets.sqlite") as db:
        running = db.execute("select count(*) from update_runs "
                             "where status='laufend'").fetchone()[0]
        if running:
            raise ValueError("Noch laufende Aktualisierung")
        for key, source in report["sources"].items():
            active = db.execute("select id,content_hash from dataset_versions "
                                "where source_key=? and status='active'", (key,)).fetchall()
            expected = [(source["active_version"], source["hash"])] if source["hash"] else []
            if active != expected:
                raise ValueError(f"Exportversion nicht aktuell: {key}")
    result = {"catalogue_entries": len(items), "originals_hash_checked": checked,
              "etf_single_class_proofs_checked": etfs, "running_updates": 0,
              "complete_world": False, "result": "passed"}
    (output / "audit_report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(audit(Path(__file__).resolve().parents[1]), indent=2))
