"""Übersicht: worum es geht, Datenlage, verfügbare Fonds."""

from __future__ import annotations

import streamlit as st

from transparenz.entities.enums import AssessmentStatus
from transparenz.entities.labels import label
from transparenz.utils.timeutil import format_date

from ui import disclaimer, get_context, status_badge

ctx = get_context()
st.title(ctx.settings.display_name)
st.markdown(
    "Fondspositionen mit nachvollziehbaren Quellen verbinden – damit Anlegerinnen und "
    "Anleger selbst beurteilen können, ob ein Fonds zu ihren Wertvorstellungen passt."
)
disclaimer()

c1, c2, c3 = st.columns(3)
with c1, st.container(border=True):
    st.markdown("**Was gezeigt wird**")
    st.markdown(
        "- welche Unternehmen in einem Fonds stecken\n"
        "- welche Belege es zu Ausschlusskriterien gibt – mit Quelle und Datum\n"
        "- wo Informationen fehlen oder unsicher sind"
    )
with c2, st.container(border=True):
    st.markdown("**Was bewusst nicht passiert**")
    st.markdown(
        "- kein Gesamtscore, keine Verrechnung zwischen Kriterien\n"
        "- keine eigenen Urteile – nur Wiedergabe von Quellen\n"
        "- keine Kauf- oder Verkaufsempfehlungen"
    )
with c3, st.container(border=True):
    st.markdown("**Wie Belege eingestuft werden**")
    for s in (
        AssessmentStatus.FESTGESTELLT,
        AssessmentStatus.VERFAHREN_LAUFEND,
        AssessmentStatus.DOKUMENTIERT,
        AssessmentStatus.MEDIENBERICHT,
        AssessmentStatus.UNBEKANNT,
    ):
        status_badge(s)
    st.caption("Massgebend ist die Art des stärksten Belegs, nicht die Anzahl Quellen.")

st.divider()
st.subheader("Datenlage")
data = ctx.active_data()
freshness = ctx.updates.freshness()
stale = [f for f in freshness if f.is_stale]
if not data.versions:
    st.info(
        "Noch keine Daten importiert. Lade die fiktiven Beispieldaten, um die Methodik "
        "auszuprobieren (lokal, keine externen Abrufe).",
        icon=":material/info:",
    )
    if st.button("Fiktive Beispieldaten laden", type="primary"):
        with st.spinner("Import läuft …"):
            outcomes = ctx.updates.run_all(force=True, trigger="app")
        for o in outcomes:
            st.write(f"{o.source_key}: {label(o.status)} – {o.message}")
        st.rerun()
    st.stop()

m1, m2, m3 = st.columns(3)
m1.metric("Aktive Datenquellen", len(data.versions))
m2.metric("Veraltete oder fehlende Quellen", len(stale))
m3.metric("Fonds im Datenbestand", len(data.funds))
if stale:
    st.warning(
        "Veraltet oder ohne gültigen Stand: " + ", ".join(f.config.name for f in stale),
        icon=":material/schedule:",
    )

st.subheader("Fonds")
for snap in sorted(data.funds.values(), key=lambda s: s.fund.name):
    with st.container(border=True):
        st.markdown(f"**{snap.fund.name}**  \nISIN {snap.fund.isin} · {snap.fund.provider}")
        st.caption(
            f"{len(snap.positions)} Positionen · Stichtag {format_date(snap.fund.as_of_date)}"
            + (" · fiktive Demodaten" if snap.fund.is_fictional else "")
        )
        st.page_link("views/fund_analysis.py", label="Zur Fondsanalyse",
                     icon=":material/arrow_forward:")
