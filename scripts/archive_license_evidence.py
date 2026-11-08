"""Archive official licensing references locally, without productive data imports."""
from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

from transparenz.config.catalog import load_catalog
from transparenz.config.settings import CONFIG_DIR
from transparenz.ingestion.external import atomic_json, atomic_write

ROOT = Path(__file__).resolve().parents[1]


def main():
    catalog = load_catalog(CONFIG_DIR / "swiss_sources.toml", CONFIG_DIR / "criteria.toml")
    references = {cfg.key: cfg.terms_url for cfg in catalog.sources}
    references.update({
        "zefix_metadata": "https://ckan.opendata.swiss/api/3/action/package_show"
                          "?id=zefix-zentraler-firmenindex",
        "swissprtr_metadata": "https://ckan.opendata.swiss/api/3/action/package_show"
                             "?id=schadstofffreisetzungs-und-transferregister-der-schweiz-swissprtr",
        "ogd_terms": "https://opendata.swiss/en/terms-of-use",
        "six_terms": "https://www.six-group.com/en/services/legal/terms-and-conditions/terms-of-use.html",
        "climate_trace_terms": "https://climatetrace.org/terms",
        "opensanctions_terms": "https://www.opensanctions.org/docs/bulk/updates/",
        "seco_reference": "https://www.seco.admin.ch/de/suche-nach-sanktionsadressaten",
    })
    evidence = []
    headers = {"User-Agent": "ProjektTransparenz/0.1 (license research)"}
    with httpx.Client(timeout=60, follow_redirects=True, headers=headers) as client:
        for key, url in references.items():
            time.sleep(1.1)
            response = client.get(url)
            stamp = datetime.now(UTC).isoformat()
            item = {"reference_key": key, "url": url, "fetched_at": stamp,
                    "status_code": response.status_code, "purpose": "license_reference_only"}
            if response.status_code == 200:
                content = response.content
                digest = hashlib.sha256(content).hexdigest()
                suffix = "json" if "json" in response.headers.get("content-type", "") else "html"
                folder = ROOT / "data/raw/external/license_evidence" / key
                path = folder / f"{digest}.{suffix}"
                item.update(sha256=digest, bytes=len(content), format=suffix, path=str(path))
                if not path.exists():
                    atomic_write(path, content)
                    atomic_json(path.with_suffix(path.suffix + ".metadata.json"), item)
            # 401/403 are recorded, never bypassed or retried via alternate hosts.
            evidence.append(item)
            print(key, response.status_code, flush=True)
    atomic_json(ROOT / "data/raw/external/license_evidence/latest_review.json", evidence)
    print(json.dumps({"references_checked": len(evidence)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
