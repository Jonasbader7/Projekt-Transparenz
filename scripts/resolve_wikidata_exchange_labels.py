"""Manual full refresh of the exchange label/country cache used by the global-candidates
search (``transparenz global-candidates-build`` also refreshes missing entries on its own;
this script forces *all* of them, e.g. after Wikidata labels changed).

Thin wrapper around services/global_candidates.py; not run automatically.
"""
from __future__ import annotations

from transparenz.services.global_candidates import (
    ensure_exchange_labels,
    exchange_labels_cache_path,
    load_snapshot_rows,
)


def main() -> int:
    _, rows = load_snapshot_rows()
    ids = {row["exchange_id"] for row in rows}
    resolved = ensure_exchange_labels(ids, refresh=True)
    missing = sorted(ids - resolved.keys())
    print(f"{len(resolved)} Börsen aufgelöst, {len(missing)} ohne Treffer: {missing}")
    print(f"-> {exchange_labels_cache_path()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
