"""Experiments — browse imported Excel experiment plans and their tasks."""

from __future__ import annotations

import streamlit as st

import ui_common as ui

st.set_page_config(page_title="Experiments · Seshat", page_icon="🪶", layout="wide")
conn = ui.get_conn()
ui.encryption_badge()

st.title("🧬 Experiments")

rows = conn.execute("SELECT * FROM experiments ORDER BY imported_at DESC").fetchall()
if not rows:
    st.info("No experiments yet. Import an Excel plan from the **Import** page.")
    st.stop()

for x in rows:
    tasks = conn.execute(
        "SELECT * FROM experiment_tasks WHERE experiment_id=? ORDER BY planned_date IS NULL, planned_date, id",
        (x["id"],),
    ).fetchall()
    done = sum(1 for t in tasks if t["status"] == "done")
    with st.expander(f"🧬 {x['name']}  ·  {done}/{len(tasks)} tasks done"):
        if x["description"]:
            st.write(x["description"])
        st.caption(
            f"status: {x['status']} · "
            f"{'file: `' + x['source_filename'] + '` · ' if x['source_filename'] else ''}"
            f"imported: {x['imported_at'][:10]}"
        )

        if tasks:
            st.dataframe(
                [
                    {
                        "✓": "✅" if t["status"] == "done" else "⬜",
                        "Task": t["task_name"],
                        "Date": t["planned_date"],
                        "Sample": t["sample"],
                        "Reagent": t["reagent"],
                        "Notes": t["notes"],
                    }
                    for t in tasks
                ],
                use_container_width=True,
                hide_index=True,
            )

        if st.button("🗑 Delete experiment", key=f"delx_{x['id']}"):
            conn.execute("DELETE FROM experiments WHERE id=?", (x["id"],))
            conn.commit()
            st.rerun()
