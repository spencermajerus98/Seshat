"""Daily Summary — generate the copy-paste text for your real ELN."""

from __future__ import annotations

import datetime as dt

import streamlit as st

import ui_common as ui
from core import summary
from core.notebook import distinct_entry_dates

st.set_page_config(page_title="Daily Summary · Seshat", page_icon="🪶", layout="wide")
conn = ui.get_conn()
ui.encryption_badge()

st.title("📤 Daily Summary")
st.caption("A clean, dated recap of the day — copy it straight into your enterprise ELN.")

dates = distinct_entry_dates(conn)
default = dt.date.today()
chosen = st.date_input("Summary date", value=default)
if dates and chosen.isoformat() not in dates:
    st.caption("(No entries on this date — pick another, or log some on the Dashboard.)")

result = summary.build_daily_summary(conn, chosen)

tab_text, tab_md, tab_preview = st.tabs(["Plain text", "Markdown", "Preview"])

with tab_text:
    st.caption("Use the copy icon in the top-right of the box below.")
    st.code(result["text"], language=None)
    st.download_button(
        "⬇ Download .txt",
        result["text"],
        file_name=f"labnotebook_{chosen.isoformat()}.txt",
    )

with tab_md:
    st.code(result["markdown"], language="markdown")
    st.download_button(
        "⬇ Download .md",
        result["markdown"],
        file_name=f"labnotebook_{chosen.isoformat()}.md",
    )

with tab_preview:
    st.markdown(result["markdown"])
