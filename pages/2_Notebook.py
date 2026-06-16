"""Notebook — the full, automatically timestamped record."""

from __future__ import annotations

import datetime as dt

import streamlit as st

import ui_common as ui
from core import notebook
from core.models import ENTRY_TYPE_LABELS, ENTRY_TYPES

st.set_page_config(page_title="Notebook · Seshat", page_icon="🪶", layout="wide")
conn = ui.get_conn()
ui.encryption_badge()

st.title("📓 Lab Notebook")

c1, c2, c3 = st.columns(3)
use_date = c1.checkbox("Filter by date", value=False)
on_date = c1.date_input("Date", value=dt.date.today()) if use_date else None
type_choice = c2.selectbox(
    "Type", ["(all)"] + ENTRY_TYPES, format_func=lambda t: ENTRY_TYPE_LABELS.get(t, t)
)
source_choice = c3.selectbox("Source", ["(all)", "app", "phone"])

entries = notebook.list_entries(
    conn,
    on_date=on_date,
    entry_type=None if type_choice == "(all)" else type_choice,
    source=None if source_choice == "(all)" else source_choice,
    limit=500,
)

st.caption(f"{len(entries)} entr{'y' if len(entries) == 1 else 'ies'}")

current_day = None
for e in entries:
    day = e["created_at"][:10]
    if day != current_day:
        current_day = day
        st.subheader(dt.date.fromisoformat(day).strftime("%A, %B %d, %Y"))

    label = ENTRY_TYPE_LABELS.get(e["entry_type"], e["entry_type"])
    when = e["created_at"][11:16]
    src = " · 📲 phone" if e["source"] == "phone" else ""
    exp = f" · *{e['experiment_name']}*" if e["experiment_name"] else ""
    with st.container(border=True):
        top = st.columns([0.9, 0.1])
        top[0].markdown(f"**{when}** · {label}{exp}{src}")
        if top[1].button("🗑", key=f"del_{e['id']}", help="Delete entry"):
            notebook.delete_entry(conn, e["id"])
            st.rerun()
        st.write(e["text"])
