"""Wertpapierstamm ISIN → Emittenten-LEI aus SEC-N-PORT-Meldungen (Roadmap Phase 2, D-056).

Grundsatz: Eine ISIN erhält einen LEI nur aus Kennungen, nie aus Namen. Quelle sind die von
den Fonds gemeldeten Emittenten-LEI («as filed»). Bestätigt ist eine Zuordnung erst, wenn
mindestens ``MIN_INDEPENDENT`` unabhängige Fondsgesellschaften denselben LEI melden und
keine meldende Stelle einen anderen LEI nennt. Unsere Regeln, nicht von der SEC:

- **Umfang:** nur Meldungen mit Auswahl «current» (jüngster Stichtag je Fonds, D-054), nur
  Positionen mit gültiger ISIN, ohne Derivate (``DERIVATIVE_ASSET_CATS``: dort nennt der
  gemeldete LEI oft die Gegenpartei oder Börse, nicht den Emittenten der ISIN).
- **Unabhängig:** Zwei Fonds sind *nicht* unabhängig, wenn sie dieselbe CIK haben oder einen
  gemeinsamen Anlageberater laut N-CEN (gleicher LEI, gleiche oberste Mutter laut GLEIF,
  gleiche SEC- oder CRD-Nummer). Gezählt werden die Gruppen, die so entstehen. Ohne N-CEN-
  Angabe bleibt nur die CIK; das wird im Bericht als Abdeckung ausgewiesen.
- **Normalisierung (nur über Kennungen, je Schritt festgehalten):**
  1. GLEIF-Status ``DUPLICATE`` mit Nachfolge-LEI → Nachfolge-LEI (gleicher Rechtsträger).
  2. Fondsanteile: Nennt ein Teil der Meldenden den Trust (Registrant-LEI) und ein anderer
     die Serie desselben Trusts (Serien-LEI laut N-PORT-Meldung des Trusts), zählt beides
     für die Serie. Die Serie ist der genauere Emittent des Anteils.
- **Widerspruch:** Bleiben nach der Normalisierung zwei verschiedene LEI, ist die ISIN
  ``conflict``, auch wenn eine Mehrheit klar ist. Die Art (Nachfolger, Mutter/Tochter,
  inaktiv, übrige) wird beschrieben, aber nicht aufgelöst.
- **GLEIF:** Ein LEI, der nicht in der GLEIF-Liste steht, annulliert ist oder als Duplikat
  ohne Nachfolger geführt wird, wird nie bestätigt. Inaktive Rechtsträger bleiben bestätigt
  (Emittent zum Stichtag), der GLEIF-Status steht daneben.

Die Logik je ISIN (``classify``) ist rein funktional; ``build_security_master`` liest die
N-PORT-Datenbank nur lesend und schreibt eine eigene Datei ``processed/security_master.sqlite``.
"""

from __future__ import annotations

import json
import os
import sqlite3
import statistics
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from itertools import groupby
from pathlib import Path
from typing import Any

from transparenz.ingestion.external import atomic_json
from transparenz.ingestion.gleif_level1 import (
    RR_ARCHIVE_NAME,
    RR_FOLDER,
    RR_SOURCE_KEY,
    LeiRecord,
    latest_snapshot,
    load_lei_records,
)
from transparenz.ingestion.gleif_lookup import load_parent_map
from transparenz.ingestion.sec_ncen_advisers import AdviserRef, load_fund_advisers
from transparenz.ingestion.sec_nport import SOURCE_KEY as NPORT_SOURCE_KEY
from transparenz.services.provenance import ProvenanceError

# Erhöhen, wenn eine Regel ändert; steht in jeder erzeugten Datei.
RULE_VERSION = "2026-11-16.1"
SCHEMA = 1
MIN_INDEPENDENT = 2
DERIVATIVE_ASSET_CATS = frozenset({"DCO", "DCR", "DE", "DFE", "DIR", "DO"})
UNUSABLE_REGISTRATION = {"ANNULLED": "lei_annulled", "DUPLICATE": "lei_duplicate_unresolved"}
MAX_SUCCESSOR_STEPS = 3

STATUSES = ("confirmed", "single_reporter", "conflict", "lei_not_in_gleif", "lei_annulled",
            "lei_duplicate_unresolved", "no_lei_reported")


# ------------------------------------------------------------------------ Unabhängigkeit


def adviser_keys(refs: Iterable[AdviserRef], parents: Mapping[str, Mapping[str, str]]
                 ) -> set[str]:
    """Schlüssel eines Fonds aus seinen Beratern: LEI und Konzern laut GLEIF, SEC-/CRD-Nummer."""
    keys: set[str] = set()
    for ref in refs:
        if ref.lei:
            known = parents.get(ref.lei, {})
            keys.add("lei:" + ref.lei)
            keys.add("lei:" + (known.get("ultimate-parent") or known.get("direct-parent")
                               or ref.lei))
        if ref.sec_file:
            keys.add("sec:" + ref.sec_file)
        if ref.crd:
            keys.add("crd:" + ref.crd)
    return keys


def independent_groups(funds: Iterable[str], keys_of: Mapping[str, Iterable[str]]) -> int:
    """Anzahl Gruppen unter den Fonds: Fonds mit einem gemeinsamen Schlüssel gehören zusammen."""
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    owner: dict[str, str] = {}
    members = list(dict.fromkeys(funds))
    for fund in members:
        parent[fund] = fund
    for fund in members:
        for key in keys_of.get(fund, ()):
            if key in owner:
                a, b = find(fund), find(owner[key])
                if a != b:
                    parent[a] = b
            else:
                owner[key] = fund
    return len({find(f) for f in members})


# ------------------------------------------------------------------------ Regel je ISIN


@dataclass
class Context:
    records: Mapping[str, LeiRecord]
    fund_keys: Mapping[str, frozenset[str]]  # Fonds → Unabhängigkeitsschlüssel (inkl. CIK)
    fund_cik: Mapping[str, str | None]
    series_trusts: Mapping[str, frozenset[str]]  # Serien-LEI → Trust-LEI (N-PORT, as filed)
    parents: Mapping[str, Mapping[str, str]] = field(default_factory=dict)


@dataclass(frozen=True)
class Claim:
    lei_reported: str
    lei: str
    funds: int
    ciks: int
    independent: int
    normalization: str | None


@dataclass(frozen=True)
class Entry:
    isin: str
    lei: str | None
    status: str
    conflict_kind: str | None
    funds: int
    ciks: int
    independent: int
    ciks_rule_confirmed: bool  # Vergleich: wäre bestätigt, wenn jede CIK unabhängig wäre
    funds_without_lei: int
    claims: tuple[Claim, ...]


def _successor(lei: str, records: Mapping[str, LeiRecord]) -> tuple[str, bool]:
    """Nachfolge-LEI für GLEIF-Duplikate (höchstens ``MAX_SUCCESSOR_STEPS`` Schritte)."""
    current, moved = lei, False
    for _ in range(MAX_SUCCESSOR_STEPS):
        rec = records.get(current)
        if rec is None or rec.registration_status != "DUPLICATE" or not rec.successor_lei:
            break
        current, moved = rec.successor_lei, True
    return current, moved


def _ciks(funds: Iterable[str], ctx: Context) -> int:
    return len({ctx.fund_cik.get(f) or "fund:" + f for f in funds})


def _related(a: str, b: str, ctx: Context) -> str:
    ra, rb = ctx.records.get(a), ctx.records.get(b)
    if ra is None or rb is None:
        return "not_in_gleif"
    if ra.successor_lei == b or rb.successor_lei == a:
        return "successor"
    pa, pb = ctx.parents.get(a, {}), ctx.parents.get(b, {})
    if b in pa.values() or a in pb.values():
        return "parent_child"
    top_a = pa.get("ultimate-parent") or pa.get("direct-parent")
    top_b = pb.get("ultimate-parent") or pb.get("direct-parent")
    if top_a and top_a == top_b:
        return "same_group"
    if ctx.series_trusts.get(a, frozenset()) & ctx.series_trusts.get(b, frozenset()):
        return "fund_structure"
    if a in ctx.series_trusts.get(b, ()) or b in ctx.series_trusts.get(a, ()):
        return "fund_structure"
    if ra.entity_status != "ACTIVE" or rb.entity_status != "ACTIVE":
        return "inactive"
    return "other"


def classify(isin: str, reported: Mapping[str | None, set[str]], ctx: Context) -> Entry:
    """Status einer ISIN aus den Meldungen ``{gemeldeter LEI oder None: {Fondsschlüssel}}``."""
    without_lei = set(reported.get(None, set()))
    claims = {lei: set(funds) for lei, funds in reported.items() if lei is not None}
    target: dict[str, tuple[str, str | None]] = {}
    for lei in claims:
        successor, moved = _successor(lei, ctx.records)
        target[lei] = (successor, "gleif_duplicate" if moved else None)
    normalized = {t for t, _ in target.values()}
    for lei, (current, reason) in list(target.items()):
        series = [s for s in normalized if current in ctx.series_trusts.get(s, ())]
        if len(series) == 1 and series[0] != current:
            target[lei] = (series[0], "+".join(filter(None, (reason, "fund_trust_to_series"))))
    merged: dict[str, set[str]] = defaultdict(set)
    for lei, funds in claims.items():
        merged[target[lei][0]] |= funds
    rows = tuple(sorted(
        (Claim(lei_reported=lei, lei=target[lei][0], funds=len(funds), ciks=_ciks(funds, ctx),
               independent=independent_groups(funds, ctx.fund_keys),
               normalization=target[lei][1]) for lei, funds in claims.items()),
        key=lambda c: (-c.independent, -c.funds, c.lei_reported)))
    all_funds = set().union(*claims.values()) if claims else set()
    independent = independent_groups(all_funds, ctx.fund_keys)
    ciks = _ciks(all_funds, ctx)
    common = {"isin": isin, "funds": len(all_funds), "ciks": ciks, "independent": independent,
              "funds_without_lei": len(without_lei - all_funds), "claims": rows}
    if not merged:
        return Entry(lei=None, status="no_lei_reported", conflict_kind=None,
                     ciks_rule_confirmed=False, **common)
    if len(merged) > 1:
        ranked = sorted(merged, key=lambda lei: (
            -independent_groups(merged[lei], ctx.fund_keys), -len(merged[lei]), lei))
        kinds = sorted({_related(ranked[0], other, ctx) for other in ranked[1:]})
        return Entry(lei=None, status="conflict", conflict_kind=",".join(kinds),
                     ciks_rule_confirmed=False, **common)
    (lei,) = merged
    rec = ctx.records.get(lei)
    if rec is None:
        status = "lei_not_in_gleif"
    elif rec.registration_status in UNUSABLE_REGISTRATION:
        status = UNUSABLE_REGISTRATION[rec.registration_status]
    else:
        status = "confirmed" if independent >= MIN_INDEPENDENT else "single_reporter"
    usable = rec is not None and rec.registration_status not in UNUSABLE_REGISTRATION
    return Entry(lei=lei, status=status, conflict_kind=None,
                 ciks_rule_confirmed=usable and ciks >= MIN_INDEPENDENT, **common)


# ------------------------------------------------------------------------ Aufbau

_SCHEMA_SQL = """
CREATE TABLE build_info (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE securities (
    isin TEXT PRIMARY KEY, lei TEXT, status TEXT NOT NULL, conflict_kind TEXT,
    funds INTEGER NOT NULL, ciks INTEGER NOT NULL, independent INTEGER NOT NULL,
    funds_without_lei INTEGER NOT NULL, holdings INTEGER NOT NULL, asset_cat TEXT,
    gleif_entity_status TEXT, gleif_registration_status TEXT, gleif_country TEXT);
CREATE TABLE claims (
    isin TEXT NOT NULL, lei_reported TEXT NOT NULL, lei TEXT NOT NULL, funds INTEGER NOT NULL,
    ciks INTEGER NOT NULL, independent INTEGER NOT NULL, normalization TEXT,
    PRIMARY KEY (isin, lei_reported));
CREATE INDEX ix_securities_lei ON securities (lei);
CREATE INDEX ix_securities_status ON securities (status);
"""

_SCOPE = ("FROM nport_holdings h JOIN nport_submissions s ON s.dataset_version_id = "
          "h.dataset_version_id AND s.quarter = h.quarter AND s.accession = h.accession "
          "WHERE h.dataset_version_id = ? AND s.selection = 'current'")
_NOT_DERIVATIVE = ("COALESCE(h.asset_cat, '') NOT IN ("
                   + ", ".join(f"'{c}'" for c in sorted(DERIVATIVE_ASSET_CATS)) + ")")


def _share(part: int, whole: int) -> dict[str, Any]:
    return {"count": part, "of": whole,
            "percent": round(100 * part / whole, 2) if whole else None}


def open_readonly(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise FileNotFoundError(f"{path} fehlt (zuerst «nport-update»).")
    return sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)


def active_nport_version(conn: sqlite3.Connection) -> tuple[int, str, str | None]:
    row = conn.execute("SELECT id, content_hash, data_as_of FROM dataset_versions WHERE "
                       "source_key = ? AND status = 'active' ORDER BY id DESC",
                       (NPORT_SOURCE_KEY,)).fetchone()
    if row is None:
        raise RuntimeError("Kein aktiver N-PORT-Datenstand.")
    return int(row[0]), str(row[1]), row[2]


def _gleif_records(path: Path, wanted: set[str]) -> tuple[dict[str, LeiRecord], int]:
    records, rows = load_lei_records(path, wanted)
    # Nachfolger von Duplikaten brauchen ihren eigenen Datensatz (zweiter, kleiner Durchgang).
    missing = set()
    for _ in range(MAX_SUCCESSOR_STEPS):
        missing = {r.successor_lei for r in records.values()
                   if r.registration_status == "DUPLICATE" and r.successor_lei
                   and r.successor_lei not in records}
        if not missing:
            break
        more, _ = load_lei_records(path, missing)
        records.update(more)
    return records, rows


@dataclass
class Inputs:
    """Alles, was ``classify`` braucht, plus Herkunft und Kennzahlen für den Bericht."""

    version_id: int
    content_hash: str
    data_as_of: str | None
    ctx: Context
    provenance: dict[str, Any]
    stats: dict[str, Any]


def load_inputs(conn: sqlite3.Connection, data_dir: Path) -> Inputs:
    version_id, content_hash, data_as_of = active_nport_version(conn)
    fund_cik: dict[str, str | None] = {}
    series_trusts: dict[str, set[str]] = defaultdict(set)
    for fund_key, cik, series_lei, registrant_lei, selection in conn.execute(
            "SELECT fund_key, cik, series_lei, registrant_lei, selection FROM nport_submissions "
            "WHERE dataset_version_id = ?", (version_id,)):
        if selection == "current" and fund_key:
            fund_cik[fund_key] = cik
        if series_lei and registrant_lei and series_lei != registrant_lei:
            series_trusts[series_lei].add(registrant_lei)
    claim_leis = {r[0] for r in conn.execute(
        f"SELECT DISTINCT h.issuer_lei {_SCOPE} AND h.isin IS NOT NULL "
        f"AND h.issuer_lei IS NOT NULL AND {_NOT_DERIVATIVE}", (version_id,))}

    advisers = load_fund_advisers(data_dir)
    gleif = latest_snapshot(data_dir)
    rr = latest_snapshot(data_dir, RR_FOLDER, RR_ARCHIVE_NAME, RR_SOURCE_KEY)
    if gleif is None or rr is None:
        raise ProvenanceError("GLEIF-Liste Level 1 und Beziehungsdatei (Level 2) werden "
                              "lokal gebraucht (raw/external/gleif_*_golden_copy).")
    records, gleif_rows = _gleif_records(data_dir / gleif.path, claim_leis)
    parents = load_parent_map(data_dir / rr.path, claim_leis | advisers.adviser_leis())

    fund_keys: dict[str, frozenset[str]] = {}
    with_adviser = 0
    for fund, cik in fund_cik.items():
        keys = adviser_keys(advisers.by_fund.get(fund, ()), parents)
        with_adviser += bool(keys)
        if cik:
            keys.add("cik:" + cik)
        fund_keys[fund] = frozenset(keys)
    ctx = Context(records=records, fund_keys=fund_keys, fund_cik=fund_cik,
                  series_trusts={k: frozenset(v) for k, v in series_trusts.items()},
                  parents=parents)
    provenance = {
        "nport": {"source_key": NPORT_SOURCE_KEY, "dataset_version_id": version_id,
                  "content_hash": content_hash, "data_as_of": data_as_of},
        "gleif_level1": gleif.as_dict(),
        "gleif_relationships": rr.as_dict(),
        "sec_ncen": [a.as_dict() for a in advisers.archives],
    }
    stats = {
        "funds_current": len(fund_cik),
        "funds_with_ncen_adviser": _share(with_adviser, len(fund_cik)),
        "ncen": advisers.stats,
        "claim_leis": len(claim_leis),
        "claim_leis_in_gleif": _share(len(claim_leis & set(records)), len(claim_leis)),
        "gleif_rows_read": gleif_rows,
        "adviser_leis": len(advisers.adviser_leis()),
        "leis_with_gleif_parent": len(parents),
        "series_with_trust_lei": len(series_trusts),
    }
    return Inputs(version_id, content_hash, data_as_of, ctx, provenance, stats)


def iter_reports(conn: sqlite3.Connection, version_id: int):
    """(ISIN, {LEI|None: {Fonds}}, Positionen, häufigste Anlageart) je ISIN, sortiert."""
    cursor = conn.execute(
        f"SELECT h.isin, h.issuer_lei, s.fund_key, h.asset_cat, COUNT(*) {_SCOPE} "
        f"AND h.isin IS NOT NULL AND {_NOT_DERIVATIVE} GROUP BY 1, 2, 3, 4 ORDER BY 1",
        (version_id,))
    for isin, rows in groupby(cursor, key=lambda r: r[0]):
        reported: dict[str | None, set[str]] = defaultdict(set)
        cats: Counter = Counter()
        holdings = 0
        for _, lei, fund, cat, n in rows:
            reported[lei].add(fund)
            cats[cat or "(leer)"] += n
            holdings += n
        yield isin, reported, holdings, min(cats, key=lambda c: (-cats[c], c))


def _write_rows(out: sqlite3.Connection, batch: list[tuple[Entry, int, str]],
                records: Mapping[str, LeiRecord]) -> None:
    sec_rows, claim_rows = [], []
    for entry, holdings, cat in batch:
        rec = records.get(entry.lei) if entry.lei else None
        sec_rows.append((entry.isin, entry.lei, entry.status, entry.conflict_kind, entry.funds,
                         entry.ciks, entry.independent, entry.funds_without_lei, holdings, cat,
                         rec.entity_status if rec else None,
                         rec.registration_status if rec else None, rec.country if rec else None))
        claim_rows.extend((entry.isin, c.lei_reported, c.lei, c.funds, c.ciks, c.independent,
                           c.normalization) for c in entry.claims)
    out.executemany("INSERT INTO securities VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    sec_rows)
    out.executemany("INSERT INTO claims VALUES (?, ?, ?, ?, ?, ?, ?)", claim_rows)


@dataclass
class _Tally:
    status: Counter = field(default_factory=Counter)
    status_holdings: Counter = field(default_factory=Counter)
    conflict_kind: Counter = field(default_factory=Counter)
    conflict_support: Counter = field(default_factory=Counter)
    normalization: Counter = field(default_factory=Counter)
    by_cat: dict[str, Counter] = field(default_factory=lambda: defaultdict(Counter))
    by_prefix: dict[str, Counter] = field(default_factory=lambda: defaultdict(Counter))
    confirmed_country: Counter = field(default_factory=Counter)
    confirmed_gleif: Counter = field(default_factory=Counter)
    confirmed_leis: set[str] = field(default_factory=set)
    independent_confirmed: list[int] = field(default_factory=list)
    cik_rule_confirmed: int = 0
    cik_rule_only: int = 0

    def add(self, entry: Entry, holdings: int, cat: str,
            records: Mapping[str, LeiRecord]) -> None:
        self.status[entry.status] += 1
        self.status_holdings[entry.status] += holdings
        self.by_cat[cat][entry.status] += 1
        self.by_prefix[entry.isin[:2]][entry.status] += 1
        for claim in entry.claims:
            if claim.normalization:
                self.normalization[claim.normalization] += 1
        self.cik_rule_confirmed += entry.ciks_rule_confirmed
        if entry.ciks_rule_confirmed and entry.status != "confirmed":
            self.cik_rule_only += 1
        if entry.status == "conflict":
            self.conflict_kind[entry.conflict_kind] += 1
            support = sorted((c.independent for c in entry.claims), reverse=True)
            self.conflict_support[(min(support[0], 5), min(sum(support[1:]), 3))] += 1
        if entry.status == "confirmed" and entry.lei:
            rec = records[entry.lei]
            self.confirmed_leis.add(entry.lei)
            self.confirmed_country[rec.country or "(leer)"] += 1
            self.confirmed_gleif[f"{rec.entity_status}/{rec.registration_status}"] += 1
            self.independent_confirmed.append(entry.independent)


def _report(tally: _Tally, inputs: Inputs, total_holdings: int, derivative_holdings: int,
            built_at: str, seconds: float) -> dict[str, Any]:
    isins = sum(tally.status.values())
    with_lei = isins - tally.status["no_lei_reported"]
    in_scope = sum(tally.status_holdings.values())

    def top(counter_map: dict[str, Counter], n: int = 20) -> list[dict[str, Any]]:
        rows = sorted(counter_map.items(), key=lambda kv: -sum(kv[1].values()))[:n]
        return [{"key": k, "isins": sum(c.values()),
                 "with_lei": sum(c.values()) - c["no_lei_reported"],
                 "confirmed": _share(c["confirmed"], sum(c.values()) - c["no_lei_reported"])}
                for k, c in rows]

    ind = tally.independent_confirmed
    return {
        "report_schema": SCHEMA,
        "rule_version": RULE_VERSION,
        "built_at": built_at,
        "build_seconds": round(seconds, 1),
        "inputs": inputs.provenance,
        "input_stats": inputs.stats,
        "rules": {
            "min_independent": MIN_INDEPENDENT,
            "excluded_asset_cats": sorted(DERIVATIVE_ASSET_CATS),
            "independent": "Fonds mit gleicher CIK oder gemeinsamem Anlageberater laut N-CEN "
                           "(LEI, oberste GLEIF-Mutter, SEC- oder CRD-Nummer) zählen als "
                           "eine Gruppe.",
            "conflict": "Jeder abweichende LEI nach Normalisierung = Widerspruch, auch "
                        "gegen eine klare Mehrheit.",
        },
        "holdings": {
            "current_filings": total_holdings,
            "derivatives_excluded": derivative_holdings,
            "in_scope_with_isin": in_scope,
            "in_scope_share_of_current": _share(in_scope, total_holdings),
            "by_status": {k: _share(v, in_scope) for k, v in tally.status_holdings.most_common()},
        },
        "isins": {
            "total": isins,
            "with_reported_lei": with_lei,
            "by_status": {k: _share(tally.status[k], isins) for k in STATUSES},
            "confirmed_of_with_lei": _share(tally.status["confirmed"], with_lei),
            "distinct_confirmed_leis": len(tally.confirmed_leis),
            "independent_groups_confirmed": {
                "median": statistics.median(ind) if ind else None,
                "exactly_2": _share(sum(1 for i in ind if i == 2), len(ind)),
                "5_or_more": _share(sum(1 for i in ind if i >= 5), len(ind))},
        },
        "comparison_cik_rule": {
            "note": "Wie viele ISIN wären bestätigt, wenn jede CIK als unabhängig gälte "
                    "(Plan vom 15.11.2026)?",
            "confirmed_cik_rule": tally.cik_rule_confirmed,
            "confirmed_adviser_rule": tally.status["confirmed"],
            "only_under_cik_rule": tally.cik_rule_only,
        },
        "normalization_claims": dict(tally.normalization.most_common()),
        "conflicts": {
            "by_kind": dict(tally.conflict_kind.most_common()),
            "support_top_vs_others": [
                {"top_independent": f"{a}{'+' if a == 5 else ''}",
                 "others_independent": f"{b}{'+' if b == 3 else ''}", "isins": n}
                for (a, b), n in sorted(tally.conflict_support.items())],
        },
        "confirmed_gleif_status": dict(tally.confirmed_gleif.most_common()),
        "by_asset_cat": top(tally.by_cat, 30),
        "by_isin_prefix": top(tally.by_prefix),
        "confirmed_by_gleif_country": dict(tally.confirmed_country.most_common(20)),
        "notes": [
            "Alle Zahlen aus dem aktiven N-PORT-Stand (nur «current»), ohne Derivate.",
            "Bestätigt heisst: von mindestens zwei unabhängigen Fondsgesellschaften gleich "
            "gemeldet, ohne Gegenmeldung, LEI bei GLEIF vorhanden und nicht annulliert. Das "
            "ist eine Referenz aus Fondsmeldungen, keine Garantie; gemeinsame Datenlieferanten "
            "der Gesellschaften sind nicht erkennbar.",
            "Nur Papiere, die US-registrierte Fonds halten; kein Weltbestand.",
        ],
    }


def build_security_master(nport_db: Path, data_dir: Path, out_path: Path,
                          report_path: Path) -> dict[str, Any]:
    """Wertpapierstamm neu aufbauen (alte Datei wird erst am Ende ersetzt)."""
    started = datetime.now(UTC)
    conn = open_readonly(nport_db)
    try:
        inputs = load_inputs(conn, data_dir)
        v = inputs.version_id
        total = conn.execute(f"SELECT COUNT(*) {_SCOPE}", (v,)).fetchone()[0]
        derivatives = conn.execute(f"SELECT COUNT(*) {_SCOPE} AND h.isin IS NOT NULL "
                                   f"AND NOT {_NOT_DERIVATIVE}", (v,)).fetchone()[0]
        out_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = out_path.with_name(out_path.name + ".tmp")
        tmp.unlink(missing_ok=True)
        out = sqlite3.connect(tmp)
        try:
            out.executescript(_SCHEMA_SQL)
            tally = _Tally()
            batch: list[tuple[Entry, int, str]] = []
            for isin, reported, holdings, cat in iter_reports(conn, v):
                entry = classify(isin, reported, inputs.ctx)
                tally.add(entry, holdings, cat, inputs.ctx.records)
                batch.append((entry, holdings, cat))
                if len(batch) >= 5000:
                    _write_rows(out, batch, inputs.ctx.records)
                    batch = []
            _write_rows(out, batch, inputs.ctx.records)
            built_at = datetime.now(UTC).isoformat(timespec="seconds")
            report = _report(tally, inputs, total, derivatives, built_at,
                             (datetime.now(UTC) - started).total_seconds())
            info = {"schema": SCHEMA, "rule_version": RULE_VERSION, "built_at": built_at,
                    "inputs": inputs.provenance}
            out.executemany("INSERT INTO build_info VALUES (?, ?)",
                            [(k, json.dumps(val, ensure_ascii=False, sort_keys=True))
                             for k, val in info.items()])
            out.commit()
        finally:
            out.close()
        os.replace(tmp, out_path)
    finally:
        conn.close()
    atomic_json(report_path, report)
    return report


def lookup(db_path: Path, isin: str) -> dict[str, Any] | None:
    """Eintrag einer ISIN samt aller gemeldeten LEI (für die Befehlszeile)."""
    conn = open_readonly(db_path)
    try:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM securities WHERE isin = ?", (isin.upper(),)).fetchone()
        if row is None:
            return None
        claims = [dict(r) for r in conn.execute(
            "SELECT lei_reported, lei, funds, ciks, independent, normalization FROM claims "
            "WHERE isin = ? ORDER BY independent DESC, funds DESC", (isin.upper(),))]
        info = {k: json.loads(v) for k, v in conn.execute("SELECT key, value FROM build_info")}
        return {**dict(row), "claims": claims, "rule_version": info.get("rule_version"),
                "built_at": info.get("built_at")}
    finally:
        conn.close()


def confirmed_reference(db_path: Path, isins: Iterable[str]) -> tuple[dict[str, str],
                                                                       dict[str, Any]]:
    """Bestätigte ISIN → LEI für die gegebenen ISIN, dazu Regelversion und Erstellzeit."""
    wanted = sorted({i.upper() for i in isins if i})
    conn = open_readonly(db_path)
    try:
        found: dict[str, str] = {}
        for i in range(0, len(wanted), 500):
            chunk = wanted[i:i + 500]
            marks = ", ".join("?" * len(chunk))
            found.update(conn.execute(
                f"SELECT isin, lei FROM securities WHERE status = 'confirmed' "
                f"AND isin IN ({marks})", chunk).fetchall())
        info = {k: json.loads(v) for k, v in conn.execute("SELECT key, value FROM build_info")}
    finally:
        conn.close()
    return found, {"rule_version": info.get("rule_version"), "built_at": info.get("built_at")}
