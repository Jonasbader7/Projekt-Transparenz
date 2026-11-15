"""EU-Emissionshandelsregister (Union Registry): Anlagen und verifizierte Emissionen je
Kontoinhaber-LEI.
"""
from __future__ import annotations

import csv
import gzip
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from transparenz.entities.identifiers import is_valid_lei
from transparenz.ingestion.gleif_lookup import require_columns

ETS_ATTRIBUTION = (
    "Europäische Kommission, Union Registry des EU-Emissionshandels, Public Website "
    "https://union-registry-data.ec.europa.eu/ (Tagesauszüge, gefiltert und umgeformt)"
)

ETS_TERMS_URL = "https://commission.europa.eu/legal-notice_en"

ETS_OPERATORS_FILE = "operators_daily.csv.gz"

ETS_ACTIVITY_FILE = "operators_yearly_activity_daily.csv.gz"

ETS_OPERATOR_COLUMNS = {"INSTALLATION_IDENTIFIER", "REGISTRY_CODE", "INSTALLATION_NAME",
                        "ACTIVITY_TYPE", "PERMIT_REVOCATION_DATE", "ACCOUNT_HOLDER_NAME",
                        "ACCOUNT_HOLDER_LEI", "SNAPSHOT_DATE"}

ETS_ACTIVITY_COLUMNS = {"INSTALLATION_IDENTIFIER", "REGISTRY_CODE", "PERIOD_YEAR",
                        "VERIFIED_EMISSIONS"}


def load_ets(operators_gz: Path, activity_gz: Path) -> dict[str, Any]:
    """Liest die öffentlichen Union-Registry-Auszüge und gruppiert Anlagen nach Kontoinhaber-LEI.

    Nur prüfzifferngültige LEIs zählen (Bindestriche der Registerschreibweise werden
    entfernt). Anlagen ohne LEI bleiben unzugeordnet, auch wenn der Name passen würde.
    «n/a» ist kein verifizierter Wert und wird nicht als 0 gelesen.
    """
    stats: Counter[str] = Counter()
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    snapshot: str | None = None
    with gzip.open(operators_gz, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        require_columns(reader, ETS_OPERATOR_COLUMNS, operators_gz.name)
        for row in reader:
            stats["installations"] += 1
            snapshot = snapshot or row["SNAPSHOT_DATE"] or None
            raw = row["ACCOUNT_HOLDER_LEI"].strip()
            if not raw:
                continue
            stats["with_lei_field"] += 1
            lei = raw.replace("-", "").replace(" ", "").upper()
            if not is_valid_lei(lei):
                stats["invalid_lei"] += 1
                continue
            by_key[(row["REGISTRY_CODE"], row["INSTALLATION_IDENTIFIER"])] = {
                "registry_code": row["REGISTRY_CODE"],
                "installation_id": row["INSTALLATION_IDENTIFIER"],
                "installation_name": row["INSTALLATION_NAME"] or None,
                "activity_type": row["ACTIVITY_TYPE"] or None,
                "permit_revocation_date": row["PERMIT_REVOCATION_DATE"] or None,
                "account_holder_name": row["ACCOUNT_HOLDER_NAME"] or None,
                "account_holder_lei": lei, "verified_emissions": {},
            }
    with gzip.open(activity_gz, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        require_columns(reader, ETS_ACTIVITY_COLUMNS, activity_gz.name)
        for row in reader:
            installation = by_key.get((row["REGISTRY_CODE"], row["INSTALLATION_IDENTIFIER"]))
            if installation is None:
                continue
            try:
                value = float(row["VERIFIED_EMISSIONS"])
                year = int(row["PERIOD_YEAR"])
            except ValueError:
                continue
            installation["verified_emissions"][year] = value
    by_lei: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for installation in by_key.values():
        by_lei[installation["account_holder_lei"]].append(installation)
    stats["with_valid_lei"] = len(by_key)
    stats["distinct_leis"] = len(by_lei)
    return {"snapshot_date": snapshot, "by_lei": dict(by_lei), "stats": dict(stats)}


def summarise_ets(lei: str, installations: list[dict[str, Any]], snapshot_date: str | None,
                  first_year: int | None = None,
                  last_year: int | None = None) -> dict[str, Any] | None:
    """Beleg nur aus Anlagen mit mindestens einem verifizierten Jahreswert im Zeitraum."""
    listed = []
    for item in sorted(installations, key=lambda i: (i["registry_code"], i["installation_id"])):
        values = {year: value for year, value in item["verified_emissions"].items()
                  if (first_year is None or year >= first_year)
                  and (last_year is None or year <= last_year)}
        if not values:
            continue
        latest = max(values)
        listed.append({
            "registry_code": item["registry_code"], "installation_id": item["installation_id"],
            "installation_name": item["installation_name"],
            "activity_type": item["activity_type"],
            "permit_revocation_date": item["permit_revocation_date"],
            "years": [min(values), latest], "latest_year": latest,
            "latest_verified_t_co2e": values[latest],
        })
    if not listed:
        return None
    return {
        "source": "eu_ets", "reporting_lei": lei, "snapshot_date": snapshot_date,
        "account_holder_names": sorted({i["account_holder_name"] for i in installations
                                        if i["account_holder_name"]}),
        "installations": listed,
        "evidence_category": "emission_trading_verified_not_violation",
        "attribution": ETS_ATTRIBUTION,
    }
