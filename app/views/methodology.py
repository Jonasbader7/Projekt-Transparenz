"""Methodik: zeigt die Methodik-Dokumente (einzige Quelle: docs/methodik/)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ui import get_context

ctx = get_context()
st.title("Methodik")
st.markdown(
    "Die Methodik ist offen. Diese Seite zeigt dieselben Dokumente, die im Repository "
    "unter `docs/methodik/` liegen – es gibt keine zweite, versteckte Version."
)

st.subheader("Aktive Ausschlusskriterien")
st.dataframe(
    pd.DataFrame(
        [
            {
                "Kriterium": c.name,
                "Beschreibung": c.description,
                "Schwere": c.severity,
                "Kennzahl": c.metric or "–",
                "Schwellenwert": f"{c.threshold:g} {c.metric_unit or ''}"
                if c.threshold is not None else "offen",
                "Bemerkung": c.threshold_note,
            }
            for c in ctx.catalog.criteria
        ]
    ),
    hide_index=True,
    width="stretch",
)

docs = ctx.settings.docs_dir / "methodik"
tabs = st.tabs(["Belegmodell & Validierung", "Quellen-Hierarchie", "Ausschlusskriterien"])
for tab, name in zip(
    tabs, ["validierung.md", "quellen-hierarchie.md", "ausschlusskriterien.md"], strict=True
):
    with tab:
        path = docs / name
        if path.exists():
            st.markdown(path.read_text(encoding="utf-8"))
        else:
            st.error(f"Dokument fehlt: docs/methodik/{name}")
