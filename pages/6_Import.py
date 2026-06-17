"""Import — browse local folders or upload files into the protocol/experiment DB."""

from __future__ import annotations

import os
import tempfile

import streamlit as st

import ui_common as ui
from core import files, importers

st.set_page_config(page_title="Import · Seshat", page_icon="🪶", layout="wide")
conn = ui.get_conn()
ui.encryption_badge()

st.title("📥 Import")
st.caption("Seshat reads your own folders — browse and pull files straight into the notebook, or upload them.")


def _save_temp(uploaded) -> str:
    suffix = os.path.splitext(uploaded.name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.getbuffer())
        return tmp.name


def _excel_import_ui(path: str, source_name: str, keyprefix: str) -> None:
    """Shared Excel → experiment mapping UI (used by browse + upload)."""
    preview = importers.parse_excel(path)
    sheet = st.selectbox("Sheet", preview["sheet_names"], key=f"{keyprefix}_sheet")
    if sheet != preview["sheet"]:
        preview = importers.parse_excel(path, sheet_name=sheet)

    st.markdown("**Preview**")
    st.dataframe(preview["rows"][:15], use_container_width=True, hide_index=True)

    name = st.text_input("Experiment name", value=os.path.splitext(source_name)[0], key=f"{keyprefix}_name")
    description = st.text_area("Description (optional)", height=70, key=f"{keyprefix}_desc")

    st.markdown("**Map spreadsheet columns → task fields**")
    cols = ["(none)"] + preview["columns"]
    mapping = {}
    mc = st.columns(len(importers.TASK_FIELDS))
    for i, field in enumerate(importers.TASK_FIELDS):
        guess = next((c for c in preview["columns"] if field.split("_")[0] in c.lower()), None)
        idx = cols.index(guess) if guess in cols else 0
        choice = mc[i].selectbox(field, cols, index=idx, key=f"{keyprefix}_map_{field}")
        mapping[field] = None if choice == "(none)" else choice

    if st.button("Import experiment", type="primary", key=f"{keyprefix}_import"):
        xid = importers.import_experiment(
            conn, name, preview["rows"], mapping,
            description=description or None, source_filename=source_name,
        )
        st.success(f"Imported experiment #{xid}: {name} ({len(preview['rows'])} task rows)")


def _protocol_preview_import(parsed, source_name: str, keyprefix: str) -> None:
    parsed.source_filename = source_name
    title = st.text_input("Title", value=parsed.title, key=f"{keyprefix}_title")
    version = st.text_input("Version (optional)", key=f"{keyprefix}_ver")
    tags = st.text_input("Tags (optional, comma-separated)", key=f"{keyprefix}_tags")
    st.markdown(f"**Detected {len(parsed.steps)} step(s):**")
    for i, s in enumerate(parsed.steps[:20], 1):
        st.markdown(f"{i}. {s}")
    if len(parsed.steps) > 20:
        st.caption(f"…and {len(parsed.steps) - 20} more")
    if st.button("Import protocol", type="primary", key=f"{keyprefix}_import"):
        parsed.title = title
        parsed.version = version or None
        pid = importers.import_protocol(conn, parsed, tags=tags or None)
        st.success(f"Imported protocol #{pid}: {title}")


tab_browse, tab_proto, tab_excel = st.tabs(
    ["📁 Browse folders", "🧪 Upload protocol", "🧬 Upload experiment plan"]
)

# ── Folder browser ────────────────────────────────────────────────────────────
with tab_browse:
    roots = files.default_roots()
    favs = ui.favorites()

    if "browse_path" not in st.session_state:
        st.session_state["browse_path"] = roots[0][1] if roots else os.path.expanduser("~")

    st.markdown("**Quick locations**")
    quick = (favs and [("★ " + os.path.basename(p.rstrip("/\\")) or p, p) for p in favs] or []) + roots
    qcols = st.columns(min(6, max(1, len(quick))))
    for i, (label, path) in enumerate(quick):
        if qcols[i % len(qcols)].button(label, key=f"quick_{i}"):
            st.session_state["browse_path"] = path
            st.rerun()

    cur = st.session_state["browse_path"]
    listing = files.list_dir(cur)

    nav = st.columns([0.15, 0.65, 0.2])
    if listing["parent"] and nav[0].button("⬆️ Up"):
        st.session_state["browse_path"] = listing["parent"]
        st.rerun()
    nav[1].text_input("Path", value=listing["path"], key="browse_path_box")
    if nav[2].button("Go"):
        st.session_state["browse_path"] = st.session_state["browse_path_box"]
        st.rerun()

    fc1, fc2 = st.columns(2)
    if fc1.button("⭐ Save to favorites"):
        ui.add_favorite(listing["path"])
        st.rerun()
    if favs and fc2.button("Remove from favorites"):
        ui.remove_favorite(listing["path"])
        st.rerun()

    st.divider()
    st.markdown("**Folders**")
    dcols = st.columns(4)
    for i, (dname, dpath) in enumerate(listing["dirs"]):
        if dcols[i % 4].button(f"📁 {dname}", key=f"dir_{i}"):
            st.session_state["browse_path"] = dpath
            st.rerun()
    if not listing["dirs"]:
        st.caption("No subfolders.")

    st.markdown("**Importable files**")
    if not listing["files"]:
        st.caption("No .docx / .pdf / .txt / .md / .xlsx files here.")
    for i, f in enumerate(listing["files"]):
        row = st.columns([0.7, 0.3])
        icon = "🧬" if f["is_experiment"] else "🧪"
        row[0].write(f"{icon} {f['name']}  ·  {f['size'] // 1024} KB")
        if f["is_experiment"]:
            if row[1].button("Open mapping ▶", key=f"file_{i}"):
                st.session_state["browse_excel"] = f["path"]
                st.session_state["browse_excel_name"] = f["name"]
        else:
            if row[1].button("Import protocol", key=f"file_{i}"):
                try:
                    pid = files.import_protocol_file(conn, f["path"])
                    st.success(f"Imported protocol #{pid}: {f['name']}")
                except Exception as exc:  # noqa: BLE001
                    st.error(f"Could not import {f['name']}: {exc}")

    if st.session_state.get("browse_excel"):
        st.divider()
        st.markdown(f"### Map experiment: `{st.session_state['browse_excel_name']}`")
        _excel_import_ui(
            st.session_state["browse_excel"],
            st.session_state["browse_excel_name"],
            keyprefix="browse_xl",
        )

# ── Upload protocol (Word / PDF / Text) ───────────────────────────────────────
with tab_proto:
    up = st.file_uploader("Upload a protocol", type=["docx", "pdf", "txt", "md"], key="proto_up")
    if up is not None:
        path = _save_temp(up)
        try:
            ext = os.path.splitext(up.name)[1].lower()
            parsed = (
                importers.parse_word(path)
                if ext == ".docx"
                else importers.parse_pdf(path)
                if ext == ".pdf"
                else importers.parse_text(path)
            )
        finally:
            os.unlink(path)
        _protocol_preview_import(parsed, up.name, keyprefix="up_proto")

# ── Upload experiment plan (Excel) ─────────────────────────────────────────────
with tab_excel:
    up = st.file_uploader("Upload an .xlsx experiment plan", type=["xlsx"], key="xlsx_up")
    if up is not None:
        path = _save_temp(up)
        try:
            _excel_import_ui(path, up.name, keyprefix="up_xl")
        finally:
            os.unlink(path)
