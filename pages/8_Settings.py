"""Settings — passphrase, folder paths, and local backup/export."""

from __future__ import annotations

import os

import streamlit as st

import ui_common as ui
from core import crypto, db

st.set_page_config(page_title="Settings · Seshat", page_icon="🪶", layout="wide")
conn = ui.get_conn()
ui.encryption_badge()

st.title("⚙️ Settings")

# ── Folder paths ──────────────────────────────────────────────────────────────
st.subheader("Folders")
cfg = ui.load_config()
with st.form("paths"):
    new_db = st.text_input("Database file", value=ui.db_path())
    new_inbox = st.text_input("Phone inbox folder (Syncthing)", value=ui.inbox_dir())
    if st.form_submit_button("Save paths"):
        cfg["db_path"] = new_db
        cfg["inbox_dir"] = new_inbox
        ui.save_config(cfg)
        st.success("Saved. Changing the database file takes effect after you lock & reopen.")

st.divider()

# ── Change passphrase ─────────────────────────────────────────────────────────
st.subheader("Change passphrase")
if not db.ENCRYPTION_AVAILABLE:
    st.warning("Encryption backend not installed — the passphrase guards access but the file is not encrypted.")
with st.form("passphrase"):
    current = st.text_input("Current passphrase", type="password")
    new_pw = st.text_input("New passphrase", type="password")
    confirm = st.text_input("Confirm new passphrase", type="password")
    if st.form_submit_button("Update passphrase"):
        salt = db.get_meta(conn, "pass_salt")
        verifier = db.get_meta(conn, "pass_verifier")
        if not (salt and verifier and crypto.verify(current, salt, verifier)):
            st.error("Current passphrase is incorrect.")
        elif not new_pw:
            st.error("New passphrase cannot be empty.")
        elif new_pw != confirm:
            st.error("New passphrases do not match.")
        else:
            db.change_passphrase(conn, ui.db_path(), new_pw)
            st.success("Passphrase updated.")

st.divider()

# ── Backup & export ───────────────────────────────────────────────────────────
st.subheader("Backup & export")
dbp = ui.db_path()
if os.path.exists(dbp):
    with open(dbp, "rb") as fh:
        data = fh.read()
    enc = "encrypted " if db.ENCRYPTION_AVAILABLE else ""
    st.download_button(
        f"⬇ Download {enc}database backup",
        data,
        file_name=os.path.basename(dbp),
        mime="application/octet-stream",
    )
    st.caption(
        "Store backups somewhere that meets your lab's security policy. "
        + ("The file is encrypted at rest." if db.ENCRYPTION_AVAILABLE else "This file is NOT encrypted.")
    )

from core.notebook import list_entries

all_entries = list_entries(conn, limit=100000)
md_lines = ["# Seshat notebook export\n"]
for e in reversed(all_entries):
    exp = f" [{e['experiment_name']}]" if e["experiment_name"] else ""
    md_lines.append(f"- **{e['created_at']}** ({e['entry_type']}{exp}, {e['source']}): {e['text']}")
st.download_button(
    "⬇ Export all entries to Markdown",
    "\n".join(md_lines),
    file_name="seshat_notebook_export.md",
)
