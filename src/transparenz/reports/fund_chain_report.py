"""Bericht zur Fondskette: HTML (Vorlage templates/fund_chain_report.html.j2) und Markdown."""
from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import jinja2

from transparenz.entities.labels import (
    CONFIDENCE_LABELS,
    CORROBORATION_LABELS,
    GEM_CAPACITY_LABELS,
    GEM_CATEGORY_LABELS,
    GEM_KIND_LABELS,
    GEM_PHASE_LABELS,
    GEM_STAKE_LABELS,
    GEM_STATUS_LABELS,
    KIND_LABELS,
    OPEN_REASONS,
    PROVENANCE_STATUS_LABELS,
    RELATIONSHIP_LABELS,
    SOURCE_LABELS,
    STATUS_LABELS,
)
from transparenz.ingestion.gem import GEM_STAKES, GEM_STATUSES
from transparenz.services.fund_chain import (
    BLOCK_PRIORITY,
    CONFIRMED_MAPPING,
    PRTR_ATTRIBUTION,
    TIMING_BLOCKS,
    gleif_names,
)
from transparenz.services.fund_findings import GEM_PHASES
from transparenz.services.ownership import OWN_ACCOUNT, RELATIONSHIP_TYPES

# ---------------------------------------------------------------------------- Ausgabe


def _fmt(value: float | None, digits: int = 2) -> str:
    return "–" if value is None else f"{value:,.{digits}f}".replace(",", "'")


def _fmt_date(value: str | None) -> str:
    if not value or len(value) < 10:
        return "–"
    return f"{value[8:10]}.{value[5:7]}.{value[:4]}"


CONFIDENCE_CHIPS = {"consistent": "c-ok", "consistent_lapsed": "c-ok",
                    "confirmed_by_decision": "c-ok", "confirmed_by_register": "c-ok",
                    "confirmed_by_agreement": "c-ok", "auto_by_name": "c-ok",
                    "name_proposal": "s-zuordnung_unsicher",
                    "name_mismatch": "s-zuordnung_unsicher", "lei_not_in_gleif":
                    "s-zuordnung_unsicher", "ambiguous": "s-zuordnung_unsicher"}

QUESTION_CHIPS = {"beantwortet": "c-ok", "teilweise": "s-unbekannt",
                  "nicht beantwortbar": "s-pruefung_ausstehend",
                  "bewusst nicht beantwortet": "s-nicht_anwendbar"}


def criteria_status(criteria: list[dict[str, Any]],
                    report: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Status je Kriterium. Ohne abdeckende Quelle «unbekannt» (D-014).

    Kohle und fossile Expansion sind mit GEM abgedeckt, aber nur für widerspruchsfrei
    zugeordnete Positionen. «conflict» wendet die Regel des Profils aus criteria.toml an
    (unsere Bewertungsentscheidung). Emissionsmengen sind nie ein Kriterienbeleg.
    """
    out = []
    gem_loaded = bool(report and report.get("gem_loaded"))
    s = (report or {}).get("summary", {})
    for c in criteria:
        item = {"key": c.get("key"), "name": c.get("name"), "description": c.get("description"),
                "severity": c.get("severity"), "threshold_note": c.get("threshold_note"),
                "rule": c.get("rule") or "", "rule_decided": c.get("decision") != "proposed",
                "status": "unbekannt", "status_label": "Unbekannt (keine Datenabdeckung)",
                "chip": "s-unbekannt", "evidence_count": 0, "breakdown": [],
                "breakdown_title": "", "conflict": None,
                "reason": c.get("source_gap")
                or "Keine der verwendeten Quellen enthält Angaben zu diesem Kriterium."}
        if gem_loaded and c.get("key") == "kohle":
            unchecked = {"positions": s["all"]["positions"] - s["coal_checked"]["positions"],
                         "weight_percent": round(s["all"]["weight_percent"]
                                                 - s["coal_checked"]["weight_percent"], 2)}
            item.update({
                "status": "teilweise belegt", "status_label": "Belegt laut GEM (Teilabdeckung)",
                "chip": "s-dokumentiert", "evidence_count": s["coal_active"]["positions"],
                "conflict": s["coal_conflict"],
                "breakdown_title": "Positionen nach stärkster Beteiligung an aktiven "
                                   "Kohleanlagen (in Betrieb oder im Ausbau):",
                "breakdown": [
                    *((GEM_STAKE_LABELS[k], s[f"coal_strongest_{k}"])
                      for k in GEM_STAKES[:-1]),
                    ("davon mit Kohleprojekt im Ausbau", s["coal_expansion"]),
                    ("keine Hinweise in GEM", s["coal_no_hint"]),
                    ("unbekannt (nicht widerspruchsfrei zugeordnet)", unchecked),
                    ("zum Vergleich: Konflikte nach Regel bis Profil 1.0",
                     s["coal_old_conflict"])],
                "reason": "Laut Global Energy Monitor: Beteiligungen an Kohlekraftwerken (ab "
                          "30 MW) und Kohleminen in Betrieb oder im Ausbau, auch indirekt. "
                          "Konflikt: Eigentum auf eigene Rechnung mit belegtem Anteil. "
                          "Vermögensverwaltung, Verwahrung, Finanzbeteiligungen mit "
                          "ungeklärter Rechnung und unbekannte Anteile zählen nicht."})
        elif gem_loaded and c.get("key") == "fossile_expansion":
            unchecked = {"positions": s["all"]["positions"]
                         - s["expansion_checked"]["positions"],
                         "weight_percent": round(s["all"]["weight_percent"]
                                                 - s["expansion_checked"]["weight_percent"], 2)}
            item.update({
                "status": "teilweise belegt", "status_label": "Belegt laut GEM (Teilabdeckung)",
                "chip": "s-dokumentiert", "evidence_count": s["expansion_any"]["positions"],
                "conflict": s["expansion_conflict"],
                "breakdown_title": "Positionen mit neuer fossiler Kapazität (angekündigt, in "
                                   "Genehmigung oder im Bau), nach stärkster Beteiligung, "
                                   "Phase und Art:",
                "breakdown": [
                    *((GEM_STAKE_LABELS[k], s[f"expansion_strongest_{k}"])
                      for k in GEM_STAKES[:-1]),
                    *((f"Phase: {label}", s[f"expansion_phase_{k}"])
                      for k, label in GEM_PHASE_LABELS.items()),
                    *((f"Art: {label}", s[f"expansion_type_{k}"])
                      for k, label in GEM_CAPACITY_LABELS.items()),
                    ("keine Hinweise in GEM", s["expansion_no_hint"]),
                    ("unbekannt (nicht widerspruchsfrei zugeordnet)", unchecked),
                    ("Konflikt nur wegen Eigenbedarf oder Notstrom (z. B. Rechenzentren)",
                     s["expansion_conflict_only_captive"]),
                    ("zum Vergleich: Konflikte nach Regel bis Profil 1.0",
                     s["expansion_old_conflict"])],
                "reason": "Laut Global Energy Monitor: Beteiligungen an neuen Kohle- und "
                          "Gaskraftwerken, Kohleminen, LNG-Terminals und Pipelines, auch "
                          "indirekt. Konflikt: Eigentum auf eigene Rechnung mit belegtem "
                          "Anteil. Nicht abgedeckt: neue Öl- und Gasfelder (Eigentümer bei "
                          "GEM nur mit Namen). Eine Position kann in mehreren Phasen und Arten "
                          "vorkommen."})
        out.append(item)
    return out


def explain_finding(finding: dict[str, Any] | None, has_key: str, min_share: float) -> str:
    """Begründet in einem Satz, warum eine Position einen Konflikt auslöst oder nicht."""
    if finding is None:
        return "nicht geprüft: Position nicht widerspruchsfrei zugeordnet"
    if not finding.get(has_key):
        return ("nur Verwahrung für Dritte, keine Beteiligung" if finding.get("custody_only")
                else "keine Hinweise in GEM")
    relationships = [RELATIONSHIP_LABELS[r] for r in finding.get("relationships", [])
                     if r != OWN_ACCOUNT]
    others = f" Daneben: {', '.join(relationships)}." if relationships else ""
    if finding.get("conflict"):
        return (f"Konflikt: Eigentum auf eigene Rechnung, durchgerechneter Anteil bis "
                f"{_fmt(finding['max_own_share'])} % ({finding['own_units']} Einheit"
                f"{'en' if finding['own_units'] != 1 else ''}).{others}")
    if finding.get("own_units"):
        if finding.get("max_own_share") is None:
            return ("kein Konflikt: Eigentum auf eigene Rechnung, aber GEM nennt keinen "
                    "Anteil. Fehlender Beleg: Beteiligungsquote." + others)
        return (f"kein Konflikt: eigener Anteil höchstens {_fmt(finding['max_own_share'])} %, "
                f"unter der Schwelle von {_fmt(min_share)} %.{others}")
    if relationships:
        return ("kein Konflikt: keine belegte Eigentumsbeteiligung, nur "
                f"{', '.join(relationships)}.")
    return "kein Konflikt: betroffene Kategorie löst im Profil keinen Konflikt aus."


def reclassified_rows(positions: list[dict[str, Any]],
                      rules: dict[str, Any]) -> list[dict[str, Any]]:
    """Alle Positionen mit Kohle- oder Expansionsbezug, nach denselben Regeln neu geprüft."""
    out = []
    for row in positions:
        coal, exp = row.get("coal") or {}, row.get("expansion") or {}
        if not (coal.get("has_active_coal") or exp.get("has_expansion")
                or coal.get("old_conflict") or exp.get("old_conflict")):
            continue
        counts: Counter[str] = Counter(a.get("relationship", OWN_ACCOUNT)
                                       for a in row.get("criterion_assets") or [])
        out.append({
            "name": row["name"], "weight": _fmt(row["weight_percent"]),
            "financial": (row.get("company") or {}).get("financial_institution"),
            "industries": ", ".join((row.get("company") or {}).get("industries") or []) or "–",
            "relationships": "; ".join(f"{RELATIONSHIP_LABELS[k]}: {n}"
                                       for k, n in sorted(counts.items(),
                                                          key=lambda i: RELATIONSHIP_TYPES.index(
                                                              i[0]))),
            "coal_old": coal.get("old_conflict", False), "coal_new": coal.get("conflict", False),
            "coal_why": explain_finding(row.get("coal"), "has_active_coal",
                                        rules.get("kohle", {}).get("min_share", 0.0)),
            "exp_old": exp.get("old_conflict", False), "exp_new": exp.get("conflict", False),
            "exp_why": explain_finding(row.get("expansion"), "has_expansion",
                                       rules.get("fossile_expansion", {}).get("min_share", 0.0)),
            "captive": exp.get("own_captive_or_backup", 0)})
    return out


def _hop_view(hop: dict[str, Any]) -> dict[str, Any]:
    share = hop.get("share")
    return {"holder": hop["holder"], "name": hop["name"],
            "share": "Anteil unbekannt" if share is None else f"{_fmt(share)} %",
            "url": hop.get("source_url"), "imputed": hop.get("imputed")}


def case_view(row: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    """Vollständige Belegkette einer Position: Unternehmen → Kette → Anlage → Regel."""
    company = row.get("company") or {}
    lei = company.get("lei")
    entry = (company.get("gleif") or {}).get(lei) or {}
    assets = []
    for asset in sorted(row.get("criterion_assets") or [], key=lambda a: (
            RELATIONSHIP_TYPES.index(a.get("relationship", OWN_ACCOUNT)),
            GEM_STATUSES.index(a["status_group"]), a["kind"], a.get("project") or "")):
        details = asset.get("details") or {}
        status = asset.get("status") or "–"
        phase = GEM_PHASES.get(status.strip().lower())
        phase_label = (GEM_PHASE_LABELS[phase] if phase
                       else GEM_STATUS_LABELS[asset["status_group"]])
        captive_kind = details.get("captive_type") or details.get("captive_use")
        assets.append({
            "project": asset.get("project") or "–", "kind": GEM_KIND_LABELS[asset["kind"]],
            "country": details.get("country") or "–",
            "status": f"{status} ({phase_label})",
            "start_year": details.get("start_year"),
            "fuel": details.get("fuel"), "operator": details.get("operator"),
            "captive": ("Notstrom" if details.get("backup") else
                        (f"Eigenbedarf ({captive_kind})" if details.get("captive_use")
                         else None)),
            "wiki": details.get("wiki_url"),
            "relationship": RELATIONSHIP_LABELS[asset.get("relationship", OWN_ACCOUNT)],
            "reason": asset.get("relationship_reason") or "",
            "share": "unbekannt" if asset["share"] is None else f"{_fmt(asset['share'])} %",
            "hops": [_hop_view(h) for h in asset.get("hops") or []],
            "decisive": asset.get("deciding_hop"),
            "criteria": ", ".join(name for name, ok in (
                ("Kohle", asset["category"] == "coal"),
                ("Fossile Expansion", asset["status_group"] == "expansion")) if ok)})
    by_rel = Counter(a["relationship"] for a in assets)
    return {"name": row["name"], "isin": row["isin"], "weight": _fmt(row["weight_percent"]),
            "lei": lei or "–", "legal_name": entry.get("legal_name") or "–",
            "mapping": CONFIDENCE_LABELS[row["mapping_confidence"]][0],
            "industries": ", ".join(company.get("industries") or []) or "keine Angabe",
            "financial": company.get("financial_institution"),
            "gem_entities": " / ".join((row.get("gem") or {}).get("entity_names") or []) or "–",
            "coal_why": explain_finding(row.get("coal"), "has_active_coal",
                                        report.get("rules", {}).get("kohle", {}).get(
                                            "min_share", 0.0)),
            "exp_why": explain_finding(row.get("expansion"), "has_expansion",
                                       report.get("rules", {}).get("fossile_expansion", {}).get(
                                           "min_share", 0.0)),
            "by_relationship": "; ".join(f"{k}: {n}" for k, n in by_rel.most_common()),
            "assets": assets}


def _gem_line(summary: dict[str, Any], category: str) -> str | None:
    counts = summary["counts"].get(category, {})
    parts = []
    for stake in GEM_STAKES:
        active = {st: n for key, n in counts.items() for sk, st in [key.split("|")]
                  if sk == stake and st in ("operating", "expansion")}
        if active:
            label = ("treuhänderisch gehalten, keine Beteiligung" if stake == "custodial"
                     else GEM_STAKE_LABELS[stake])
            parts.append(f"{label}: " + ", ".join(
                f"{_fmt(n, 0)} {GEM_STATUS_LABELS[st]}" for st, n in sorted(active.items())))
    closed = sum(n for key, n in counts.items() if not key.endswith(("operating", "expansion")))
    if closed:
        parts.append(f"zusätzlich {_fmt(closed, 0)} stillgelegt, aufgegeben oder ohne Status")
    return f"{GEM_CATEGORY_LABELS[category]}: " + "; ".join(parts) if parts else None


def _gem_asset_view(asset: dict[str, Any]) -> dict[str, Any]:
    share = asset["share"]
    return {"kind": GEM_KIND_LABELS[asset["kind"]], "project": asset["project"] or "–",
            "status": f"{asset['status'] or '–'} ({GEM_STATUS_LABELS[asset['status_group']]})",
            "stake": GEM_STAKE_LABELS[asset["stake"]],
            "share": "unbekannt" if share is None else f"{_fmt(share, 2)} %",
            "capacity": (f"{_fmt(float(asset['capacity']), 1)} "
                         f"{asset['capacity_label'].replace('Capacity', '').strip(' ()') or ''}"
                         if asset["capacity"] not in (None, "") and _is_number(asset["capacity"])
                         else "–"),
            "path": asset["path"] or "–"}


def _is_number(value: Any) -> bool:
    try:
        float(value)
    except (TypeError, ValueError):
        return False
    return True


def coal_cell(row: dict[str, Any]) -> str:
    coal = row.get("coal")
    if coal is None:
        return "nicht geprüft"
    if not coal["has_active_coal"]:
        return "keine Hinweise in GEM"
    return (GEM_STAKE_LABELS[coal["strongest"]] + (", im Ausbau" if coal["expansion"] else "")
            + ("; Konflikt mit Profil" if coal.get("conflict") else ""))


# Welche Tests die Regel eines Kriteriums prüfen (ein Test stellt sicher, dass es sie gibt).
GENERIC_CRITERION_TEST = ("tests/test_screening.py::"
                          "test_every_active_criterion_applies_statuses_and_categories")

CRITERION_TESTS: dict[str, tuple[str, ...]] = {
    "kohle": ("tests/test_pilot_fund_chain.py::test_chain_reports_coal_by_relationship_type",
              "tests/test_ownership.py::test_bank_and_asset_manager_chains_are_not_ownership"),
    "fossile_expansion": (
        "tests/test_pilot_fund_chain.py::test_chain_reports_coal_by_relationship_type",
        "tests/test_pilot_fund_chain.py::test_expansion_counts_captive_units_and_threshold"),
    "waffen": ("tests/test_screening.py::test_weapons_category_decides_conflict",),
    "korruption": ("tests/test_screening.py::test_corruption_expiry_runs_from_conclusion",
                   "tests/test_screening.py::test_corruption_expiry_respects_consequences_and"
                   "_remediation"),
}

PILOT_CRITERIA = ("kohle", "fossile_expansion")


def criteria_readiness(criteria: list[dict[str, Any]],
                       report: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Fünf getrennte Stufen je Kriterium: definiert, implementiert, getestet, mit
    freigegebenen Daten verbunden, am Fonds tatsächlich geprüft."""
    s = (report or {}).get("summary", {})
    gem_loaded = bool((report or {}).get("gem_loaded"))
    out = []
    for c in criteria:
        key = c.get("key")
        categories = c.get("categories") or c.get("category") or []
        decides = any((cat.get("effect") if isinstance(cat, dict) else cat.effect) != "conflict"
                      for cat in categories)
        parts = ["Belegstatus"]
        if categories:
            parts.append("Kategorien entscheiden über Konflikt" if decides
                         else "Kategorien angezeigt")
        if c.get("conflict_expiry_years"):
            parts.append("Wirkungsdauer mit Abhilfe und fortbestehenden Folgen")
        implemented = ("Pilot: GEM-Besitzketten, Beziehungstypen, Kategorien, Schwelle; "
                       if key in PILOT_CRITERIA else "") + "Engine: " + ", ".join(parts)
        tests = (*CRITERION_TESTS.get(key, ()), GENERIC_CRITERION_TEST)
        checked_key = {"kohle": "coal_checked", "fossile_expansion": "expansion_checked"}.get(key)
        if gem_loaded and checked_key:
            checked = s[checked_key]
            fund = (f"ja: {checked['positions']} Positionen ({_fmt(checked['weight_percent'])} %)"
                    " geprüft; übrige unbekannt")
        else:
            fund = "nein: keine freigegebene, zugeordnete Quelle"
        out.append({
            "name": c.get("name"),
            "defined": "ja" + ("" if c.get("decision") != "proposed"
                               else " (Vorschlag, noch zu bestätigen)"),
            "implemented": implemented,
            "tested": f"ja, {len(tests)} Test(s) mit fiktiven Daten",
            "tests": [t.split("::")[-1] for t in tests],
            "data": c.get("data_status_label") or "keine geeignete Quelle gefunden",
            "data_note": "; ".join(c.get("sources") or []) or c.get("source_gap") or "",
            "fund": fund})
    return out


def _path_text(evidence: dict[str, Any]) -> str:
    if evidence["via"] == "direct":
        return ("Das Unternehmen ist selbst Kontoinhaber im Register (gleicher LEI)"
                if evidence["source"] == "eu_ets" else "Das Unternehmen meldet selbst")
    timing = evidence.get("timing") or {}
    level = evidence["corroboration_level"]
    text = (f"Über die Tochter «{evidence.get('child_legal_name') or evidence['child_lei']}». "
            f"Laut GLEIF ist das Fondsunternehmen ihre "
            f"{KIND_LABELS.get(evidence['kind'], evidence['kind'])} "
            f"({CORROBORATION_LABELS.get(level, level)}), seit {_fmt_date(timing.get('start'))}")
    if timing.get("start_is_registration_date"):
        text += " (Tag der LEI-Registrierung; die Beziehung kann älter sein)"
    return text


def _evidence_view(evidence: dict[str, Any]) -> dict[str, Any]:
    view = {"source": SOURCE_LABELS.get(evidence["source"], evidence["source"]),
            "path": _path_text(evidence),
            "status": STATUS_LABELS.get(evidence.get("status", ""), evidence.get("status")),
            "first_full_year": (evidence.get("timing") or {}).get("first_full_year")}
    if evidence["source"] == "eu_ets":
        installations = evidence["installations"]
        latest = max(i["latest_year"] for i in installations)
        latest_total = sum(i["latest_verified_t_co2e"] for i in installations
                           if i["latest_year"] == latest)
        view.update({
            "holder": " / ".join(evidence["account_holder_names"]) or "ohne Namensangabe",
            "lei": evidence["reporting_lei"], "as_of": _fmt_date(evidence["snapshot_date"]),
            "headline": f"{len(installations)} Anlage(n); verifizierte Emissionen {latest}: "
                        f"{_fmt(latest_total, 0)} t CO2e",
            "older": sum(1 for i in installations if i["latest_year"] < latest),
            "rows": [{"id": f"{i['registry_code']}-{i['installation_id']}",
                      "name": i["installation_name"] or "ohne Namen",
                      "activity": i["activity_type"] or "nicht angegeben",
                      "years": f"{i['years'][0]}–{i['years'][1]}",
                      "latest": f"{_fmt(i['latest_verified_t_co2e'], 0)} t CO2e "
                                f"({i['latest_year']})",
                      "revoked": _fmt_date(i["permit_revocation_date"])
                      if i["permit_revocation_date"] else None} for i in installations]})
    else:
        view.update({
            "holder": None, "lei": evidence["reporting_company_key"].removeprefix("lei:"),
            "as_of": _fmt_date(evidence.get("data_as_of")),
            "headline": f"{evidence['rows_total']} Meldezeilen {evidence['years'][0]}–"
                        f"{evidence['years'][1]} für Betriebs-UID "
                        f"{', '.join(evidence['facility_uids'])}",
            "older": 0,
            "rows": [{"id": evidence["latest_year"],
                      "name": r["pollutant_name"] or "ohne Schadstoffbezeichnung in der Meldezeile",
                      "activity": r.get("medium") or "–", "years": str(evidence["latest_year"]),
                      "latest": f"{_fmt(r['value'])} {r['unit'] or ''}".strip(), "revoked": None}
                     for r in evidence["latest_year_rows"]]})
    return view


def html_context(report: dict[str, Any], criteria: list[dict[str, Any]]) -> dict[str, Any]:
    """Bereitet den Bericht für Laien auf. Keine neue Logik: nur Auswahl und Formulierung."""
    s, fund, inputs = report["summary"], report["fund"], report.get("inputs", {})
    positions = sorted(report["positions"], key=lambda r: -(r["weight_percent"] or 0))

    def legal_name(row: dict[str, Any]) -> str:
        company = row.get("company") or {}
        entries = list((company.get("gleif") or {}).values())
        return entries[0]["legal_name"] if entries else "–"

    review_keys = ("name_mismatch", "lei_not_in_gleif", "ambiguous", "name_proposal")
    review_rows = [r for r in positions if r["mapping_confidence"] in review_keys]
    review_weight = round(sum(r["weight_percent"] or 0 for r in review_rows), 2)
    missing_weight = round(sum(r["weight_percent"] or 0 for r in positions if r[
        "mapping_confidence"] in ("unknown", "no_lei", "no_valid_isin", "lei_not_checked")), 2)

    tiers = []
    for key, (label, text) in CONFIDENCE_LABELS.items():
        item = s["by_mapping_confidence"].get(key)
        if item:
            tiers.append({"label": label, "text": text, "chip": CONFIDENCE_CHIPS.get(
                key, "s-unbekannt"), "confirmed": key in CONFIRMED_MAPPING, **item})

    emission_rows = []
    for row in positions:
        confirmed = [e for e in row["evidence"] if e["status"] == "confirmed"]
        if not confirmed:
            continue
        parts = []
        for source in ("eu_ets", "swissprtr"):
            items = [e for e in confirmed if e["source"] == source]
            if not items:
                continue
            count = (sum(len(e["installations"]) for e in items) if source == "eu_ets"
                     else sum(len(e["facility_uids"]) for e in items))
            children = len({e["child_lei"] for e in items if e["via"] != "direct"})
            ways = [*(["selbst"] if any(e["via"] == "direct" for e in items) else []),
                    *([f"über {children} Tochtergesellschaft{'en' if children > 1 else ''}"]
                      if children else [])]
            parts.append(f"{SOURCE_LABELS[source]}: {count} "
                         f"{'Anlage' if count == 1 else 'Anlagen'} ({' und '.join(ways)})")
        emission_rows.append({"name": row["name"], "isin": row["isin"],
                              "weight": _fmt(row["weight_percent"]),
                              "legal_name": legal_name(row), "line": "; ".join(parts),
                              "evidence": [_evidence_view(e) for e in confirmed]})

    def separate(statuses: tuple[str, ...]) -> list[dict[str, Any]]:
        out = []
        for row in positions:
            for e in row["evidence"]:
                if e["status"] in statuses:
                    out.append({"name": row["name"], "isin": row["isin"],
                                "weight": _fmt(row["weight_percent"]),
                                "legal_name": legal_name(row), "reason": STATUS_LABELS[e["status"]],
                                "timing": e.get("timing") or {}, **_evidence_view(e)})
        return out

    statuses: dict[tuple[str | None, str], set[str]] = defaultdict(set)
    for row in positions:
        for e in row["evidence"]:
            if e.get("child_lei"):
                statuses[(row["isin"], e["child_lei"])].add(e["status"])

    def outcome(rel: dict[str, Any]) -> str:
        found = statuses.get((rel["isin"], rel["child_lei"]), set())
        if not rel["verified"]:
            return "nicht zugerechnet: Beziehung unbestätigt"
        if "confirmed" in found:
            return f"zugerechnet ab {rel['timing'].get('first_full_year')}"
        blocking = next((s for s in BLOCK_PRIORITY if s in found), None)
        return f"nicht zugerechnet: {STATUS_LABELS[blocking]}" if blocking else "–"

    relationships = [{
        "position": rel["position"], "weight": _fmt(rel["weight_percent"]),
        "outcome": outcome(rel),
        "child": rel["child_legal_name"] or rel["child_lei"],
        "kind": KIND_LABELS.get(rel["kind"], rel["kind"]),
        "corroboration": CORROBORATION_LABELS.get(rel["corroboration_level"],
                                                  rel["corroboration_level"]),
        "verified": rel["verified"], "start": _fmt_date(rel["timing"].get("start")),
        "start_is_registration_date": rel["timing"].get("start_is_registration_date"),
        "first_full_year": rel["timing"].get("first_full_year"),
        "valid": rel["timing"].get("valid_at_fund_date"),
        "sources": ", ".join(SOURCE_LABELS.get(x, x) for x in rel["sources"])}
        for rel in sorted(report.get("group_relationships", []),
                          key=lambda r: -(r["weight_percent"] or 0))]

    hints = [{"name": row["name"], "weight": _fmt(row["weight_percent"]),
              "child": h["child_legal_name"] or h["child_lei"],
              "kind": KIND_LABELS.get(h["kind"], h["kind"]),
              "corroboration": CORROBORATION_LABELS.get(h["corroboration_level"],
                                                        h["corroboration_level"]),
              "start": _fmt_date((h.get("timing") or {}).get("start")),
              "sources": ", ".join(SOURCE_LABELS.get(x, x) for x in h["sources"])}
             for row in positions for h in row["group_hints"]]

    countries = list(s["by_issuer_country"].items())[:3]
    top = positions[0]
    crit = criteria_status(criteria, report)
    crit_names = ", ".join(c["name"] for c in crit)
    gem_loaded = bool(report.get("gem_loaded"))
    gem_rows = []
    for row in positions:
        summary = row.get("gem")
        if not summary or not summary["assets_total"]:
            continue
        lines = [line for line in (_gem_line(summary, "coal"), _gem_line(summary, "oil_gas"))
                 if line]
        gem_rows.append({
            "name": row["name"], "weight": _fmt(row["weight_percent"]),
            "entity": " / ".join(summary["entity_names"]), "lines": lines,
            "total": summary["assets_total"],
            "assets": [_gem_asset_view(a) for cat in ("coal", "oil_gas")
                       for a in summary["shown"][cat]]})
    if gem_loaded:
        criteria_answer = (
            "teilweise",
            f"Für Kohle und fossile Expansion: {s['coal_active']['positions']} Positionen "
            f"({_fmt(s['coal_active']['weight_percent'])} %) sind laut GEM an Kohleanlagen in "
            f"Betrieb oder im Ausbau beteiligt, davon {s['coal_strongest_control']['positions']} "
            f"mit Kontrolle; {s['expansion_any']['positions']} Positionen "
            f"({_fmt(s['expansion_any']['weight_percent'])} %) an neuer fossiler Kapazität. "
            f"Nach unserem Profil sind das {s['coal_conflict']['positions']} Konflikte bei "
            f"Kohle und {s['expansion_conflict']['positions']} bei fossiler Expansion. "
            f"Die übrigen {len(crit) - 2} Kriterien: unbekannt.")
    else:
        criteria_answer = (
            "nicht beantwortbar",
            f"Für keines der {len(crit)} Kriterien ({crit_names}) liegt eine Quelle vor. Der "
            "Status ist «unbekannt», nicht «keine Hinweise». Emissionsmengen sind kein Verstoss "
            "gegen ein Kriterium.")
    questions = [
        ("Was steckt im Fonds, und wie stark ist jede Position gewichtet?", "beantwortet",
         f"{s['all']['positions']} Positionen zum {_fmt_date(fund['quarter_end'])}, vollständig "
         f"aus der Meldung an die schwedische Finanzaufsicht. Grösste Position: {top['name']} "
         f"({_fmt(top['weight_percent'])} %)."),
        ("Aus welchen Ländern stammen die Emittenten?", "beantwortet",
         "Laut Fondsmeldung vor allem " + ", ".join(
             f"{k} ({_fmt(v['weight_percent'])} %)" for k, v in countries) + "."),
        ("Zu welchen Unternehmen gehören die Positionen?", "teilweise",
         f"{_fmt(s['confirmed_coverage']['weight_percent'])} % des Fondsvermögens "
         f"({s['confirmed_coverage']['positions']} Positionen) sind automatisch zugeordnet, "
         f"{_fmt(review_weight)} % bleiben unsicher, {_fmt(missing_weight)} % ohne Unternehmen. "
         "Das ist eine Abdeckungsangabe. Wie oft eine Zuordnung stimmt (Präzision), wird "
         "getrennt an Referenzfällen gemessen (Abschnitt 2)."),
        ("Welche Unternehmen im Fonds betreiben Anlagen mit amtlich gemeldeten Emissionen?",
         "teilweise",
         f"{s['with_confirmed_evidence']['positions']} Positionen "
         f"({_fmt(s['with_confirmed_evidence']['weight_percent'])} %). Abgedeckt sind nur "
         "Betriebe in der Schweiz (SwissPRTR) und Anlagen im EU-Emissionshandel. Fälle mit "
         "Identitätskonflikt oder unpassendem Zeitraum sind nicht mitgezählt (Abschnitt 6). "
         "Unternehmen ohne Eintrag können trotzdem Emissionen verursachen, etwa ausserhalb "
         "Europas."),
        *([("An welchen Kohle-, Gas- oder Ölanlagen sind die Firmen beteiligt, auch "
            "indirekt?", "teilweise",
            f"{s['gem_entities']['positions']} Positionen "
            f"({_fmt(s['gem_entities']['weight_percent'])} %) sind bei Global Energy Monitor "
            "als Eigentümer erfasst. Beteiligungen stehen gestuft nach Anteil und mit "
            "Besitzkette in Abschnitt 4, ohne Summen über Stufen hinweg. Öl- und Gasfelder "
            "fehlen, weil GEM deren Eigentümer nur mit Namen nennt.")] if gem_loaded else []),
        ("Wie gross ist der CO2-Fussabdruck des Fonds?", "nicht beantwortbar",
         "Die Daten zeigen einzelne Anlagen, nicht ganze Unternehmen und keinen Anteil des "
         "Fonds. Eine Summe wäre irreführend und wird deshalb nicht gebildet."),
        ("Verletzt ein Unternehmen im Fonds meine Ausschlusskriterien?", *criteria_answer),
        ("Gibt es Gerichtsurteile, Behördenentscheide oder Sanktionen?", "nicht beantwortbar",
         "Der Pilot enthält keine solche Quelle."),
        ("Wie aktuell und wie belegt sind die Angaben?", "beantwortet",
         f"Jede Angabe nennt Quelle und Stichtag: Fondsbestand {_fmt_date(fund['quarter_end'])}, "
         f"EU-Emissionshandel Stand {_fmt_date(inputs.get('ets_snapshot_date'))}, SwissPRTR bis "
         f"{_fmt_date(inputs.get('swissprtr_data_as_of'))}, GLEIF-Abfrage "
         f"{_fmt_date((inputs.get('gleif_fetched_at') or '')[:10])}"
         + (f", GEM-Besitzdaten «{inputs.get('gem_release')}»" if gem_loaded else "") + "."),
        ("Ist der Fonds nachhaltig, und passt er zu meinen Werten?", "bewusst nicht beantwortet",
         "Der Bericht urteilt nicht und empfiehlt nichts. Er zeigt, was belegt ist und was fehlt; "
         "die Beurteilung bleibt bei Ihnen."),
    ]
    separate_count = len({r["isin"] for r in review_rows}
                         | {e["isin"] for e in separate(("identity_conflict", *TIMING_BLOCKS))}
                         | {r["isin"] for r in positions if r["group_hints"]})
    return {
        "fund": fund, "quarter_end": _fmt_date(fund["quarter_end"]),
        "attribution": report["attribution"], "inputs": inputs,
        "provenance": provenance_rows(report),
        "cards": [
            ("Positionen im Fonds", str(s["all"]["positions"]),
             f"Stand {_fmt_date(fund['quarter_end'])}"),
            ("Widerspruchsfrei zugeordnet", f"{_fmt(s['confirmed_coverage']['weight_percent'])} %",
             f"des Fondsvermögens, {s['confirmed_coverage']['positions']} Positionen"),
            ("Mit amtlichen Emissionsdaten",
             f"{_fmt(s['with_confirmed_evidence']['weight_percent'])} %",
             f"{s['with_confirmed_evidence']['positions']} Positionen, nur Schweiz und "
             "EU-Emissionshandel"),
            *([("Beteiligt an Kohleanlagen, auch indirekt",
               f"{_fmt(s['coal_active']['weight_percent'])} %",
                f"{s['coal_active']['positions']} Positionen laut GEM, davon "
                f"{s['coal_strongest_control']['positions']} mit Kontrolle")]
              if gem_loaded else []),
            ("Kriterien mit Quelle",
             f"{sum(1 for c in crit if c['status'] != 'unbekannt')} von {len(crit)}",
             "Kohle und fossile Expansion laut GEM; übrige unbekannt" if gem_loaded
             else "kein Kriterium durch eine Quelle abgedeckt"),
            ("Separat ausgewiesen", str(separate_count),
             "Positionen mit Prüffall, Konflikt oder unbestätigtem Konzernbezug (Abschnitt 6)"),
        ],
        "gem_loaded": gem_loaded, "gem_rows": gem_rows,
        "stake_labels": [GEM_STAKE_LABELS[k] for k in GEM_STAKES],
        "questions": [{"q": q, "status": st, "chip": QUESTION_CHIPS[st], "a": a}
                      for q, st, a in questions],
        "profile": report.get("profile") or "Startprofil laut criteria.toml",
        "tiers": tiers, "emission_rows": emission_rows, "criteria": crit,
        "identity_conflicts": separate(("identity_conflict",)),
        "timing_blocked": separate(TIMING_BLOCKS),
        "mapping_review": [{
            "name": r["name"], "isin": r["isin"], "weight": _fmt(r["weight_percent"]),
            "label": CONFIDENCE_LABELS[r["mapping_confidence"]][0],
            "leis": (r.get("company") or {}).get("leis") or [],
            "wikidata": " / ".join((r.get("company") or {}).get("wikidata_names") or []),
            "gleif": [n for e in ((r.get("company") or {}).get("gleif") or {}).values()
                      for n in gleif_names(e)[:3] if n],
            "had_evidence": bool(r["evidence"])} for r in review_rows],
        "hints": hints, "relationships": relationships,
        "top": [{"name": r["name"], "weight": _fmt(r["weight_percent"]),
                 "country": r["issuer_country"] or "–",
                 "label": CONFIDENCE_LABELS[r["mapping_confidence"]][0],
                 "chip": CONFIDENCE_CHIPS.get(r["mapping_confidence"], "s-unbekannt"),
                 "legal_name": legal_name(r),
                 "coal": coal_cell(r),
                 "evidence": any(e["status"] == "confirmed" for e in r["evidence"])}
                for r in positions[:10]],
        "all_positions": [{"name": r["name"], "isin": r["isin"] or "–",
                           "country": r["issuer_country"] or "–",
                           "weight": _fmt(r["weight_percent"]),
                           "label": CONFIDENCE_LABELS[r["mapping_confidence"]][0],
                           "chip": CONFIDENCE_CHIPS.get(r["mapping_confidence"], "s-unbekannt"),
                           "legal_name": legal_name(r),
                           "coal": coal_cell(r),
                           "evidence": any(e["status"] == "confirmed" for e in r["evidence"])}
                          for r in positions],
        "summary": s, "fmt": _fmt,
        "readiness": criteria_readiness(criteria, report),
        "relationship_rules": report.get("relationship_rules") or [],
        "reclassified": reclassified_rows(positions, report.get("rules") or {}),
        "sensitivity": [{"threshold": _fmt(c["threshold"], 0), "coal": c, "exp": e}
                        for c, e in zip(s.get("coal_sensitivity") or [],
                                        s.get("expansion_sensitivity") or [], strict=False)],
        "cases": [case_view(r, report) for isin in report.get("cases") or []
                  for r in positions if r["isin"] == isin],
        "mapping": mapping_view(report, positions),
    }


def mapping_view(report: dict[str, Any], positions: list[dict[str, Any]]) -> dict[str, Any]:
    """Verfahren, Messung und der Verbleib der Positionen ohne Kennungsweg."""
    evaluation = report.get("mapping_evaluation") or {}
    start = [r for r in positions if r["isin_valid"] and (
        r["mapping_confidence"] in ("unknown", "no_lei", "name_proposal")
        or r.get("mapping_signal") in ("unknown", "no_lei"))]
    outcome: Counter[str] = Counter()
    rows = []
    for r in sorted(start, key=lambda x: -(x["weight_percent"] or 0)):
        auto = r.get("auto_match") or {}
        name = auto.get("name") or {}
        register = auto.get("register") or {}
        origin = r.get("mapping_signal") or r["mapping_confidence"]
        if r["mapping_confidence"] in CONFIRMED_MAPPING:
            result = CONFIDENCE_LABELS[r["mapping_confidence"]][0]
        elif r["mapping_confidence"] == "name_proposal":
            result = "Vorschlag, offen (Verfahren nicht freigegeben)"
        elif name.get("status") == "ambiguous":
            result = "offen: mehrere gleichnamige Rechtsträger"
        elif name.get("status") == "too_many":
            result = "offen: Name zu allgemein"
        elif name.get("status") in (None, "not_searched"):
            result = "offen: Namenssuche nicht durchgeführt"
        else:
            result = "offen: kein passender Rechtsträger bei GLEIF"
        outcome[result] += 1
        rows.append({"name": r["name"], "isin": r["isin"], "country": r["issuer_country"] or "–",
                     "weight": _fmt(r["weight_percent"]),
                     "origin": OPEN_REASONS.get(origin, origin), "result": result,
                     "register": register.get("reason") or "–",
                     "name_reason": name.get("reason") or "–",
                     "lei": ((r.get("company") or {}).get("leis") or ["–"])[0]})
    return {"evaluation": evaluation, "start_count": len(start),
            "start_weight": _fmt(sum(r["weight_percent"] or 0 for r in start)),
            "outcome": outcome.most_common(), "rows": rows}


def render_html(report: dict[str, Any], criteria: list[dict[str, Any]]) -> str:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(Path(__file__).resolve().parent / "templates")),
        autoescape=True, trim_blocks=True, lstrip_blocks=True,
        undefined=jinja2.StrictUndefined)
    return env.get_template("fund_chain_report.html.j2").render(**html_context(report, criteria))


def render_markdown(report: dict[str, Any]) -> str:
    """Technische Fassung für Prüfung und Versionsvergleich (der HTML-Bericht ist für Laien)."""
    fund, summary = report["fund"], report["summary"]
    lines = [
        f"# Pilotanalyse (technisch): {fund['fund_name']}", "",
        f"Positionen: {report['attribution']['positions']} ({report['attribution']['terms']}).",
        f"Fondsgesellschaft laut Meldung: {fund['manager_name']}. Fonds-ISIN: {fund['fund_isin']}.",
        "", "**Lokaler Pilot, nicht veröffentlicht.** Keine Bewertung, keine Empfehlung. "
        "Nicht zugeordnete Positionen sind «unbekannt», nicht «unbedenklich».", "",
        "## Abdeckung", "", "| Stufe | Positionen | Gewicht in % |", "|---|---:|---:|",
    ]
    for label, key in (
            ("Alle Positionen", "all"), ("mit gültiger ISIN", "with_valid_isin"),
            ("mit Unternehmenshinweis (Wikidata, unbestätigt)", "with_company_candidate"),
            ("davon mit genau einem LEI", "with_unique_lei"),
            ("**widerspruchsfrei zugeordnet (bestätigte Abdeckung)**", "confirmed_coverage"),
            ("**mit zugeordnetem Emissionsbeleg**", "with_confirmed_evidence"),
            ("– davon SwissPRTR", "with_confirmed_evidence_swissprtr"),
            ("– davon EU-Emissionshandel", "with_confirmed_evidence_eu_ets"),
            ("separat: Identitätskonflikt im Register", "with_identity_conflict"),
            ("separat: Beleg, aber Position nicht widerspruchsfrei",
             "with_evidence_mapping_unconfirmed"),
            ("separat: Beleg nur ausserhalb des Beziehungszeitraums",
             "with_evidence_timing_only"),
            ("separat: nur unbestätigter Konzernhinweis", "with_group_hint_only")):
        lines.append(f"| {label} | {summary[key]['positions']} | "
                     f"{_fmt(summary[key]['weight_percent'])} |")
    lines += ["", "## Zuordnungssicherheit", "", "| Stufe | Positionen | Gewicht in % |",
              "|---|---:|---:|"]
    for key, (label, _text) in CONFIDENCE_LABELS.items():
        item = summary["by_mapping_confidence"].get(key)
        if item:
            lines.append(f"| {label} | {item['positions']} | {_fmt(item['weight_percent'])} |")
    for title, wanted in (("Zugeordnete Emissionsbelege", ("confirmed",)),
                          ("Separat: nicht mitgezählte Belege", (*BLOCK_PRIORITY,))):
        lines += ["", f"## {title}", ""]
        for row in sorted(report["positions"], key=lambda r: -(r["weight_percent"] or 0)):
            selected = [e for e in row["evidence"] if e["status"] in wanted]
            if not selected:
                continue
            lines.append(f"### {row['name']} ({row['isin']}, {_fmt(row['weight_percent'])} %)")
            lines.append(f"- Zuordnung: {CONFIDENCE_LABELS[row['mapping_confidence']][0]}; "
                         f"LEI {', '.join(row['company']['leis'])}.")
            for evidence in selected:
                lines += render_evidence(evidence)
            lines.append("")
    lines += ["## Konzernhinweise ohne Bestätigung (kein Beleg übertragen)", ""]
    for row in report["positions"]:
        for hint in row["group_hints"]:
            lines.append(
                f"- {row['name']}: «{hint['child_legal_name'] or hint['child_lei']}» "
                f"({hint['kind']}, {hint['corroboration_level']}, seit "
                f"{_fmt_date((hint.get('timing') or {}).get('start'))}).")
    evaluation = report.get("mapping_evaluation") or {}
    if evaluation:
        lines += ["", "## Automatische Zuordnung: Präzision und Abdeckung getrennt", "",
                  "| Verfahren | Referenzfälle | mit Ergebnis | richtig | falsch | Präzision | "
                  "untere 95-%-Grenze | freigegeben |", "|---|---:|---:|---:|---:|---:|---:|---|"]
        for key in ("name", "register"):
            e = evaluation[key]
            lines.append(f"| {key} | {e['reference_cases']} | {e['answered']} | {e['correct']} "
                         f"| {e['wrong']} | {e['precision']} | {e['precision_lower_bound_95']} "
                         f"| {e['released']} |")
        for case in evaluation["name"].get("wrong_cases", []):
            lines.append(f"- Abweichung: {case['position_name']} ({case['isin']}, {case['fund']}):"
                         f" Referenz {case['reference_lei']}, Namenssuche {case['predicted_lei']}")
    rows = reclassified_rows(sorted(report["positions"], key=lambda r: -(r["weight_percent"]
                                                                         or 0)),
                             report.get("rules") or {})
    if rows:
        lines += ["", "## Kohle und fossile Expansion: alle Treffer nach Beziehungstyp", "",
                  "| Position | Gewicht % | Beziehungen | Kohle vorher → jetzt | Expansion vorher "
                  "→ jetzt |", "|---|---:|---|---|---|"]
        for r in rows:
            lines.append(
                f"| {r['name']} | {r['weight']} | {r['relationships']} | "
                f"{'K' if r['coal_old'] else '–'} → {'K' if r['coal_new'] else '–'}: "
                f"{r['coal_why']} | {'K' if r['exp_old'] else '–'} → "
                f"{'K' if r['exp_new'] else '–'}: {r['exp_why']} |")
    lines += ["", f"Quelle Emissionen Schweiz: {PRTR_ATTRIBUTION}."]
    if "eu_ets" in report["attribution"]:
        text, terms = report["attribution"]["eu_ets"]
        lines.append(f"Quelle Emissionshandel: {text}. Nutzungsbedingungen (Auslegung): {terms}.")
    lines += ["Quelle Zuordnung: Wikidata (CC0), GLEIF (CC0).", ""]
    rows = provenance_rows(report)
    if rows:
        lines += ["## Herkunft der Eingabedateien", "",
                  "Pfad relativ zum Datenordner. Prüfsumme bei jedem Lauf neu berechnet und mit "
                  "der Begleitdatei vom Download verglichen (D-052).", "",
                  "| Quelle | Datei | Grösse | SHA-256 | Prüfung | Lizenz | Stand | Ursprung |",
                  "|---|---|---:|---|---|---|---|---|"]
        for r in rows:
            lines.append(f"| {r['source']} | {r['path']} | {r['size']} | `{r['sha256']}` | "
                         f"{r['status']} | {r['licence']} | {r['retrieved']} | {r['origin']} |")
        lines.append("")
    return "\n".join(lines)


def provenance_rows(report: dict[str, Any]) -> list[dict[str, str]]:
    """Eingabedateien für die Anzeige; ohne Begleitdatei steht «nicht erfasst», nie ein Wert."""
    rows = []
    for item in report.get("provenance") or []:
        checked = item["status"] in ("verified", "derived")
        rows.append({
            "source": item.get("source_key") or "–",
            "path": item["path"],
            "size": f"{item['bytes'] / 1_000_000:,.1f} MB".replace(",", "'"),
            "sha256": item["sha256"],
            "sha_short": item["sha256"][:12],
            "status": PROVENANCE_STATUS_LABELS.get(item["status"], item["status"]),
            "licence": item.get("licence") or ("keine benannte Lizenz" if checked else "–"),
            "retrieved": item.get("retrieved") or "–",
            "origin": item.get("derived_from") or item.get("recorded_in") or "–",
        })
    return rows


def render_evidence(evidence: dict[str, Any]) -> list[str]:
    view = _evidence_view(evidence)
    lines = [f"- {view['source']} ({view['status']}): {view['path']}. {view['headline']}"
             + (f"; Kontoinhaber «{view['holder']}»" if view["holder"] else "")
             + f". Stand {view['as_of']}. Amtlich gemeldete bzw. verifizierte Jahreswerte, "
             "kein Nachweis eines Rechtsverstosses."]
    if evidence.get("name_check") == "different":
        lines.append("  - **Sichtprüfung nötig:** Kontoinhaber im Register und Rechtsname des LEI "
                     "bei GLEIF teilen kein Wort; möglicherweise trägt das Register den LEI einer "
                     "anderen Konzerngesellschaft.")
    for item in view["rows"]:
        revoked = f", Genehmigung widerrufen {item['revoked']}" if item["revoked"] else ""
        lines.append(f"  - {item['id']} «{item['name']}» ({item['activity']}{revoked}): "
                     f"{item['latest']}")
    return lines
