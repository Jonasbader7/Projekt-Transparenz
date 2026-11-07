"""Fondsanalyse: Positionen, Belege mit Quelle und Datenstand, Datenlücken."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from transparenz.entities.enums import AssessmentStatus
from transparenz.entities.labels import SHORT_STATUS, label
from transparenz.reports.fund_report import (
    findings_table,
    issuer_text,
    positions_table,
    to_markdown,
)
from transparenz.reports.texts import finding_sentence, provenance, status_explanation
from transparenz.screening.engine import EvidenceMatch
from transparenz.utils.timeutil import format_date

from ui import disclaimer, fictional_banner, get_context, status_badge, style_status_columns


def _table_height(rows: int) -> int:
    """Höhe so, dass alle Zeilen ohne inneres Scrollen sichtbar sind."""
    return 38 + 35 * max(rows, 1)


ctx = get_context()
data = ctx.active_data()
if not data.funds:
    st.title("Fondsanalyse")
    st.info("Noch keine Fondsdaten vorhanden. Bitte zuerst Daten importieren.")
    st.page_link("views/data_sources.py", label="Zu Datenquellen & Aktualität")
    st.stop()

snaps = sorted(data.funds.values(), key=lambda s: s.fund.name)
isin = st.selectbox(
    "Fonds",
    [s.fund.isin for s in snaps],
    format_func=lambda i: f"{data.funds[i].fund.name} ({i})",
)
result = ctx.analyze_fund(isin, data=data)
assert result is not None
fund = result.fund
names = ctx.source_names

st.title(fund.name)
st.caption(
    f"ISIN {fund.isin} · {fund.provider} · Positionen per {format_date(fund.as_of_date)} · "
    f"Auswertung per {format_date(result.as_of)}"
)
if fund.is_fictional:
    fictional_banner()
disclaimer()

# ------------------------------------------------------------------ Kennzahlen
k1, k2, k3, k4 = st.columns(4)
k1.metric("Positionen", len(result.positions))
k2.metric("Gewicht mit Belegen", f"{result.weight_with_finding:.1f} %",
          help="Positionen mit mindestens einem Beleg zu mindestens einem Kriterium.")
k3.metric("davon festgestellt", f"{result.weight_with_status(AssessmentStatus.FESTGESTELLT):.1f} %",
          help="Gerichtlich/behördlich rechtskräftig festgestellt, Dokument von uns geprüft.")
k4.metric("Emittent nicht identifiziert", f"{result.unidentified_weight:.1f} %")

# ------------------------------------------------------------- pro Kriterium
st.subheader("Überblick pro Kriterium")
st.caption("Anteil am Fondsgewicht je Belegstatus. Jedes Kriterium steht für sich – "
           "es gibt keinen Gesamtwert.")
statuses = [s for s in AssessmentStatus if s != AssessmentStatus.NICHT_ANWENDBAR]
summary = pd.DataFrame(
    [
        {"Belegstatus": SHORT_STATUS[s]}
        | {c.name: round(result.summaries[c.key].weight_by_status[s], 1) for c in result.criteria}
        for s in statuses
    ]
)
st.dataframe(
    style_status_columns(summary, ["Belegstatus"]),
    hide_index=True,
    width="stretch",
    height=_table_height(len(summary)),
    column_config={c.name: st.column_config.NumberColumn(format="%.1f %%")
                   for c in result.criteria},
)
na_weight = result.total_weight - result.screenable_weight
if na_weight:
    st.caption(f"Nicht nach Emittent prüfbar (Barmittel, Derivate): {na_weight:.1f} % – "
               "in allen Kriterien gleich.")

# ----------------------------------------------------------------- Positionen
st.subheader("Positionen")
only_findings = st.toggle("Nur Positionen mit Belegen anzeigen", value=False)
table = positions_table(result, short=True)
if only_findings:
    keep = [p.has_finding for p in result.positions]
    table = table[keep]
crit_cols = [c.name for c in result.criteria]
st.dataframe(
    style_status_columns(table, crit_cols),
    hide_index=True,
    width="stretch",
    height=_table_height(len(table)),
    column_config={"Gewicht %": st.column_config.NumberColumn(format="%.2f"),
                   "Position": st.column_config.TextColumn(pinned=True)},
)

# ------------------------------------------------------------------- Belege
st.subheader("Belege im Detail")
st.caption("Jede Aussage gibt eine Quelle wieder. Unter jeder Aussage steht, aus welchem "
           "Datenstand sie stammt.")


def _render_match(m: EvidenceMatch, role: str) -> None:
    r = m.record
    st.markdown(f"**{role}:** {finding_sentence(m)}")
    st.caption(
        f"{label(r.evidence_type)} · Verfahren {label(r.proceeding_status)} · "
        f"{label(r.tier)} · Verifizierung: {label(r.verification_level)} · "
        f"letzte Überprüfung {format_date(r.last_reviewed)} · "
        f"Zuordnung {label(m.resolution.method)} ({label(m.resolution.confidence)})"
    )
    st.caption(f"Quelle: [{r.source_title}]({r.source_url})  \n{provenance(m, names)}")


with_findings = [p for p in result.positions if p.has_finding]
if not with_findings:
    st.info("Zu keiner Position liegen Belege vor. Das ist kein Nachweis von Nachhaltigkeit – "
            "siehe Datenlücken.")
for p in with_findings:
    title = (f"{p.position.name} · {p.position.weight_pct:.2f} % · "
             f"stärkster Status: {SHORT_STATUS[p.strongest_status]}")
    with st.expander(title):
        st.markdown(f"Emittent: **{issuer_text(p)}**"
                    + (f" (LEI {p.company.lei})" if p.company and p.company.lei else ""))
        if p.verified_parents:
            st.caption("Verifizierte Muttergesellschaft(en): "
                       + ", ".join(c.name for c in p.verified_parents))
        for c in result.criteria:
            a = p.assessments[c.key]
            if not a.has_finding:
                continue
            st.markdown(f"#### {c.name}")
            status_badge(a.status)
            st.markdown(status_explanation(a))
            for m in a.supporting:
                _render_match(m, "Massgebend" if m is a.decisive else "Weiterer Beleg")
            for m in a.context:
                _render_match(m, "Kontext")
            for m in a.not_counted:
                _render_match(m, "Nicht gezählt")
            for flag in a.flags:
                st.caption(f"⚠ {flag}")

# ------------------------------------------------------------- Datenlücken
st.subheader("Datenlücken und Unsicherheiten")
gap_rows = [
    {"Kriterium": c.name,
     "Gewicht ohne Datenabdeckung %": round(
         result.summaries[c.key].weight_by_status[AssessmentStatus.UNBEKANNT], 1)}
    for c in result.criteria
]
st.dataframe(pd.DataFrame(gap_rows), hide_index=True, width="stretch")

unknown = [p for p in result.positions if p.applicable and p.company is None]
if unknown:
    st.markdown("**Emittent nicht identifiziert** – für diese Positionen ist jede Aussage "
                "«unbekannt»:")
    for p in unknown:
        st.markdown(f"- {p.position.name} ({p.position.isin or 'ohne ISIN'}, "
                    f"{p.position.weight_pct:.2f} %): {p.issuer_resolution.note}")
if result.low_confidence_mappings:
    st.markdown("**Unsichere Zuordnung Wertpapier → Unternehmen:**")
    for p in result.low_confidence_mappings:
        st.markdown(f"- {p.position.name}: {p.issuer_resolution.note} "
                    f"(Vertrauen {label(p.issuer_resolution.confidence)})")
hints = [
    (p, c, a) for p in result.positions for c in result.criteria
    if p.company is not None and not (a := p.assessments[c.key]).has_finding and a.flags
]
if hints:
    st.markdown("**Weitere Hinweise ohne übernommenen Beleg:**")
    for p, c, a in hints:
        for flag in a.flags:
            st.markdown(f"- {p.position.name} – {c.name}: {flag}")
if result.unresolved_evidence:
    st.markdown("**Sachverhalte ohne Zuordnung** (fliessen nicht in die Auswertung ein):")
    st.dataframe(
        pd.DataFrame(
            [{"Datensatz": ev.record.evidence_id, "Name in Quelle": ev.record.company_name,
              "LEI in Quelle": ev.record.lei or "–", "Herausgeber": ev.record.publisher,
              "Grund": res.note} for ev, res in result.unresolved_evidence]
        ),
        hide_index=True,
        width="stretch",
    )

# ------------------------------------------------------------------- Export
st.subheader("Bericht exportieren")
md = to_markdown(result, ctx.settings.display_name, ctx.data_version_lines(data), names)
e1, e2 = st.columns(2)
e1.download_button("Bericht (Markdown)", md, file_name=f"analyse_{fund.isin}.md",
                   mime="text/markdown", icon=":material/description:")
e2.download_button(
    "Alle Belege (CSV)",
    findings_table(result, names).to_csv(index=False).encode("utf-8-sig"),
    file_name=f"belege_{fund.isin}.csv",
    mime="text/csv",
    icon=":material/table:",
)
with st.expander("Zugrunde liegende Datenstände"):
    for line in ctx.data_version_lines(data):
        st.markdown(f"- {line}")
