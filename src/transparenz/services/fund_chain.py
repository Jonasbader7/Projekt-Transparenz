"""Kette «Fondsposition → Unternehmen → Beleg»: Zuordnung, Konzernbeziehungen, Belege und
Zusammenfassung je Fonds.
"""
from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Collection, Mapping
from dataclasses import asdict
from typing import Any

from transparenz.entities.identifiers import is_valid_lei
from transparenz.entities.labels import GEM_CAPACITY_LABELS, GEM_PHASE_LABELS
from transparenz.ingestion.eu_ets import ETS_ATTRIBUTION, ETS_TERMS_URL, summarise_ets
from transparenz.ingestion.fi_holdings import FI_ATTRIBUTION, FI_TERMS_URL, Fund, Position
from transparenz.ingestion.gem import (
    GEM_LICENCE_URL,
    GEM_STAKES,
    classify_gem_assets,
    summarise_gem,
)
from transparenz.ingestion.gleif_lookup import gleif_entry
from transparenz.services.entity_matching import (
    GleifCandidate,
    MatchResult,
    allowed_countries,
    match_by_name,
    match_by_register,
    names_agree,
    position_region,
    register_queries,
    security_query,
)
from transparenz.services.fund_findings import coal_finding, expansion_finding, sensitivity
from transparenz.services.ownership import is_financial_sector

PRTR_ATTRIBUTION = (
    "Bundesamt für Umwelt BAFU, Schadstofffreisetzungs- und Transferregister der Schweiz "
    "(SwissPRTR), https://opendata.swiss/en/dataset/"
    "schadstofffreisetzungs-und-transferregister-der-schweiz-swissprtr"
)


# -------------------------------------------------------------------- lokale Bestände


def index_candidates(candidates: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in candidates:
        if row.get("isin"):
            index[row["isin"].upper()].append(row)
    return index


def index_emissions(emissions: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in emissions:
        if row.get("company_key") and row.get("mapping_status") == "exact_uid_match":
            index[row["company_key"]].append(row)
    return index


def position_names(position: Position, hits: list[dict[str, Any]]) -> list[str]:
    """Namen, mit denen gesucht wird: Positionsname und (falls vorhanden) Wikidata-Bezeichnung."""
    names = [position.name, *(h.get("name") for h in hits
                              if h.get("name") and not re.fullmatch(r"Q\d+", h["name"]))]
    return list(dict.fromkeys(n for n in names if n))


def search_plan(fund: Fund, candidates: dict[str, list[dict[str, Any]]],
                profiles: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    """Welche GLEIF-Suchen ein Lauf braucht: Namen je Position und Registernummern."""
    names, numbers = [], []
    for position in fund.positions:
        if not position.isin_valid:
            continue
        hits = candidates.get(position.isin or "", [])
        names.extend(security_query(n) for n in position_names(position, hits))
        for hit in hits:
            claims = profiles.get(hit["wikidata_id"], {}).get("register", {})
            numbers.extend(number for _, number, _ in register_queries(claims))
    return {"entity.names": [n for n in dict.fromkeys(names) if len(n) >= 3],
            "entity.registeredAs": list(dict.fromkeys(numbers))}


def auto_match(fund: Fund, candidates: dict[str, list[dict[str, Any]]],
               profiles: dict[str, dict[str, Any]], cache: dict[str, Any],
               parent_of: dict[str, set[str]] | None = None) -> dict[str, dict[str, Any]]:
    """Reine Funktion: Ergebnis der Verfahren «register» und «gleif_name_country» je ISIN.

    Läuft für jede Position mit gültiger ISIN, auch für bereits über Wikidata zugeordnete:
    Dort dient das Ergebnis als unabhängige Gegenprobe und zur Messung der Präzision.
    """
    out: dict[str, dict[str, Any]] = {}
    for position in fund.positions:
        if not position.isin_valid or position.isin in out:
            continue
        hits = candidates.get(position.isin or "", [])
        countries = allowed_countries(position.isin, position.issuer_country)
        searched = [cache.get(f"entity.names:{security_query(n)}")
                    for n in position_names(position, hits)]
        searched = [s for s in searched if s is not None]
        entities: dict[str, GleifCandidate] = {}
        for result in searched:
            for record in result["records"]:
                entities.setdefault(record["lei"], GleifCandidate.from_dict(record))
        if searched:
            name = match_by_name(position_names(position, hits), countries, entities.values(),
                                 truncated=all(s["truncated"] for s in searched),
                                 parent_of=parent_of)
        else:
            name = MatchResult("gleif_name_country", None, "not_searched",
                               "Namenssuche nicht durchgeführt.")
        queries = [q for hit in hits for q in register_queries(
            profiles.get(hit["wikidata_id"], {}).get("register", {}))]
        found = {number: [GleifCandidate.from_dict(r) for r in
                          cache.get(f"entity.registeredAs:{number}", {}).get("records", [])]
                 for _, number, _ in queries}
        if any(f"entity.registeredAs:{number}" not in cache for _, number, _ in queries):
            register = MatchResult("register", None, "not_searched",
                                   "Registernummernsuche nicht durchgeführt.")
        else:
            register = match_by_register(queries, found, countries)
        for match in (name, register):
            for lei in match.candidates:
                if lei not in entities:
                    for records in found.values():
                        entities.update({c.lei: c for c in records if c.lei == lei})
        out[position.isin] = {
            "name": name.to_dict(), "register": register.to_dict(),
            "entities": {lei: entities[lei].to_dict() for lei in
                         {*name.candidates, *register.candidates} if lei in entities}}
    return out


# ------------------------------------------------------------------------------ Kette


def summarise_emissions(company_key: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    years = sorted({r["year"] for r in rows})
    latest = years[-1]
    return {
        "source": "swissprtr",
        "reporting_company_key": company_key,
        "facility_uids": sorted({r["uid_facility"] for r in rows if r.get("uid_facility")}),
        "years": [years[0], latest], "rows_total": len(rows),
        "data_as_of": rows[0].get("data_as_of"),
        "latest_year": latest,
        "latest_year_rows": [
            {"pollutant_name": r.get("pollutant_name"), "medium": r.get("medium"),
             "value": r.get("value"), "unit": r.get("unit")}
            for r in rows if r["year"] == latest],
        "evidence_category": "emission_register_not_violation",
        "attribution": PRTR_ATTRIBUTION,
    }


def gleif_names(entry: dict[str, Any] | None) -> list[str]:
    if not entry:
        return []
    return [entry.get("legal_name"), *(o.get("name") for o in entry.get("other_names") or [])]


def name_check(holder_names: list[str], legal_names: list[str | None] | str | None) -> str:
    """Nur zur Sichtprüfung: beeinflusst nie die Zuordnung (die läuft allein über den LEI)."""
    if isinstance(legal_names, str) or legal_names is None:
        legal_names = [legal_names]
    result = names_agree(list(holder_names or []), list(legal_names))
    return "not_checked" if result is None else ("shared_word" if result else "different")


CONFIRMED_MAPPING = ("consistent", "consistent_lapsed", "confirmed_by_decision",
                     "confirmed_by_register", "confirmed_by_agreement", "auto_by_name")

REVIEW_SIGNALS = ("name_mismatch", "ambiguous", "name_proposal")


def review_queue(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Offene Ja/Nein-Fragen: Positionen, die nur ein menschlicher Entscheid klären kann.

    Je Fall alle Kandidaten mit dem, was man zum Entscheiden braucht (Positionsname, Namen
    laut Wikidata, Rechtsname und frühere Namen laut GLEIF). Grösstes Fondsgewicht zuerst.
    «LEI bei GLEIF unbekannt» fehlt bewusst: Das kann kein Entscheid heilen.
    """
    queue = []
    for row in rows:
        if row["mapping_confidence"] not in REVIEW_SIGNALS:
            continue
        company = row["company"]
        rejected = set(company.get("rejected_leis", []))
        queue.append({
            "isin": row["isin"], "position_name": row["name"],
            "weight_percent": row["weight_percent"], "signal": row["mapping_confidence"],
            "wikidata_ids": company["wikidata_ids"], "wikidata_names": company["wikidata_names"],
            "candidates": [{"lei": lei, **{key: (company["gleif"].get(lei) or {}).get(key)
                                          for key in ("legal_name", "registration_status")},
                            "other_names": [o.get("name") for o in (company["gleif"].get(lei)
                                            or {}).get("other_names") or []]}
                           for lei in company["leis"] if lei not in rejected]})
    return sorted(queue, key=lambda case: -(case["weight_percent"] or 0))


TIMING_BLOCKS = ("relationship_start_unknown", "relationship_not_valid_at_fund_date",
                 "outside_relationship_period")

BLOCK_PRIORITY = ("identity_conflict", "position_mapping_unconfirmed", *TIMING_BLOCKS)


def mapping_confidence(position_name: str, lei: str, names: dict[str, Any],
                       names_checked: set[str]) -> str:
    entry = names.get(lei)
    if entry is None:
        return "lei_not_in_gleif" if lei in names_checked else "lei_not_checked"
    agree = names_agree([position_name], gleif_names(entry))
    if agree is None:
        return "lei_not_checked"
    if not agree:
        return "name_mismatch"
    return "consistent" if entry.get("registration_status") == "ISSUED" else "consistent_lapsed"


def relationship_timing(link: dict[str, Any], quarter_end: str) -> dict[str, Any]:
    """Ordnet eine Konzernbeziehung zeitlich ein (Beginn/Ende laut GLEIF «RELATIONSHIP_PERIOD»).

    Ein Emissionsjahr gilt nur als zurechenbar, wenn die Beziehung das ganze Kalenderjahr
    bestand. Fällt der gemeldete Beginn auf das Datum der LEI-Registrierung, ist er vermutlich
    nur der früheste dokumentierte Tag; die Beziehung kann älter sein. Das wird angezeigt,
    aber nicht zu Gunsten einer Zurechnung ausgelegt.
    """
    start, end = link.get("relationship_start"), link.get("relationship_end")
    timing: dict[str, Any] = {
        "start": start, "end": end,
        "start_is_registration_date": bool(
            start and start == link.get("registration_initial_date")),
        "registration_last_update": link.get("registration_last_update"),
        "valid_at_fund_date": None, "first_full_year": None, "last_full_year": None,
    }
    if not start:
        timing["status"] = "relationship_start_unknown"
        return timing
    timing["valid_at_fund_date"] = start <= quarter_end and (end is None or end >= quarter_end)
    timing["first_full_year"] = int(start[:4]) + (0 if start[5:] == "01-01" else 1)
    if end:
        timing["last_full_year"] = int(end[:4]) - (0 if end[5:] == "12-31" else 1)
    timing["status"] = ("ok" if timing["valid_at_fund_date"]
                        else "relationship_not_valid_at_fund_date")
    return timing


def evidence_for(lei: str, emissions: dict[str, list[dict[str, Any]]],
                 ets: dict[str, Any] | None, first_year: int | None = None,
                 last_year: int | None = None) -> list[dict[str, Any]]:
    """Belege, die ein Rechtsträger mit diesem LEI selbst hat (je Quelle höchstens einer)."""
    def in_range(year: int) -> bool:
        return (first_year is None or year >= first_year) and (last_year is None
                                                               or year <= last_year)

    found = []
    own = [r for r in emissions.get(f"lei:{lei}", []) if in_range(r["year"])]
    if own:
        found.append(summarise_emissions(f"lei:{lei}", own))
    installations = (ets or {}).get("by_lei", {}).get(lei)
    if installations:
        summary = summarise_ets(lei, installations, ets.get("snapshot_date"), first_year,
                                last_year)
        if summary:
            found.append(summary)
    return found


def _finish(item: dict[str, Any], blocks: list[str]) -> dict[str, Any]:
    item["blocking"] = sorted(set(blocks), key=BLOCK_PRIORITY.index)
    item["status"] = item["blocking"][0] if item["blocking"] else "confirmed"
    return item


def name_contradicts_reference(auto: Mapping[str, Any] | None, reference_lei: str | None
                               ) -> bool:
    """Nennt die Namenssuche einen anderen LEI als der bestätigte N-PORT-Konsens?"""
    name = (auto or {}).get("name") or {}
    return bool(reference_lei and name.get("status") == "accepted" and name.get("lei")
                and name["lei"] != reference_lei)


def name_released_for(position: Position, released: bool | Collection[str]) -> bool:
    """Wirkt die Namenssuche für diese Position? Freigabe gesamt oder je Region (D-058)."""
    if isinstance(released, bool):
        return released
    return position_region(position.issuer_country, position.isin) in set(released)


def _assign(row: dict[str, Any], status: str, confidence: str | None = None) -> None:
    row["mapping_status"] = status
    row["mapping_confidence"] = confidence or status


def resolve_position(position: Position, hits: list[dict[str, Any]],
                     decided: dict[str, str], names: dict[str, Any], names_checked: set[str],
                     auto: dict[str, Any] | None, name_released: bool,
                     row: dict[str, Any]) -> str | None:
    """Ordnet eine Position einem LEI zu und setzt Status und Sicherheitsstufe in ``row``.

    Reihenfolge: menschlicher Entscheid (Korrektur) → Wikidata-Kennung (ISIN → LEI) →
    Registernummer → GLEIF-Namenssuche mit Land (nur wenn das Verfahren freigegeben ist).
    Zwei unabhängige Wege, die auf denselben LEI zeigen, lösen Mehrdeutigkeit und
    Namensabweichung auf («confirmed_by_agreement»). Gibt den LEI oder ``None`` zurück.
    """
    approved = sorted(lei for lei, answer in decided.items() if answer == "yes")
    rejected = {lei for lei, answer in decided.items() if answer == "no"}
    auto = auto or {}
    by_name = auto.get("name") or {}
    by_register = auto.get("register") or {}
    name_lei = by_name.get("lei") if by_name.get("status") == "accepted" else None
    register_lei = by_register.get("lei") if by_register.get("status") == "accepted" else None
    candidate_leis = sorted({lei.upper() for hit in hits
                             for lei in hit["claims"].get("P1278", []) if is_valid_lei(lei)})
    leis = [lei for lei in candidate_leis if lei not in rejected]
    items = sorted({hit["wikidata_id"] for hit in hits})
    row["auto_match"] = {"name": by_name or None, "register": by_register or None,
                         "name_released": name_released}

    def company(shown: list[str], source: str) -> dict[str, Any]:
        return {"wikidata_ids": items, "wikidata_names": sorted({h["name"] for h in hits}),
                "leis": shown, "rejected_leis": sorted(rejected & set(candidate_leis)),
                "source": source,
                "gleif": {lei: names.get(lei) for lei in shown if names.get(lei)}}

    if approved:
        # Ein menschlicher Entscheid geht vor. Er kann keinen LEI gültig machen, den GLEIF
        # nicht führt.
        row["company"] = company(sorted({*candidate_leis, *approved}), (
            "Wikidata (CC0), exakter ISIN-Abgleich" if hits
            else "eigener Entscheid (kein Eintrag in Wikidata)"))
        lei = approved[0]
        if lei in names_checked and lei not in names:
            _assign(row, "candidate_lei_not_in_gleif", "lei_not_in_gleif")
            return None
        row["mapping_signal"] = ("ambiguous" if len(items) != 1 or len(candidate_leis) > 1
                                 else mapping_confidence(position.name, lei, names,
                                                         names_checked))
        _assign(row, "confirmed_by_decision")
        return lei
    if hits:
        row["company"] = company(candidate_leis, "Wikidata (CC0), exakter ISIN-Abgleich")
    if candidate_leis and not leis:
        _assign(row, "rejected_by_decision")
        return None
    if leis and (len(items) != 1 or len(leis) > 1):
        if name_released and name_lei in leis:
            row["company"]["leis"] = [name_lei]
            row["company"]["gleif"] = ({name_lei: names[name_lei]} if names.get(name_lei)
                                       else {})
            row["mapping_signal"] = "ambiguous"
            _assign(row, "confirmed_by_agreement")
            return name_lei
        _assign(row, "ambiguous_candidate", "ambiguous")
        return None
    if leis:
        lei = leis[0]
        if lei in names_checked and lei not in names:
            _assign(row, "candidate_lei_not_in_gleif", "lei_not_in_gleif")
            return None
        confidence = mapping_confidence(position.name, lei, names, names_checked)
        if confidence == "name_mismatch" and name_released and name_lei == lei:
            row["mapping_signal"] = "name_mismatch"
            _assign(row, "confirmed_by_agreement")
            return lei
        _assign(row, "unverified_candidate_with_lei", confidence)
        return lei
    # Keine Wikidata-Kennung: Registernummer, dann (falls freigegeben) Namenssuche.
    for method, lei, status, source in (
            ("register", register_lei, "confirmed_by_register",
             "GLEIF (CC0), gleiche Registernummer wie in Wikidata (CC0)"),
            ("name", name_lei if name_released else None, "auto_by_name",
             "GLEIF (CC0), Namenssuche mit Sitzland, Verfahren freigegeben")):
        if lei and lei not in rejected:
            row["company"] = {**company([lei], source), "method": method}
            row["mapping_signal"] = "no_lei" if hits else "unknown"
            _assign(row, status)
            return lei
    if name_lei and name_lei not in rejected:
        row["company"] = {**company([name_lei], "Vorschlag der GLEIF-Namenssuche (Verfahren "
                                    "nicht freigegeben)"), "method": "name"}
        _assign(row, "name_proposal")
        return None
    if hits:
        _assign(row, "candidate_without_lei", "no_lei")
    else:
        row["company"] = None
        _assign(row, "unknown_no_mapping_source", "unknown")
    return None


def build_chain(fund: Fund, candidates: dict[str, list[dict[str, Any]]],
                emissions: dict[str, list[dict[str, Any]]],
                gleif: dict[str, Any] | None, ets: dict[str, Any] | None = None,
                group_links: list[dict[str, Any]] | None = None,
                gem: dict[str, Any] | None = None,
                decisions: dict[str, dict[str, str]] | None = None,
                auto: dict[str, dict[str, Any]] | None = None,
                name_released: bool | Collection[str] = False,
                profiles: dict[str, dict[str, Any]] | None = None,
                rules: dict[str, Any] | None = None,
                reference: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Reine Funktion: verbindet Positionen, Kandidaten, Belege und GLEIF-Beziehungen.

    Jeder Beleg erhält einen Status. «confirmed» nur, wenn die Position widerspruchsfrei
    zugeordnet ist, kein Identitätskonflikt im Register vorliegt und (bei Tochterfirmen) die
    Konzernbeziehung im Emissionsjahr bestand. Alles andere bleibt sichtbar, zählt aber nicht.

    ``decisions`` (ISIN → LEI → «yes»/«no») sind gespeicherte menschliche Entscheide.
    ``auto`` sind die Ergebnisse der automatischen Verfahren (``auto_match``); die Namenssuche
    wirkt nur mit ``name_released``: ``True``/``False`` für alle Positionen oder eine Menge
    freigegebener Regionen (``entity_matching.position_region``, D-058). ``reference``
    (ISIN → bestätigter LEI aus dem N-PORT-Konsens): Nennt die Namenssuche einen anderen LEI,
    wirkt sie für diese Position nicht – ein Name wirkt nie gegen eine Kennung. ``profiles``
    liefert die Branche je Wikidata-Eintrag (Finanzinstitut ja/nein für die
    Beziehungstypen). ``rules`` enthält je Kriterium die Beteiligungsschwelle und die
    Wirkung der Kategorien aus criteria.toml.
    """
    names = dict((gleif or {}).get("names", {}))
    for result in (auto or {}).values():
        for lei, entity in result.get("entities", {}).items():
            names.setdefault(lei, gleif_entry(entity))
    names_checked = set((gleif or {}).get("names_checked", [])) | {
        lei for result in (auto or {}).values() for lei in result.get("entities", {})}
    rules = rules or {}
    children: dict[str, list[dict[str, Any]]] = defaultdict(list)
    known: set[tuple[str, str, str]] = set()
    for link in [*(gleif or {}).get("parents", []), *(group_links or [])]:
        key = (link["child_lei"], link.get("parent_lei") or "", link["kind"])
        if link.get("parent_lei") and key not in known:
            known.add(key)
            children[link["parent_lei"]].append(link)

    rows: list[dict[str, Any]] = []
    relationships: list[dict[str, Any]] = []
    for position in fund.positions:
        row: dict[str, Any] = {**asdict(position), "mapping_status": "unknown_no_mapping_source",
                               "mapping_confidence": "unknown", "company": None,
                               "evidence": [], "group_hints": [], "gem": None, "coal": None,
                               "expansion": None}
        rows.append(row)
        if not position.isin_valid:
            row["mapping_status"] = row["mapping_confidence"] = "no_valid_isin"
            continue
        hits = candidates.get(position.isin or "", [])
        position_auto = (auto or {}).get(position.isin or "")
        released = name_released_for(position, name_released)
        contradicts = name_contradicts_reference(position_auto, (reference or {}).get(
            position.isin or ""))
        lei = resolve_position(position, hits, (decisions or {}).get(position.isin or "", {}),
                               names, names_checked, position_auto,
                               released and not contradicts, row)
        if contradicts:
            row["auto_match"]["name_contradicts_reference"] = True
        if lei is None:
            continue
        industries = sorted({label for item in (row.get("company") or {}).get("wikidata_ids", [])
                             for label in (profiles or {}).get(item, {}).get("industries", [])})
        financial = is_financial_sector(industries)
        if row.get("company") is not None:
            row["company"]["industries"] = industries
            row["company"]["financial_institution"] = financial
            row["company"]["lei"] = lei
        position_block = ([] if row["mapping_confidence"] in CONFIRMED_MAPPING
                          else ["position_mapping_unconfirmed"])
        if gem is not None and not position_block:
            # GEM nur für widerspruchsfrei zugeordnete Positionen; fehlt die Firma bei GEM,
            # heisst das «keine Hinweise in GEM», nie «keine Kohle».
            assets = classify_gem_assets(gem["assets"].get(lei, []), financial,
                                         gem.get("listed", {}))
            row["gem"] = summarise_gem(lei, gem, assets)
            coal_rule = rules.get("kohle", {})
            exp_rule = rules.get("fossile_expansion", {})
            row["coal"] = (coal_finding(assets, coal_rule.get("min_share", 0.0),
                                        coal_rule.get("effects")) if row["gem"]
                           else {"has_active_coal": False})
            row["expansion"] = expansion_finding(assets if row["gem"] else [],
                                                 exp_rule.get("min_share", 0.0),
                                                 exp_rule.get("effects"))
            row["criterion_assets"] = [
                a for a in assets if a["status_group"] == "expansion"
                or (a["category"] == "coal" and a["status_group"] == "operating")]
        legal_names = gleif_names(names.get(lei))

        for item in evidence_for(lei, emissions, ets):
            blocks = list(position_block)
            if item["source"] == "eu_ets":
                item["name_check"] = name_check(item["account_holder_names"], legal_names)
                if item["name_check"] == "different":
                    blocks.append("identity_conflict")
            row["evidence"].append(_finish({"via": "direct", "timing": None, **item}, blocks))

        seen: set[str] = set()
        ordered = sorted(children.get(lei, []), key=lambda link: (
            not link["verified"], link.get("relationship_start") or "9999"))
        for link in ordered:
            child = link["child_lei"]
            if child == lei or child in seen:
                continue
            found_all = evidence_for(child, emissions, ets)
            if not found_all:
                continue
            seen.add(child)
            timing = relationship_timing(link, fund.quarter_end)
            child_names = gleif_names(names.get(child))
            entry = {"child_lei": child,
                     "child_legal_name": (names.get(child) or {}).get("legal_name"),
                     "kind": link["kind"], "corroboration_level": link["corroboration_level"],
                     "verified": link["verified"], "timing": timing}
            relationships.append({"position": position.name, "isin": position.isin,
                                  "weight_percent": position.weight_percent,
                                  "parent_lei": lei, "sources": sorted(
                                      {f["source"] for f in found_all}), **entry})
            if not link["verified"]:
                row["group_hints"].append({
                    **entry, "sources": [item["source"] for item in found_all],
                    "note": "unbestätigt, überträgt keinen Beleg"})
                continue
            in_period: list[dict[str, Any]] = []
            if timing["status"] == "ok":
                in_period = evidence_for(child, emissions, ets, timing["first_full_year"],
                                         timing["last_full_year"])
            covered = {item["source"] for item in in_period}
            outside = [item for item in found_all if item["source"] not in covered]
            for item, extra in [*((i, []) for i in in_period),
                                *((i, [timing["status"] if timing["status"] != "ok"
                                       else "outside_relationship_period"]) for i in outside)]:
                blocks = [*position_block, *extra]
                if item["source"] == "eu_ets":
                    item["name_check"] = name_check(item["account_holder_names"], child_names)
                    if item["name_check"] == "different":
                        blocks.append("identity_conflict")
                row["evidence"].append(_finish(
                    {"via": "verified_group_relationship", **entry, **item}, blocks))

    attribution = {"positions": f"{FI_ATTRIBUTION}, Quartalsende {fund.quarter_end}",
                   "terms": FI_TERMS_URL}
    if ets:
        attribution["eu_ets"] = (f"{ETS_ATTRIBUTION}, Stand {ets.get('snapshot_date')}",
                                 ETS_TERMS_URL)
    if gem is not None:
        attribution["gem"] = (f"Global Energy Monitor, {gem['release']} (CC BY 4.0); "
                              "Daten gefiltert, Anteile und Status zusammengefasst",
                              GEM_LICENCE_URL)
    return {"fund": {k: v for k, v in asdict(fund).items() if k != "positions"},
            "attribution": attribution, "summary": summarise(rows), "positions": rows,
            "group_relationships": relationships, "gem_loaded": gem is not None}


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def bucket(selected: list[dict[str, Any]]) -> dict[str, Any]:
        return {"positions": len(selected),
                "weight_percent": round(sum(r["weight_percent"] or 0 for r in selected), 2)}

    def having(predicate: Any) -> list[dict[str, Any]]:
        return [r for r in rows if any(predicate(e) for e in r["evidence"])]

    by_country: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_status: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_confidence: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_country[row["issuer_country"] or "??"].append(row)
        by_status[row["mapping_status"]].append(row)
        by_confidence[row["mapping_confidence"]].append(row)
    confirmed = having(lambda e: e["status"] == "confirmed")
    return {
        "all": bucket(rows),
        "with_valid_isin": bucket([r for r in rows if r["isin_valid"]]),
        "with_company_candidate": bucket([r for r in rows if r["company"]]),
        "with_unique_lei": bucket([*by_status.get("unverified_candidate_with_lei", []),
                                   *by_status.get("confirmed_by_decision", [])]),
        "confirmed_by_decision": bucket(by_status.get("confirmed_by_decision", [])),
        "confirmed_coverage": bucket([r for r in rows
                                      if r["mapping_confidence"] in CONFIRMED_MAPPING]),
        "with_evidence": bucket([r for r in rows if r["evidence"]]),
        "with_evidence_swissprtr": bucket(having(lambda e: e["source"] == "swissprtr")),
        "with_evidence_eu_ets": bucket(having(lambda e: e["source"] == "eu_ets")),
        "with_confirmed_evidence": bucket(confirmed),
        "with_confirmed_evidence_swissprtr": bucket(having(
            lambda e: e["status"] == "confirmed" and e["source"] == "swissprtr")),
        "with_confirmed_evidence_eu_ets": bucket(having(
            lambda e: e["status"] == "confirmed" and e["source"] == "eu_ets")),
        "with_identity_conflict": bucket(having(lambda e: e["status"] == "identity_conflict")),
        "with_evidence_mapping_unconfirmed": bucket(having(
            lambda e: e["status"] == "position_mapping_unconfirmed")),
        "with_evidence_timing_only": bucket([r for r in having(
            lambda e: e["status"] in TIMING_BLOCKS) if r not in confirmed]),
        "with_group_hint_only": bucket([r for r in rows if r["group_hints"] and not r["evidence"]]),
        "gem_entities": bucket([r for r in rows if r.get("gem")]),
        "coal_checked": bucket([r for r in rows if r.get("coal") is not None]),
        "coal_active": bucket([r for r in rows if (r.get("coal") or {}).get("has_active_coal")]),
        "coal_expansion": bucket([r for r in rows if (r.get("coal") or {}).get("expansion")]),
        **{f"coal_strongest_{stake}": bucket([r for r in rows if (r.get("coal") or {}).get(
            "strongest") == stake]) for stake in GEM_STAKES[:-1]},
        "coal_old_conflict": bucket([r for r in rows if (r.get("coal") or {}).get(
            "old_conflict")]),
        "coal_sensitivity": sensitivity(rows, "coal"),
        "coal_no_hint": bucket([r for r in rows if r.get("coal") is not None
                                and not r["coal"]["has_active_coal"]]),
        "coal_conflict": bucket([r for r in rows if (r.get("coal") or {}).get("conflict")]),
        "expansion_checked": bucket([r for r in rows if r.get("expansion") is not None]),
        "expansion_any": bucket([r for r in rows
                                 if (r.get("expansion") or {}).get("has_expansion")]),
        "expansion_conflict": bucket([r for r in rows
                                      if (r.get("expansion") or {}).get("conflict")]),
        "expansion_no_hint": bucket([r for r in rows if r.get("expansion") is not None
                                     and not r["expansion"]["has_expansion"]]),
        **{f"expansion_strongest_{stake}": bucket([r for r in rows if (r.get(
            "expansion") or {}).get("strongest") == stake]) for stake in GEM_STAKES[:-1]},
        "expansion_old_conflict": bucket([r for r in rows if (r.get("expansion") or {}).get(
            "old_conflict")]),
        "expansion_sensitivity": sensitivity(rows, "expansion"),
        "expansion_conflict_only_captive": bucket([
            r for r in rows if (r.get("expansion") or {}).get("conflict")
            and r["expansion"].get("own_captive_or_backup")
            == r["expansion"].get("own_units_total")]),
        **{f"expansion_phase_{phase}": bucket([r for r in rows if phase in (r.get(
            "expansion") or {}).get("phases", {})]) for phase in GEM_PHASE_LABELS},
        **{f"expansion_type_{kind}": bucket([r for r in rows if kind in (r.get(
            "expansion") or {}).get("capacity_types", {})]) for kind in GEM_CAPACITY_LABELS},
        "by_mapping_confidence": {k: bucket(v) for k, v in sorted(by_confidence.items())},
        "by_mapping_status": {k: bucket(v) for k, v in sorted(by_status.items())},
        "by_issuer_country": dict(sorted(
            ((k, bucket(v)) for k, v in by_country.items()),
            key=lambda item: -item[1]["weight_percent"])),
    }
