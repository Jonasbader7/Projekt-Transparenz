"""Local search over the global Wikidata ticker/exchange research snapshot.

Deliberately separate from the Swiss foundation (``swiss_foundation.py``, ``swiss.sqlite``)
and the SEC market catalogue (``market_catalog.py``, ``markets.sqlite``): this covers a
single CC0 Wikidata snapshot across ALL countries at once
(``scripts/download_global_candidates.py``), downloaded outside the versioned
DataUpdateManager/catalog pipeline. Every row is an unverified company-level claim --
"this Wikidata item has a ticker and is linked to this exchange" -- never a confirmed,
currently-tradable security, never an ISIN, and rows are never merged by matching name or
ticker text alone (only exact Wikidata item identity groups a row's listings together).

The exchange's own country (Wikidata P17 of the exchange item, resolved once and cached in
``exchange_labels.json``) is shown for filtering; it is the exchange's home country, not
necessarily the listed company's country of incorporation (foreign/dual listings exist).
"""
from __future__ import annotations

import json
import unicodedata
from collections import defaultdict
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import httpx

from transparenz.config.settings import get_settings, resolve_data_path
from transparenz.entities.identifiers import normalize_company_name
from transparenz.ingestion.external import atomic_json, atomic_write
from transparenz.services.provenance import ProvenanceError, verify_recorded

EXPORT_SCHEMA_VERSION = 1
SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "ProjektTransparenz/0.1 (+https://github.com/Jonasbader7/Projekt-Transparenz)"
SNAPSHOT_DIR = "raw/external/wikidata_global"  # relativ zum Datenordner


def _folder() -> Path:
    return get_settings().processed_dir / "global_candidates"


@contextmanager
def global_candidates_lock():
    """Same OS-lock mechanism as the Swiss foundation and market catalogue (one writer
    at a time per folder); scoped to this feature's own folder, no collision with either.
    """
    from transparenz.services.swiss_foundation import foundation_lock
    with foundation_lock(_folder()):
        yield


def snapshot_pointer() -> dict:
    path = get_settings().data_dir / SNAPSHOT_DIR / "current.json"
    if not path.is_file():
        raise FileNotFoundError(
            "Kein globaler Wikidata-Bestand gefunden. Zuerst "
            "'.venv\\Scripts\\python scripts\\download_global_candidates.py "
            "--source wikidata_global' ausführen.")
    return json.loads(path.read_bytes())


def load_snapshot_rows() -> tuple[dict, list[dict]]:
    """Raw rows straight from the downloaded SPARQL result; no joins, no filtering."""
    settings = get_settings()
    pointer = snapshot_pointer()
    raw_path = resolve_data_path(pointer["file"], settings.project_root).resolve()
    if not raw_path.is_relative_to((settings.data_dir / SNAPSHOT_DIR).resolve()):
        raise ValueError("Rohdatenpfad ausserhalb des Quellenarchivs")
    if not pointer.get("sha256"):
        raise ProvenanceError(f"{SNAPSHOT_DIR}/current.json: keine Prüfsumme – nicht verwendet.")
    # Die beim Download in current.json festgehaltene Prüfsumme gilt (D-061).
    content, _ = verify_recorded(raw_path, settings.data_dir, "wikidata_global",
                                 pointer["sha256"], settings.data_dir / SNAPSHOT_DIR /
                                 "current.json", pointer)
    body = json.loads(content)
    bindings = body["results"]["bindings"]
    rows = []
    for binding in bindings:
        missing = {"item", "name", "exchange", "ticker"} - binding.keys()
        if missing:
            raise ValueError(f"Unerwartetes Rohdatenformat: Feld(er) fehlen: {sorted(missing)}")
        rows.append({
            "wikidata_id": binding["item"]["value"].rsplit("/", 1)[-1],
            "name": binding["name"]["value"],
            "exchange_id": binding["exchange"]["value"].rsplit("/", 1)[-1],
            "ticker": binding["ticker"]["value"],
        })
    return pointer, rows


def fetch_exchange_labels(ids: list[str]) -> dict[str, dict]:
    """Bounded VALUES lookup for exchange labels/countries already present in the snapshot.

    Never queries per-company data; only resolves the (small, bounded) set of distinct
    exchange items the snapshot already references, for display and filtering.
    """
    values = " ".join(f"wd:{qid}" for qid in ids)
    query = f"""SELECT ?exchange ?labelEn ?labelDe ?country ?countryLabelEn WHERE {{
  VALUES ?exchange {{ {values} }}
  OPTIONAL {{ ?exchange rdfs:label ?labelEn . FILTER(LANG(?labelEn)="en") }}
  OPTIONAL {{ ?exchange rdfs:label ?labelDe . FILTER(LANG(?labelDe)="de") }}
  OPTIONAL {{ ?exchange wdt:P17 ?country . ?country rdfs:label ?countryLabelEn .
             FILTER(LANG(?countryLabelEn)="en") }}
}}"""
    response = httpx.get(SPARQL_ENDPOINT, params={"query": query, "format": "json"},
                         headers={"User-Agent": USER_AGENT,
                                  "Accept": "application/sparql-results+json"},
                         timeout=60, follow_redirects=True)
    response.raise_for_status()
    by_exchange: dict[str, dict] = defaultdict(
        lambda: {"label_en": None, "label_de": None, "countries": []})
    for row in response.json()["results"]["bindings"]:
        qid = row["exchange"]["value"].rsplit("/", 1)[-1]
        entry = by_exchange[qid]
        entry["label_en"] = entry["label_en"] or row.get("labelEn", {}).get("value")
        entry["label_de"] = entry["label_de"] or row.get("labelDe", {}).get("value")
        if "country" in row:
            pair = [row["country"]["value"].rsplit("/", 1)[-1], row["countryLabelEn"]["value"]]
            if pair not in entry["countries"]:
                entry["countries"].append(pair)
    return dict(by_exchange)


def exchange_labels_cache_path() -> Path:
    return _folder() / "exchange_labels.json"


def ensure_exchange_labels(exchange_ids: set[str], *, refresh: bool) -> dict[str, dict]:
    """Loads the cached exchange-label lookup, refreshing only missing/forced entries.

    Fully offline once cached: the search/build commands only hit the network here, and
    only when the cache is missing an id that the current snapshot needs, or --refresh-labels
    was explicitly passed.
    """
    cache_path = exchange_labels_cache_path()
    cached: dict[str, dict] = {}
    if cache_path.is_file():
        cached = json.loads(cache_path.read_bytes()).get("exchanges", {})
    missing = sorted(exchange_ids - cached.keys()) if not refresh else sorted(exchange_ids)
    if missing:
        cached = {**cached, **fetch_exchange_labels(missing)}
        atomic_json(cache_path, {
            "generated_at": datetime.now(UTC).isoformat(),
            "license": "CC0 1.0 Universal (Wikidata structured data)",
            "license_url": "https://www.wikidata.org/wiki/Wikidata:Licensing",
            "method": "Bounded SPARQL VALUES lookup over exchange ids already present in "
                      "the wikidata_global snapshot; label + the exchange's own P17 country.",
            "exchanges": cached,
        })
    return cached


def _enrich(rows: list[dict], labels: dict[str, dict]) -> list[dict]:
    enriched = []
    for row in rows:
        label = labels.get(row["exchange_id"], {})
        countries = label.get("countries", [])
        enriched.append({
            **row,
            "exchange_label": label.get("label_de") or label.get("label_en"),
            "country_qids": [c[0] for c in countries],
            "country_labels": [c[1] for c in countries],
            "item_url": f"https://www.wikidata.org/wiki/{row['wikidata_id']}",
            "exchange_url": f"https://www.wikidata.org/wiki/{row['exchange_id']}",
        })
    return enriched


def _quality_report(rows: list[dict], pointer: dict) -> dict:
    companies = {r["wikidata_id"] for r in rows}
    by_name: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        by_name[normalize_company_name(row["name"])].add(row["wikidata_id"])
    duplicate_name_groups = [
        {"normalized_name": name, "wikidata_ids": sorted(ids)}
        for name, ids in sorted(by_name.items()) if len(ids) > 1]
    tickers_per_item: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        tickers_per_item[row["wikidata_id"]].add(row["ticker"])
    missing_exchange_label = sum(1 for r in rows if not r["exchange_label"])
    missing_country = sum(1 for r in rows if not r["country_labels"])
    return {
        "export_schema_version": EXPORT_SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "snapshot_retrieved_at": pointer["retrieved_at"],
        "snapshot_source_url": pointer["source_url"],
        "snapshot_sha256": pointer["sha256"],
        "snapshot_status": pointer["status"],
        "counts": {
            "entries": len(rows),
            "unique_companies": len(companies),
            "distinct_exchanges": len({r["exchange_id"] for r in rows}),
            "distinct_countries": len({c for r in rows for c in r["country_labels"]}),
            "companies_with_multiple_tickers": sum(
                1 for v in tickers_per_item.values() if len(v) > 1),
            "rows_missing_exchange_label": missing_exchange_label,
            "rows_missing_exchange_country": missing_country,
            "possible_duplicate_name_groups": len(duplicate_name_groups),
        },
        "possible_duplicates": duplicate_name_groups,
        "coverage_notes": [
            "Jede Zeile ist eine unbestätigte Wikidata-Aussage (CC0): 'dieses Wikidata-Item "
            "hat einen Ticker und ist mit dieser Börse verlinkt'. Kein bestätigtes "
            "Wertpapier, keine ISIN, keine Handelbarkeit, kein Nachhaltigkeitsurteil.",
            "Land = Sitzland der BÖRSE (Wikidata P17 der Börse), nicht automatisch das "
            "Sitzland des gelisteten Unternehmens (Zweit-/Auslandskotierungen, ADRs).",
            "Keine Fusion über Namen oder Ticker: mehrere Zeilen zum selben Wikidata-Item "
            "sind dieselbe reale Firma (z. B. Doppelkotierung); gleicher Name bei "
            "verschiedenen Wikidata-Items wird nur als mögliche Dublette gelistet, nie "
            "automatisch zusammengeführt.",
            "Kein Vollständigkeitsnachweis für irgendeinen Markt oder weltweit.",
            "CVM-Brasilien-Bestand bewusst getrennt, hier nicht enthalten.",
        ],
    }


def build(*, refresh_labels: bool = False) -> dict:
    """Builds a new generation (rows + quality report + HTML) from the current snapshot."""
    pointer, raw_rows = load_snapshot_rows()
    labels = ensure_exchange_labels({r["exchange_id"] for r in raw_rows}, refresh=refresh_labels)
    rows = _enrich(raw_rows, labels)
    report = _quality_report(rows, pointer)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    output = _folder()
    generation = output / "generations" / stamp
    atomic_json(generation / "rows.json", rows)
    atomic_json(generation / "quality_report.json", report)
    from transparenz.reports.global_candidates import render_global_candidates
    atomic_write(generation / "global_candidates.html",
                render_global_candidates(rows, report).encode("utf-8"))
    atomic_write(output / "current.json", json.dumps(
        {"generation": f"generations/{stamp}", "counts": report["counts"]},
        ensure_ascii=False).encode("utf-8"))
    return report


def _current_rows() -> list[dict]:
    output = _folder()
    pointer = json.loads((output / "current.json").read_bytes())
    generation = (output / pointer["generation"]).resolve()
    if not generation.is_relative_to((output / "generations").resolve()):
        raise ValueError("Ungültiger Exportpfad")
    return json.loads((generation / "rows.json").read_bytes())


def _fold(text: str) -> str:
    """Accent-insensitive, case-insensitive fold (so 'Nestle' also finds 'Nestlé')."""
    stripped = "".join(c for c in unicodedata.normalize("NFKD", text)
                       if not unicodedata.combining(c))
    return stripped.casefold()


def search(query: str, *, country: str | None = None, exchange: str | None = None,
          limit: int = 20) -> list[dict]:
    """Substring search over name/ticker/wikidata-id, with optional country/exchange filter.

    ``country``/``exchange`` match case-insensitively against the resolved labels or the
    raw Wikidata QID. Never a confirmed-equity search; see build()'s coverage_notes.
    Ranking favours a name that starts with or contains the query as a whole word over an
    incidental substring hit buried inside another word (e.g. "roche" inside
    "petrochemical"), so a short, common query still surfaces the obvious match first.
    """
    try:
        rows = _current_rows()
    except (OSError, FileNotFoundError, ValueError, KeyError) as exc:
        raise ValueError(
            "Kein Suchindex gefunden oder ungültig. Zuerst "
            "'transparenz global-candidates-build' ausführen."
        ) from exc
    if country:
        needle = country.casefold()
        rows = [r for r in rows if needle in [c.casefold() for c in r["country_labels"]]
               or needle in [c.casefold() for c in r["country_qids"]]]
    if exchange:
        needle = exchange.casefold()
        rows = [r for r in rows if needle == r["exchange_id"].casefold()
               or needle in (r["exchange_label"] or "").casefold()]
    needle = _fold(query)
    matches = [r for r in rows if needle in
              _fold(f"{r['name']} {r['ticker']} {r['wikidata_id']}")]

    def rank(row: dict) -> tuple[bool, bool, bool]:
        name = _fold(row["name"])
        return (row["ticker"].casefold() != query.casefold(),
               not name.startswith(needle),
               needle not in name.split())

    matches.sort(key=rank)
    return matches[:limit]
