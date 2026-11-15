"""Download licensed research snapshots; never assert verified/global completeness."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

from transparenz.config.settings import local_data_dir
from transparenz.ingestion.external import atomic_json, atomic_write

ROOT = Path(__file__).resolve().parents[1]
DATA = local_data_dir(ROOT)  # Datenordner (TRANSPARENZ_DATA_DIR, sonst data/)
QUERY = """SELECT DISTINCT ?item ?name ?exchange ?ticker WHERE {
 ?item p:P414 ?statement .
 ?statement ps:P414 ?exchange; pq:P249 ?ticker .
 FILTER NOT EXISTS { ?statement pq:P582 ?end }
 FILTER NOT EXISTS { ?statement wikibase:rank wikibase:DeprecatedRank }
 ?item rdfs:label ?name . FILTER(LANG(?name)="en")
}"""
SOURCES = {
    "wikidata_global": {
        "url": "https://query.wikidata.org/sparql",
        "extension": "json",
        "license": "CC0 structured data",
        "days": 7,
        "license_url": "https://www.wikidata.org/wiki/Wikidata:Licensing",
    },
    "cvm_companies": {
        "url": "https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/DADOS/cad_cia_aberta.csv",
        "extension": "csv",
        "license": "ODbL; raw research only",
        "days": 1,
        "license_url": "https://dados.cvm.gov.br/dataset/cia_aberta-cad/resource/"
        "2391143f-1423-48a5-9f6a-423245aca362",
    },
}


def download(key: str, force: bool = False) -> dict:
    source = SOURCES[key]
    folder = DATA / "raw/external" / key
    current = folder / "current.json"
    now = datetime.now(UTC)
    if current.exists() and not force:
        previous = json.loads(current.read_bytes())
        if now - datetime.fromisoformat(previous["retrieved_at"]) < timedelta(days=source["days"]):
            return {"source": key, "status": "not_due", "sha256": previous["sha256"]}
    params = {"query": QUERY, "format": "json"} if key == "wikidata_global" else None
    with httpx.Client(
        timeout=90,
        follow_redirects=True,
        headers={
            "User-Agent": "ProjektTransparenz/0.1 (+https://github.com/Jonasbader7/Projekt-Transparenz)"
        },
    ) as client:
        response = client.get(source["url"], params=params)
        response.raise_for_status()
    content = response.content
    if key == "wikidata_global":
        rows = response.json()["results"]["bindings"]
        if not rows or any(not {"item", "name", "exchange", "ticker"} <= r.keys() for r in rows):
            raise ValueError("Empty or invalid Wikidata response; keeping previous snapshot")
        count = len(rows)
    else:
        import csv
        import io

        reader = csv.DictReader(io.StringIO(content.decode("latin-1")), delimiter=";")
        if not {"CNPJ_CIA", "DENOM_SOCIAL", "SIT"} <= set(reader.fieldnames or []):
            raise ValueError("Invalid CVM schema; keeping previous snapshot")
        count = sum(1 for _ in reader)
        if not count:
            raise ValueError("Empty CVM snapshot; keeping previous snapshot")
    digest = hashlib.sha256(content).hexdigest()
    path = folder / "objects" / f"{digest}.{source['extension']}"
    atomic_write(path, content)
    metadata = {
        "source": key,
        "source_url": source["url"],
        "retrieved_at": now.isoformat(),
        "sha256": digest,
        "bytes": len(content),
        "rows": count,
        "license": source["license"],
        "license_url": source["license_url"],
        "file": str(path.relative_to(DATA)),
        "status": "unverified_research_snapshot",
        "complete_world": False,
    }
    if params:
        metadata["query"] = QUERY
    atomic_json(path.with_suffix(path.suffix + ".metadata.json"), metadata)
    atomic_json(current, metadata)
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--source", choices=list(SOURCES))
    args = parser.parse_args()
    results = []
    for key in [args.source] if args.source else SOURCES:
        try:
            result = download(key, args.force)
        except Exception as exc:
            result = {"source": key, "status": "failed", "error": str(exc)}
        results.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
    atomic_json(
        DATA / "processed/automation/download_status.json",
        {"checked_at": datetime.now(UTC).isoformat(), "results": results},
    )
    return int(any(r["status"] == "failed" for r in results))


if __name__ == "__main__":
    raise SystemExit(main())
