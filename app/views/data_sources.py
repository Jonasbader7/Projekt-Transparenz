"""Datenquellen & Aktualität: Lizenzen, Datenstände, Update-Protokoll, manueller Auslöser."""

from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from transparenz.database.repository import recent_runs
from transparenz.entities.enums import UpdateStatus
from transparenz.entities.labels import label
from transparenz.utils.timeutil import format_date, format_datetime

from ui import get_context

ctx = get_context()
st.title("Datenquellen & Aktualität")
st.markdown(
    "Öffentlich zugänglich heisst nicht kommerziell nutzbar – Lizenz und Nutzungsrecht "
    "stehen deshalb bei jeder Quelle. Aktuell sind **ausschliesslich fiktive Demoquellen** "
    "angebunden; Kandidaten für echte Quellen stehen in `docs/DATA_SOURCES.md`."
)

fresh = ctx.updates.freshness()
rows = []
for f in fresh:
    v = f.active_version
    rows.append(
        {
            "Quelle": f.config.name,
            "Art": label(f.config.kind),
            "Herausgeber": f.config.publisher,
            "Fiktiv": "ja" if f.config.is_fictional else "nein",
            "Lizenz": f.config.license,
            "Kommerziell nutzbar": label(f.config.commercial_use),
            "Datenstand": format_date(f.data_as_of),
            "Zuletzt geprüft": format_datetime(f.last_check_at),
            "Alter (Tage)": f.age_days if f.age_days is not None else "–",
            "Max. Alter": f.config.max_age_days,
            "Zustand": "deaktiviert" if not f.config.enabled
            else ("VERALTET" if f.is_stale else "aktuell"),
            "Version": f"#{v.id} · {v.content_hash[:10]}" if v else "kein gültiger Stand",
            "Letzter Lauf": label(UpdateStatus(f.last_run.status)) if f.last_run else "–",
        }
    )
st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
stale = [f.config.name for f in fresh if f.is_stale]
if stale:
    st.warning("Veraltet oder ohne gültigen Stand: " + ", ".join(stale))

st.subheader("Aktualisierung manuell auslösen")
st.caption(
    "Fehlerhafte neue Daten werden abgelehnt; der letzte gültige Stand bleibt dann aktiv. "
    "Jeder Versuch wird protokolliert."
)
c1, c2, c3 = st.columns([2, 1, 1])
options = ["Alle Quellen", *[s.key for s in ctx.catalog.sources]]
target = c1.selectbox("Quelle", options)
force = c2.checkbox("Intervall ignorieren", value=False,
                    help="Sonst werden noch nicht fällige Quellen übersprungen.")
if c3.button("Jetzt aktualisieren", type="primary"):
    with st.spinner("Aktualisierung läuft …"):
        if target == "Alle Quellen":
            outcomes = ctx.updates.run_all(force=force, trigger="app")
        else:
            outcomes = [ctx.updates.run_source(target, force=force, trigger="app")]
    for o in outcomes:
        msg = f"**{o.source_key}**: {label(o.status)} – {o.message}"
        if o.status in (UpdateStatus.FEHLGESCHLAGEN, UpdateStatus.GESPERRT):
            st.error(msg + ("\n\n" + "; ".join(o.errors) if o.errors else ""))
        else:
            st.success(msg)

st.subheader("Update-Protokoll")
with ctx.session_factory() as session:
    runs = recent_runs(session, limit=50)
if not runs:
    st.info("Noch keine Aktualisierungen protokolliert.")
else:
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Start": format_datetime(r.started_at),
                    "Quelle": r.source_key,
                    "Auslöser": r.trigger,
                    "Ergebnis": label(UpdateStatus(r.status)),
                    "Versuche": r.attempts,
                    "Version": f"#{r.dataset_version_id}" if r.dataset_version_id else "–",
                    "Meldung": r.message,
                }
                for r in runs
            ]
        ),
        hide_index=True,
        width="stretch",
    )
    failed = [r for r in runs if r.status == UpdateStatus.FEHLGESCHLAGEN.value]
    for r in failed[:10]:
        with st.expander(f"Fehlgeschlagen: {r.source_key} · {format_datetime(r.started_at)}"):
            for err in json.loads(r.errors_json or "[]"):
                st.markdown(f"- {err}")
            if r.raw_path:
                st.caption(f"Abgelehnte Rohdaten aufbewahrt unter: {r.raw_path}")

st.subheader("Wo die Daten liegen")
st.markdown(
    f"- Datenbank: `{ctx.settings.database_url.split('///')[-1]}` (lokal, SQLite)\n"
    "- Rohdaten-Schnappschüsse: `data/raw/<quelle>/` (abgelehnte unter `abgelehnt/`)\n"
    "- GitHub Actions speichert nichts dauerhaft – siehe `docs/ARCHITECTURE.md`."
)
