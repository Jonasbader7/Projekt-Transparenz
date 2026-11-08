"""Archive official market-source terms for review, without importing restricted data."""
from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path

import httpx


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        if data.strip():
            self.parts.append(data.strip())


def main():
    urls = {
        "esma_legal": "https://www.esma.europa.eu/about-esma/legal-notice-and-data-protection",
        "sec_terms": "https://www.sec.gov/about/privacy-information",
        "sec_access": ("https://www.sec.gov/search-filings/edgar-search-assistance/"
                       "accessing-edgar-data"),
        "tickerinside_terms": "https://tickerinside.com/legal/",
        "tickerinside_api": "https://tickerinside.com/api/",
        "nasdaq_terms": "https://nasdaqtrader.com/Trader.aspx?id=CopyDisclaimMain",
    }
    root = Path(__file__).resolve().parents[1]
    folder = root / "data/raw/external/market_license_evidence"
    folder.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": "ProjektTransparenz/0.1 (source licence research)"}
    with httpx.Client(timeout=60, follow_redirects=True, headers=headers) as c:
        for key, url in urls.items():
            r = c.get(url)
            print(key, r.status_code, len(r.content), flush=True)
            digest = hashlib.sha256(r.content).hexdigest()
            path = folder / f"{key}_{digest}.html"
            if not path.exists():
                path.write_bytes(r.content)
                path.with_suffix('.metadata.json').write_text(json.dumps({
                    "url": url, "sha256": digest, "bytes": len(r.content),
                    "downloaded_at": datetime.now(UTC).isoformat(),
                    "status": r.status_code, "purpose": "licensing_reference_only"}),
                    encoding="utf-8")
            parser = Text()
            parser.feed(r.text)
            text = '\n'.join(parser.parts)
            (folder / f"{key}.txt").write_text(text, encoding="utf-8")
            time.sleep(1.1)


if __name__ == '__main__':
    main()
