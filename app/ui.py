"""Gemeinsame Bausteine der Streamlit-App (Kontext, Farben, Hinweise)."""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:  # funktioniert auch ohne «pip install -e .»
    sys.path.insert(0, str(_SRC))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from transparenz.config.settings import load_settings  # noqa: E402
from transparenz.entities.enums import AssessmentStatus  # noqa: E402
from transparenz.entities.labels import SHORT_STATUS  # noqa: E402
from transparenz.reports.fund_report import DISCLAIMER  # noqa: E402
from transparenz.services.context import AppContext, create_context  # noqa: E402

# Ruhige Farbtöne. «Unbekannt» ist bewusst auffällig (gelb): Datenlücken sollen
# sichtbar sein. «Keine Hinweise» ist neutral grau, NICHT grün – es ist kein
# Nachweis von Nachhaltigkeit.
STATUS_BG: dict[AssessmentStatus, str] = {
    AssessmentStatus.FESTGESTELLT: "#F2C4BD",
    AssessmentStatus.PRUEFUNG_AUSSTEHEND: "#F6D7B0",
    AssessmentStatus.VERFAHREN_LAUFEND: "#F6D7B0",
    AssessmentStatus.DOKUMENTIERT: "#DCD3EC",
    AssessmentStatus.MEDIENBERICHT: "#D3E0EE",
    AssessmentStatus.ZUORDNUNG_UNSICHER: "#F3E9B5",
    AssessmentStatus.UNBEKANNT: "#F3E9B5",
    AssessmentStatus.KEINE_HINWEISE: "#E7E5DF",
    AssessmentStatus.NICHT_ANWENDBAR: "#F4F3EF",
}
STATUS_BADGE: dict[AssessmentStatus, str] = {
    AssessmentStatus.FESTGESTELLT: "red",
    AssessmentStatus.PRUEFUNG_AUSSTEHEND: "orange",
    AssessmentStatus.VERFAHREN_LAUFEND: "orange",
    AssessmentStatus.DOKUMENTIERT: "violet",
    AssessmentStatus.MEDIENBERICHT: "blue",
    AssessmentStatus.ZUORDNUNG_UNSICHER: "yellow",
    AssessmentStatus.UNBEKANNT: "yellow",
    AssessmentStatus.KEINE_HINWEISE: "gray",
    AssessmentStatus.NICHT_ANWENDBAR: "gray",
}
_BG_BY_SHORT = {SHORT_STATUS[s]: c for s, c in STATUS_BG.items()}


@st.cache_resource(show_spinner=False)
def _context(database_url: str) -> AppContext:
    return create_context(load_settings())


def get_context() -> AppContext:
    """Ein Kontext pro Datenbank-URL (Tests nutzen eigene Datenbanken)."""
    return _context(load_settings().database_url)


def status_badge(status: AssessmentStatus) -> None:
    st.badge(SHORT_STATUS[status], color=STATUS_BADGE[status])  # type: ignore[arg-type]


def style_status_columns(df: pd.DataFrame, columns: list[str]):  # type: ignore[no-untyped-def]
    """Färbt Statuszellen dezent ein (nur Anzeige, keine Bewertung)."""

    def _color(value: object) -> str:
        bg = _BG_BY_SHORT.get(str(value))
        return f"background-color: {bg}; color: #1F2421" if bg else ""

    return df.style.map(_color, subset=columns)


def disclaimer() -> None:
    st.caption(DISCLAIMER)


def fictional_banner() -> None:
    st.warning(
        "**Fiktive Demodaten.** Fonds, Unternehmen, Kennungen und Quellen in dieser "
        "Demo sind erfunden. Ähnlichkeiten mit realen Unternehmen sind nicht beabsichtigt.",
        icon=":material/science:",
    )
