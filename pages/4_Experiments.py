"""Experiments — browse, create/edit (modular, type-driven), calendar, and lists."""

from __future__ import annotations

import calendar as _cal
import datetime as dt
import os
import tempfile

import pandas as pd
import streamlit as st

import ui_common as ui
from core import exp_types, experiments as expm, importers, vocab
from core.exp_types import VALID_KINDS, slugify

st.set_page_config(page_title="Experiments · Seshat", page_icon="🪶", layout="wide")
conn = ui.get_conn()
ui.encryption_badge()

st.title("🧬 Experiments")

STATUSES = ["planned", "active", "done", "abandoned"]


def _protocol_options() -> dict[str, int]:
    rows = conn.execute("SELECT id, title FROM protocols ORDER BY title COLLATE NOCASE").fetchall()
    return {r["title"]: r["id"] for r in rows}


tab_browse, tab_edit, tab_cal, tab_lists = st.tabs(
    ["📚 Browse", "➕ Create / Edit", "🗓 Calendar", "⚙️ Types & Lists"]
)

# ══════════════════════════════════════════════════════════════════════════════
# Browse
# ══════════════════════════════════════════════════════════════════════════════
with tab_browse:
    exps = expm.list_experiments(conn)
    if not exps:
        st.info("No experiments yet. Create one in the **Create / Edit** tab, or import an Excel plan from **Import**.")
    for e in exps:
        tasks = expm.list_tasks(conn, e["id"])
        done = sum(1 for t in tasks if t["status"] == "done")
        sched = ""
        if e.get("start_date"):
            sched = e["start_date"]
            if e.get("end_date") and e["end_date"] != e["start_date"]:
                sched += f" → {e['end_date']}"
        title = f"🧬 {e['name']}"
        if e.get("type_name"):
            title += f"  ·  {e['type_name']}"
        title += f"  ·  {e['status']}"
        with st.expander(title):
            if sched:
                st.caption(f"🗓 {sched}")
            report = expm.build_experiment_report(conn, e["id"])
            st.markdown(report["markdown"])

            if tasks:
                st.markdown(f"**Tasks** ({done}/{len(tasks)} done)")
                st.dataframe(
                    [
                        {
                            "✓": "✅" if t["status"] == "done" else "⬜",
                            "Task": t["task_name"],
                            "Date": t["planned_date"],
                            "Sample": t["sample"],
                            "Reagent": t["reagent"],
                        }
                        for t in tasks
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

            with st.popover("📋 Copy for Labguru"):
                rt, rtxt = st.tabs(["Rich (select & copy)", "Plain text"])
                with rt:
                    st.caption("Select all below and copy → paste into Labguru with formatting.")
                    st.markdown(
                        f"<div style='border:1px solid #ddd;padding:12px;border-radius:6px'>{report['html']}</div>",
                        unsafe_allow_html=True,
                    )
                with rtxt:
                    st.code(report["text"], language=None)

            c1, c2 = st.columns(2)
            if c1.button("✏️ Edit", key=f"edit_{e['id']}"):
                st.session_state["edit_exp_id"] = e["id"]
                st.rerun()
            if c2.button("🗑 Delete", key=f"delx_{e['id']}"):
                expm.delete_experiment(conn, e["id"])
                st.session_state.pop("edit_exp_id", None)
                st.rerun()
        if st.session_state.get("edit_exp_id") == e["id"]:
            st.info("Now open the **Create / Edit** tab to edit this experiment.")

# ══════════════════════════════════════════════════════════════════════════════
# Create / Edit
# ══════════════════════════════════════════════════════════════════════════════
with tab_edit:
    all_exps = expm.list_experiments(conn)
    picker_opts = ["➕ New experiment"] + [f"{e['id']}: {e['name']}" for e in all_exps]
    edit_id = st.session_state.get("edit_exp_id")
    default_idx = 0
    if edit_id is not None:
        for i, e in enumerate(all_exps, start=1):
            if e["id"] == edit_id:
                default_idx = i
                break
    choice = st.selectbox("Editing", picker_opts, index=default_idx)

    if choice == "➕ New experiment":
        current = None
        st.session_state.pop("edit_exp_id", None)
    else:
        cid = int(choice.split(":", 1)[0])
        current = expm.get_experiment(conn, cid)

    types = exp_types.list_types(conn)
    type_names = [t["name"] for t in types]
    type_by_name = {t["name"]: t for t in types}

    # ── Type selection (with inline add) ──────────────────────────────────────
    cur_type_name = None
    if current and current.get("type_id"):
        ct = exp_types.get_type(conn, current["type_id"])
        cur_type_name = ct["name"] if ct else None
    type_choice = st.selectbox(
        "Experiment type",
        type_names + ["➕ Add new type…"],
        index=(type_names.index(cur_type_name) if cur_type_name in type_names else 0)
        if type_names
        else len(type_names),
    )
    if type_choice == "➕ Add new type…":
        nc1, nc2 = st.columns([0.7, 0.3])
        new_type_name = nc1.text_input("New type name", key="new_type_name")
        if nc2.button("Create type") and new_type_name.strip():
            tid = exp_types.create_type(conn, new_type_name.strip())
            st.success(f"Created type '{new_type_name}'. Customize its fields under Types & Lists.")
            st.rerun()
        st.stop()

    selected_type = type_by_name.get(type_choice)
    setup_current = (current or {}).get("setup", {})

    st.divider()
    name = st.text_input("Experiment name", value=(current["name"] if current else ""))

    # ── Dynamic setup-condition fields from the type template ─────────────────
    st.markdown("**Setup conditions**")
    setup_values: dict = {}
    proto_opts = _protocol_options()
    for field in (selected_type["fields"] if selected_type else []):
        key, label, kind = field["key"], field["label"], field.get("kind", "text")
        wkey = f"f_{(current['id'] if current else 'new')}_{key}"
        cur_val = setup_current.get(key)
        if kind == "multiselect":
            setup_values[key] = ui.vocab_multiselect(
                conn, field.get("vocab", key), label, default=cur_val or [], key=wkey
            )
        elif kind == "select":
            opts = vocab.list_terms(conn, field.get("vocab", key))
            idx = opts.index(cur_val) + 1 if cur_val in opts else 0
            sel = st.selectbox(label, ["—"] + opts, index=idx, key=wkey)
            setup_values[key] = None if sel == "—" else sel
        elif kind == "protocol":
            names = list(proto_opts)
            cur_title = next((t for t, pid in proto_opts.items() if pid == cur_val), None)
            idx = names.index(cur_title) + 1 if cur_title in names else 0
            sel = st.selectbox(label, ["—"] + names, index=idx, key=wkey)
            setup_values[key] = proto_opts.get(sel) if sel != "—" else None
        elif kind == "number":
            setup_values[key] = st.number_input(
                label, value=float(cur_val) if cur_val not in (None, "") else 0.0, key=wkey
            )
        elif kind == "date":
            setup_values[key] = str(st.date_input(label, key=wkey)) if st.checkbox(
                f"Set {label}", value=bool(cur_val), key=f"{wkey}_chk"
            ) else (cur_val or None)
        elif kind == "checkbox":
            setup_values[key] = st.checkbox(label, value=bool(cur_val), key=wkey)
        elif kind == "textarea":
            setup_values[key] = st.text_area(label, value=cur_val or "", key=wkey)
        else:  # text
            setup_values[key] = st.text_input(label, value=cur_val or "", key=wkey)

    # Protocol shortcut: upload a new protocol on the fly.
    with st.expander("📄 Upload a new protocol (then pick it above)"):
        up = st.file_uploader("Protocol file", type=["docx", "pdf", "txt", "md"], key="exp_proto_up")
        if up is not None and st.button("Import this protocol"):
            suffix = os.path.splitext(up.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(up.getbuffer())
                tmp_path = tmp.name
            try:
                ext = suffix.lower()
                parsed = (
                    importers.parse_word(tmp_path)
                    if ext == ".docx"
                    else importers.parse_pdf(tmp_path)
                    if ext == ".pdf"
                    else importers.parse_text(tmp_path)
                )
                parsed.source_filename = up.name
                importers.import_protocol(conn, parsed)
            finally:
                os.unlink(tmp_path)
            st.success(f"Imported protocol: {parsed.title}")
            st.rerun()

    st.divider()
    c1, c2, c3 = st.columns(3)
    start_default = (
        dt.date.fromisoformat(current["start_date"])
        if current and current.get("start_date")
        else dt.date.today()
    )
    start_date = c1.date_input("Start date", value=start_default)
    duration = c2.number_input(
        "Planned duration (days)",
        min_value=1,
        value=int(current["duration_days"]) if current and current.get("duration_days") else 1,
    )
    status = c3.selectbox(
        "Status",
        STATUSES,
        index=STATUSES.index(current["status"]) if current and current["status"] in STATUSES else 0,
    )
    description = st.text_area("Description", value=(current.get("description") or "") if current else "")

    end_preview = expm.compute_end_date(start_date.isoformat(), int(duration))
    st.caption(f"📅 Scheduled {start_date.isoformat()} → {end_preview} ({int(duration)} day(s))")

    if st.button("💾 Save experiment", type="primary"):
        if not name.strip():
            st.error("Experiment name is required.")
        else:
            type_id = selected_type["id"] if selected_type else None
            proto_id = next(
                (setup_values[f["key"]] for f in (selected_type["fields"] if selected_type else [])
                 if f.get("kind") == "protocol" and setup_values.get(f["key"])),
                None,
            )
            if current:
                expm.update_experiment(
                    conn, current["id"], name=name, type_id=type_id,
                    start_date=start_date.isoformat(), duration_days=int(duration),
                    protocol_id=proto_id, setup_values=setup_values,
                    description=description or None, status=status,
                )
                st.success(f"Updated '{name}'.")
            else:
                expm.create_experiment(
                    conn, name=name, type_id=type_id, start_date=start_date.isoformat(),
                    duration_days=int(duration), protocol_id=proto_id,
                    setup_values=setup_values, description=description or None, status=status,
                )
                st.success(f"Created '{name}'.")
            st.session_state.pop("edit_exp_id", None)
            st.rerun()

    # ── Tasks for the experiment being edited ─────────────────────────────────
    if current:
        st.divider()
        st.markdown("**Tasks / milestones**")
        for t in expm.list_tasks(conn, current["id"]):
            tc = st.columns([0.55, 0.2, 0.12, 0.13])
            tc[0].write(t["task_name"])
            tc[1].write(t["planned_date"] or "")
            if tc[2].button("✅" if t["status"] != "done" else "↩︎", key=f"tk_{t['id']}"):
                expm.set_task_status(conn, t["id"], "pending" if t["status"] == "done" else "done")
                st.rerun()
            if tc[3].button("🗑", key=f"tkd_{t['id']}"):
                conn.execute("DELETE FROM experiment_tasks WHERE id=?", (t["id"],))
                conn.commit()
                st.rerun()
        nt1, nt2, nt3 = st.columns([0.5, 0.3, 0.2])
        new_task = nt1.text_input("New task", key="new_task_name", label_visibility="collapsed", placeholder="New task…")
        new_task_date = nt2.date_input("Task date", key="new_task_date", label_visibility="collapsed")
        if nt3.button("➕ Add task") and new_task.strip():
            expm.add_task(conn, current["id"], new_task.strip(), planned_date=new_task_date.isoformat())
            st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# Calendar
# ══════════════════════════════════════════════════════════════════════════════
with tab_cal:
    sched = [e for e in expm.list_experiments(conn) if e.get("start_date")]
    if not sched:
        st.info("No scheduled experiments yet. Add a start date and duration in Create / Edit.")
    else:
        view = st.radio("View", ["Timeline (Gantt)", "Month grid"], horizontal=True)
        if view == "Timeline (Gantt)":
            import altair as alt

            df = pd.DataFrame(
                [
                    {
                        "Experiment": e["name"],
                        "Start": e["start_date"],
                        # +1 day so single-day bars are visible (exclusive end).
                        "End": (
                            dt.date.fromisoformat(e["end_date"] or e["start_date"])
                            + dt.timedelta(days=1)
                        ).isoformat(),
                        "Type": e.get("type_name") or "—",
                        "Status": e["status"],
                    }
                    for e in sched
                ]
            )
            chart = (
                alt.Chart(df)
                .mark_bar(cornerRadius=4, height=18)
                .encode(
                    x=alt.X("Start:T", title="Date"),
                    x2="End:T",
                    y=alt.Y("Experiment:N", sort="-x", title=None),
                    color=alt.Color("Type:N", legend=alt.Legend(title="Type")),
                    tooltip=["Experiment", "Type", "Status", "Start", "End"],
                )
                .properties(height=max(120, 40 * len(df)))
            )
            st.altair_chart(chart, use_container_width=True)
        else:
            today = dt.date.today()
            mc1, mc2 = st.columns(2)
            year = mc1.number_input("Year", value=today.year, min_value=2000, max_value=2100, step=1)
            month = mc2.selectbox("Month", list(range(1, 13)), index=today.month - 1,
                                  format_func=lambda m: _cal.month_name[m])
            st.markdown(f"### {_cal.month_name[month]} {int(year)}")
            spans = [
                (
                    e["name"],
                    dt.date.fromisoformat(e["start_date"]),
                    dt.date.fromisoformat(e["end_date"] or e["start_date"]),
                )
                for e in sched
            ]
            head = st.columns(7)
            for i, dname in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
                head[i].markdown(f"**{dname}**")
            for week in _cal.Calendar().monthdayscalendar(int(year), month):
                cols = st.columns(7)
                for i, day in enumerate(week):
                    if day == 0:
                        continue
                    d = dt.date(int(year), month, day)
                    names = [n for n, s, e in spans if s <= d <= e]
                    cell = f"**{day}**"
                    for n in names:
                        cell += f"<br><span style='font-size:0.78em;background:#e3efe8;border-radius:4px;padding:1px 4px'>{n}</span>"
                    cols[i].markdown(cell, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# Types & Lists
# ══════════════════════════════════════════════════════════════════════════════
with tab_lists:
    st.subheader("Experiment types & their fields")
    types = exp_types.list_types(conn)
    if types:
        tnames = [t["name"] for t in types]
        sel_name = st.selectbox("Type to edit", tnames)
        sel = next(t for t in types if t["name"] == sel_name)

        st.caption("Edit the modular setup-condition fields for this type. "
                   "`kind` controls the widget; `vocab` (for select/multiselect) names the dropdown list.")
        editor_df = pd.DataFrame(sel["fields"]) if sel["fields"] else pd.DataFrame(
            columns=["key", "label", "kind", "vocab"]
        )
        for col in ["key", "label", "kind", "vocab"]:
            if col not in editor_df.columns:
                editor_df[col] = None
        edited = st.data_editor(
            editor_df[["key", "label", "kind", "vocab"]],
            num_rows="dynamic",
            use_container_width=True,
            key=f"fields_{sel['id']}",
            column_config={
                "key": st.column_config.TextColumn("key (auto if blank)"),
                "label": st.column_config.TextColumn("label", required=True),
                "kind": st.column_config.SelectboxColumn("kind", options=VALID_KINDS),
                "vocab": st.column_config.SelectboxColumn("vocab", options=["", *vocab.CATEGORIES]),
            },
        )
        if st.button("💾 Save fields"):
            fields = []
            for _, row in edited.iterrows():
                label = (row.get("label") or "").strip()
                if not label:
                    continue
                key = (row.get("key") or "").strip() or slugify(label)
                kind = row.get("kind") or "text"
                f = {"key": key, "label": label, "kind": kind}
                if row.get("vocab"):
                    f["vocab"] = row["vocab"]
                fields.append(f)
            exp_types.update_type_fields(conn, sel["id"], fields)
            st.success("Saved field template.")
            st.rerun()

    st.markdown("**Add a new type**")
    ac1, ac2 = st.columns([0.7, 0.3])
    nt = ac1.text_input("New type name", key="lists_new_type", label_visibility="collapsed", placeholder="e.g. Lentiviral transduction")
    if ac2.button("Create type", key="lists_create_type") and nt.strip():
        exp_types.create_type(conn, nt.strip())
        st.rerun()

    st.divider()
    st.subheader("Controlled vocabulary lists")
    vcols = st.columns(len(vocab.CATEGORIES))
    for i, cat in enumerate(vocab.CATEGORIES):
        with vcols[i]:
            st.markdown(f"**{vocab.CATEGORY_LABELS[cat]}**")
            for term in vocab.list_terms(conn, cat):
                tc = st.columns([0.8, 0.2])
                tc[0].write(term)
                if tc[1].button("✕", key=f"delv_{cat}_{term}"):
                    vocab.delete_term(conn, cat, term)
                    st.rerun()
            add = st.text_input(f"Add {cat}", key=f"addv_{cat}", label_visibility="collapsed", placeholder=f"Add {cat}…")
            if st.button("➕", key=f"addvbtn_{cat}") and add.strip():
                vocab.add_term(conn, cat, add.strip())
                st.rerun()
