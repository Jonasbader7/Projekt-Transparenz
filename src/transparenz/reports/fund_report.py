"""Tabellen und Markdown-Bericht aus einem Screening-Ergebnis (deterministisch)."""

from __future__ import annotations

import pandas as pd

from transparenz.entities.enums import AssessmentStatus
from transparenz.entities.labels import SHORT_STATUS, label
from transparenz.reports.texts import finding_sentence, provenance, status_explanation
from transparenz.screening.engine import EvidenceMatch, FundScreeningResult, PositionResult
from transparenz.utils.timeutil import format_date

DISCLAIMER = (
    "Diese Auswertung ist eine Informations- und Analysehilfe. Sie gibt wieder, was "
    "die genannten Quellen berichten oder festgestellt haben, und enthält keine Empfehlung "
    "zum Kauf, Verkauf oder Halten von Finanzinstrumenten. Vorwürfe sind keine bewiesenen "
    "Verstösse. «Unbekannt» bedeutet fehlende Daten, nicht Unbedenklichkeit."
)


def issuer_text(p: PositionResult) -> str:
    if not p.applicable:
        return "–"
    if p.company is None:
        return "nicht identifiziert"
    return p.company.name


def positions_table(result: FundScreeningResult, short: bool = False) -> pd.DataFrame:
    status_text = (lambda s: SHORT_STATUS[s]) if short else label
    rows = []
    for p in result.positions:
        # Reihenfolge: das Wichtigste (Belegstatus) zuerst, Kennungen danach
        row: dict[str, object] = {
            "Position": p.position.name,
            "Gewicht %": round(p.position.weight_pct, 2),
        }
        for c in result.criteria:
            row[c.name] = status_text(p.assessments[c.key].status)
        row |= {
            "Emittent": issuer_text(p),
            "Zuordnung": (
                f"{label(p.issuer_resolution.method)} ({label(p.issuer_resolution.confidence)})"
                if p.company else p.issuer_resolution.note
            ),
            "Anlageklasse": label(p.position.asset_class),
            "ISIN": p.position.isin or "–",
            "LEI": (p.company.lei if p.company and p.company.lei else "–"),
        }
        rows.append(row)
    return pd.DataFrame(rows)


def _match_role(m: EvidenceMatch, p: PositionResult, crit_key: str) -> str:
    a = p.assessments[crit_key]
    if a.decisive is m:
        return "massgebend"
    if m in a.supporting:
        return "stützend"
    if m in a.context:
        return "Kontext"
    if m in a.unverified_parent_evidence:
        return "nicht übernommen (Konzern unverifiziert)"
    return "nicht gezählt"


def findings_table(
    result: FundScreeningResult, source_names: dict[str, str] | None = None
) -> pd.DataFrame:
    rows = []
    for p in result.positions:
        for c in result.criteria:
            a = p.assessments[c.key]
            for m in [*a.supporting, *a.context, *a.not_counted, *a.unverified_parent_evidence]:
                r = m.record
                rows.append(
                    {
                        "Position": p.position.name,
                        "Betroffenes Unternehmen": m.matched_company.name,
                        "Kriterium": c.name,
                        "Status Kriterium": label(a.status),
                        "Rolle": _match_role(m, p, c.key),
                        "Art": label(r.evidence_type),
                        "Verfahren": label(r.proceeding_status),
                        "Herausgeber": r.publisher,
                        "Quellenstufe": label(r.tier),
                        "Veröffentlicht": format_date(r.published_date),
                        "Ereignis": format_date(r.event_date),
                        "Verifizierung": label(r.verification_level),
                        "Letzte Überprüfung": format_date(r.last_reviewed),
                        "Zuordnung": (
                            f"{label(m.resolution.method)} ({label(m.resolution.confidence)})"
                        ),
                        "Schwellenwert": label(m.threshold_check),
                        "Aussage (quellenbasiert)": finding_sentence(m),
                        "Quelle": r.source_title,
                        "URL": r.source_url,
                        "Datenstand": provenance(m, source_names),
                    }
                )
    return pd.DataFrame(rows)


def to_markdown(
    result: FundScreeningResult,
    display_name: str,
    data_versions: list[str],
    source_names: dict[str, str] | None = None,
) -> str:
    f = result.fund
    lines = [
        f"# {display_name} – Fondsanalyse: {f.name}",
        "",
        f"ISIN {f.isin} · Anbieter {f.provider} · Positionen per {format_date(f.as_of_date)}"
        f" · Auswertung per {format_date(result.as_of)}",
        "",
    ]
    if f.is_fictional:
        lines += ["> **Fiktive Demodaten.** Fonds, Unternehmen und Quellen sind erfunden.", ""]
    lines += [f"> {DISCLAIMER}", "", "## Zusammenfassung pro Kriterium (Anteil Fondsgewicht)", ""]
    statuses = [s for s in AssessmentStatus]
    lines.append("| Kriterium | " + " | ".join(label(s) for s in statuses) + " |")
    lines.append("|---|" + "---|" * len(statuses))
    for c in result.criteria:
        s = result.summaries[c.key]
        lines.append(
            f"| {c.name} | "
            + " | ".join(f"{s.weight_by_status[x]:.1f} %" for x in statuses)
            + " |"
        )
    lines += ["", "## Positionen mit Belegen", ""]
    for p in result.positions:
        if not p.has_finding:
            continue
        lines.append(f"### {p.position.name} ({p.position.weight_pct:.2f} %)")
        lines.append(f"Emittent: {issuer_text(p)}")
        for c in result.criteria:
            a = p.assessments[c.key]
            if not a.has_finding:
                continue
            lines.append(f"- **{c.name}: {label(a.status)}** – {status_explanation(a)}")
            for m in [*a.supporting, *a.context]:
                lines.append(f"  - {finding_sentence(m)}")
                lines.append(f"    Quelle: {m.record.source_title} – {m.record.source_url}")
                lines.append(f"    {provenance(m, source_names)}")
            for flag in a.flags:
                lines.append(f"  - Hinweis: {flag}")
        lines.append("")
    other = [
        (p, c, a)
        for p in result.positions
        for c in result.criteria
        if not (a := p.assessments[c.key]).has_finding and a.flags and p.company is not None
    ]
    if other:
        lines += ["## Weitere Hinweise (ohne übernommenen Beleg)", ""]
        for p, c, a in other:
            for flag in a.flags:
                lines.append(f"- {p.position.name} – {c.name}: {flag}")
        lines.append("")
    unknown = [p for p in result.positions if p.applicable and p.company is None]
    lines += ["## Datenlücken", ""]
    lines.append(
        f"- Nicht identifizierte Emittenten: {len(unknown)} Position(en), "
        f"{result.unidentified_weight:.2f} % Gewicht."
    )
    for c in result.criteria:
        w = result.summaries[c.key].weight_by_status[AssessmentStatus.UNBEKANNT]
        lines.append(f"- {c.name}: {w:.1f} % des Fondsgewichts ohne Datenabdeckung.")
    if result.unresolved_evidence:
        lines.append(
            f"- {len(result.unresolved_evidence)} Sachverhalt(e) konnten keinem Unternehmen "
            "zugeordnet werden und fliessen nicht ein:"
        )
        for ev, res in result.unresolved_evidence:
            lines.append(
                f"  - {ev.record.evidence_id} «{ev.record.company_name}» "
                f"({ev.record.publisher}): {res.note}"
            )
    lines += ["", "## Datenstände", ""]
    lines += [f"- {v}" for v in data_versions]
    lines.append("")
    return "\n".join(lines)
