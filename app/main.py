"""Einstieg der Streamlit-App.

Start (im Projektordner):  streamlit run app/main.py
"""

# ruff: noqa: I001  – «ui» muss vor «transparenz» importiert werden (setzt den Importpfad)
from __future__ import annotations

import streamlit as st

import ui  # noqa: F401
from transparenz.config.settings import load_settings
from transparenz.utils.logging_setup import setup_logging

settings = load_settings()
setup_logging(settings.log_level)

st.set_page_config(
    page_title=settings.display_name,
    page_icon=":material/visibility:",
    layout="wide",
)

pages = [
    st.Page("views/overview.py", title="Übersicht", icon=":material/home:", default=True),
    st.Page("views/fund_analysis.py", title="Fondsanalyse", icon=":material/search:"),
    st.Page("views/methodology.py", title="Methodik", icon=":material/menu_book:"),
    st.Page("views/data_sources.py", title="Datenquellen & Aktualität",
            icon=":material/database:"),
]
nav = st.navigation(pages)
with st.sidebar:
    st.markdown(f"**{settings.display_name}**")
    st.caption("Forschungsprototyp · nur Information, keine Anlageempfehlung")
nav.run()
