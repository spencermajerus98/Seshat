"""Protocols — browse and search your imported Word protocols."""

from __future__ import annotations

import streamlit as st

import ui_common as ui

st.set_page_config(page_title="Protocols · Seshat", page_icon="🪶", layout="wide")
conn = ui.get_conn()
ui.encryption_badge()

st.title("🧪 Protocols")

query = st.text_input("Search protocols", placeholder="title or text…").strip()

if query:
    like = f"%{query}%"
    rows = conn.execute(
        "SELECT * FROM protocols WHERE title LIKE ? OR body_text LIKE ? ORDER BY title",
        (like, like),
    ).fetchall()
else:
    rows = conn.execute("SELECT * FROM protocols ORDER BY title").fetchall()

if not rows:
    st.info("No protocols yet. Add one from the **Import** page (Word .docx).")
    st.stop()

for p in rows:
    with st.expander(f"📄 {p['title']}"):
        meta = []
        if p["source_filename"]:
            meta.append(f"file: `{p['source_filename']}`")
        if p["version"]:
            meta.append(f"version: {p['version']}")
        meta.append(f"imported: {p['imported_at'][:10]}")
        st.caption(" · ".join(meta))

        steps = conn.execute(
            "SELECT step_no, text FROM protocol_steps WHERE protocol_id=? ORDER BY step_no",
            (p["id"],),
        ).fetchall()
        if steps:
            st.markdown("**Steps**")
            for s in steps:
                st.markdown(f"{s['step_no']}. {s['text']}")
        with st.popover("Full text"):
            st.text(p["body_text"] or "")

        if st.button("🗑 Delete protocol", key=f"delp_{p['id']}"):
            conn.execute("DELETE FROM protocols WHERE id=?", (p["id"],))
            conn.commit()
            st.rerun()
