"""Import — bring in Word (.docx) protocols and Excel (.xlsx) experiment plans."""

from __future__ import annotations

import os
import tempfile

import streamlit as st

import ui_common as ui
from core import importers

st.set_page_config(page_title="Import · Seshat", page_icon="🪶", layout="wide")
conn = ui.get_conn()
ui.encryption_badge()

st.title("📥 Import")
st.caption("Keep authoring in Word/Excel — import here to view and link them in your notebook.")


def _save_temp(uploaded) -> str:
    suffix = os.path.splitext(uploaded.name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.getbuffer())
        return tmp.name


tab_word, tab_excel = st.tabs(["🧪 Protocol (Word)", "🧬 Experiment plan (Excel)"])

# ── Word protocol ─────────────────────────────────────────────────────────────
with tab_word:
    up = st.file_uploader("Upload a .docx protocol", type=["docx"], key="docx")
    if up is not None:
        path = _save_temp(up)
        try:
            parsed = importers.parse_word(path)
        finally:
            os.unlink(path)
        parsed.source_filename = up.name

        title = st.text_input("Title", value=parsed.title)
        version = st.text_input("Version (optional)")
        tags = st.text_input("Tags (optional, comma-separated)")
        st.markdown(f"**Detected {len(parsed.steps)} step(s):**")
        for i, s in enumerate(parsed.steps[:20], 1):
            st.markdown(f"{i}. {s}")
        if len(parsed.steps) > 20:
            st.caption(f"…and {len(parsed.steps) - 20} more")

        if st.button("Import protocol", type="primary"):
            parsed.title = title
            parsed.version = version or None
            pid = importers.import_protocol(conn, parsed, tags=tags or None)
            st.success(f"Imported protocol #{pid}: {title}")

# ── Excel experiment plan ─────────────────────────────────────────────────────
with tab_excel:
    up = st.file_uploader("Upload an .xlsx experiment plan", type=["xlsx"], key="xlsx")
    if up is not None:
        path = _save_temp(up)
        try:
            # Peek at sheet names first.
            preview = importers.parse_excel(path)
            sheet = st.selectbox("Sheet", preview["sheet_names"])
            if sheet != preview["sheet"]:
                preview = importers.parse_excel(path, sheet_name=sheet)

            st.markdown("**Preview**")
            st.dataframe(preview["rows"][:15], use_container_width=True, hide_index=True)

            name = st.text_input("Experiment name", value=os.path.splitext(up.name)[0])
            description = st.text_area("Description (optional)", height=70)

            st.markdown("**Map spreadsheet columns → task fields**")
            cols = ["(none)"] + preview["columns"]
            mapping = {}
            mc = st.columns(len(importers.TASK_FIELDS))
            for i, field in enumerate(importers.TASK_FIELDS):
                # Pre-select a column whose name loosely matches the field.
                guess = next(
                    (c for c in preview["columns"] if field.split("_")[0] in c.lower()),
                    None,
                )
                idx = cols.index(guess) if guess in cols else 0
                choice = mc[i].selectbox(field, cols, index=idx, key=f"map_{field}")
                mapping[field] = None if choice == "(none)" else choice

            if st.button("Import experiment", type="primary"):
                xid = importers.import_experiment(
                    conn,
                    name,
                    preview["rows"],
                    mapping,
                    description=description or None,
                    source_filename=up.name,
                )
                st.success(
                    f"Imported experiment #{xid}: {name} ({len(preview['rows'])} task rows)"
                )
        finally:
            os.unlink(path)
