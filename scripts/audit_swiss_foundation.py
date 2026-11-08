"""Offline audit of actual imported records and archived originals (no downloads)."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from transparenz.entities.identifiers import is_valid_isin, is_valid_lei
from transparenz.ingestion.external import atomic_json, normalize_uid

ROOT = Path(__file__).resolve().parents[1]


def array_items(path):
    """Incrementally decode a JSON array, bounded by one record plus a 64 KiB chunk."""
    decoder = json.JSONDecoder()
    with path.open(encoding="utf-8") as handle:
        buffer = ""
        started = False
        eof = False
        while True:
            if not eof:
                chunk = handle.read(65536)
                eof = not chunk
                buffer += chunk
            buffer = buffer.lstrip()
            if not started:
                if not buffer:
                    if eof:
                        raise ValueError("Empty JSON array file")
                    continue
                if not buffer.startswith("["):
                    raise ValueError("Expected array")
                buffer, started = buffer[1:].lstrip(), True
            while buffer:
                buffer = buffer.lstrip()
                if buffer.startswith(","):
                    buffer = buffer[1:].lstrip()
                if buffer.startswith("]"):
                    return
                try:
                    item, end = decoder.raw_decode(buffer)
                except json.JSONDecodeError:
                    if eof:
                        raise
                    break
                yield item
                buffer = buffer[end:]
            if eof:
                raise ValueError("Incomplete JSON array")


def main():
    base = ROOT / "data/processed/swiss"
    pointer = json.loads((base / "current.json").read_bytes())
    folder = base / pointer["generation"]
    quality = json.loads((folder / "quality_report.json").read_bytes())
    counts = quality["counts"]
    seen = set()
    missing_lei = identified = 0
    for row in array_items(folder / "companies.json"):
        assert row["company_key"] not in seen, row["company_key"]
        seen.add(row["company_key"])
        assert row.get("lei") is None or is_valid_lei(row["lei"])
        assert row.get("uid") is None or normalize_uid(row["uid"]) == row["uid"]
        missing_lei += not bool(row.get("lei"))
        identified += row["identity_status"] == "identified"
    assert len(seen) == counts["companies_legal_entities"]
    assert missing_lei == counts["companies_without_lei"]
    assert identified == counts["identified_companies"]
    funds = list(array_items(folder / "funds.json"))
    assert len(funds) == counts["funds_legal_entities"]
    assert all(is_valid_lei(f["lei"]) for f in funds)
    securities = list(array_items(folder / "securities.json"))
    assert len(securities) == counts["securities_confirmed"]
    assert all(is_valid_isin(s["isin"]) for s in securities)
    assert counts["fund_holdings"] == 0
    facilities = list(array_items(folder / "facilities.json"))
    assert len(facilities) == counts["facilities"]
    emissions = list(array_items(folder / "emissions.json"))
    assert len(emissions) == counts["emissions"]
    matched = diffuse = 0
    for row in emissions:
        assert row.get("uid_facility") is None or normalize_uid(row["uid_facility"]) == row[
            "uid_facility"]
        assert 2000 <= row["year"] <= 2100
        assert row.get("value") is None or isinstance(row["value"], int | float)
        if row["company_key"] is not None:
            assert row["company_key"] in seen, row["company_key"]
            assert row["mapping_status"] == "exact_uid_match"
            matched += 1
        if row["mapping_status"] == "diffuse_source_no_facility":
            assert row["facility_id"] is None
            diffuse += 1
    assert matched == counts["emissions_company_matched"]
    assert diffuse == counts["emissions_diffuse_source"]
    originals = 0
    for key, report in quality["sources"].items():
        assert not report["license_block_reasons"], key
        for entry in report.get("original_files", []):
            path = ROOT / "data/raw/external" / key / entry["path"]
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                while chunk := handle.read(1024 * 1024):
                    digest.update(chunk)
            assert digest.hexdigest() == entry["sha256"], path
            assert path.stat().st_size == entry["bytes"], path
            originals += 1
    with sqlite3.connect(ROOT / "data/processed/swiss.sqlite") as conn:
        runs = dict(conn.execute("SELECT status, COUNT(*) FROM update_runs GROUP BY status"))
        assert not runs.get("laufend"), runs
        active = conn.execute("SELECT source_key, record_count FROM dataset_versions "
                              "WHERE status='active'").fetchall()
    result = {"status": "passed", "counts": counts, "originals_hash_verified": originals,
              "unique_company_keys": len(seen), "emissions_checked": len(emissions),
              "update_runs_by_status": runs,
              "active_versions_record_counts": dict(active),
              "note": "Historical failures are retained; Wikidata 403 remains unresolved."}
    atomic_json(base / "audit_report.json", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
