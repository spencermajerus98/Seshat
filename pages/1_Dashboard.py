"""Dashboard — today at a glance: quick-log what you do + pending tasks."""

from __future__ import annotations

import streamlit as st

import ui_common as ui
from core import notebook
from core.models import ENTRY_TYPES, ENTRY_TYPE_LABELS

st.set_page_config(page_title="Dashboard · Seshat", page_icon="🪶", layout="wide")
conn = ui.get_conn()
ui.encryption_badge()

st.title("📋 Dashboard")


def _experiment_options() -> dict[str, int]:
    rows = conn.execute("SELECT id, name FROM experiments ORDER BY name").fetchall()
    return {r["name"]: r["id"] for r in rows}


# ── Quick log ───────────────────────────────────────────────────────────────
st.subheader("Quick log")
st.caption("Logged with the exact date & time automatically — you never type a timestamp.")

exp_opts = _experiment_options()
with st.form("quicklog", clear_on_submit=True):
    text = st.text_area("What did you just do / observe?", height=110)
    c1, c2 = st.columns(2)
    entry_type = c1.selectbox(
        "Type", ENTRY_TYPES, format_func=lambda t: ENTRY_TYPE_LABELS[t]
    )
    exp_choice = c2.selectbox("Link to experiment (optional)", ["—"] + list(exp_opts))
    if st.form_submit_button("Log entry", type="primary"):
        try:
            notebook.add_entry(
                conn,
                text,
                entry_type=entry_type,
                experiment_id=exp_opts.get(exp_choice),
            )
            st.success("Logged.")
        except ValueError as exc:
            st.error(str(exc))

st.divider()

# ── Pending tasks ─────────────────────────────────────────────────────────────
st.subheader("Pending experiment tasks")
tasks = conn.execute(
    """
    SELECT t.id, t.task_name, t.planned_date, t.sample, t.reagent, x.name AS experiment_name
    FROM experiment_tasks t
    JOIN experiments x ON x.id = t.experiment_id
    WHERE t.status = 'pending'
    ORDER BY t.planned_date IS NULL, t.planned_date, t.id
    LIMIT 100
    """
).fetchall()

if not tasks:
    st.info("No pending tasks. Import an experiment plan from **Import** to populate this.")
else:
    for t in tasks:
        cols = st.columns([0.62, 0.18, 0.20])
        meta = " · ".join(
            x for x in [t["experiment_name"], t["planned_date"], t["sample"]] if x
        )
        cols[0].markdown(f"**{t['task_name']}**  \n<small>{meta}</small>", unsafe_allow_html=True)
        if cols[2].button("✅ Done", key=f"done_{t['id']}"):
            conn.execute("UPDATE experiment_tasks SET status='done' WHERE id=?", (t["id"],))
            conn.commit()
            notebook.add_entry(
                conn,
                f"Completed task: {t['task_name']}",
                entry_type="task_done",
                experiment_id=conn.execute(
                    "SELECT experiment_id FROM experiment_tasks WHERE id=?", (t["id"],)
                ).fetchone()[0],
            )
            st.rerun()

st.divider()

# ── Today's entries ──────────────────────────────────────────────────────────
import datetime as _dt

st.subheader("Today's entries")
today = notebook.list_entries(conn, on_date=_dt.date.today())
if not today:
    st.caption("Nothing logged yet today.")
for e in today:
    label = ENTRY_TYPE_LABELS.get(e["entry_type"], e["entry_type"])
    when = e["created_at"][11:16]
    src = " · 📲 phone" if e["source"] == "phone" else ""
    exp = f" · {e['experiment_name']}" if e["experiment_name"] else ""
    st.markdown(f"**{when}** · {label}{exp}{src}  \n{e['text']}")
