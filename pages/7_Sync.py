"""Sync — pull dictated notes from your phone inbox (via Syncthing)."""

from __future__ import annotations

import os

import streamlit as st

import ui_common as ui
from core import notebook, sync

st.set_page_config(page_title="Sync · Seshat", page_icon="🪶", layout="wide")
conn = ui.get_conn()
ui.encryption_badge()

st.title("📲 Phone Sync")

inbox = ui.inbox_dir()
os.makedirs(inbox, exist_ok=True)
pending = sync.count_pending(inbox)

c1, c2 = st.columns([0.7, 0.3])
c1.markdown(f"**Inbox folder:** `{inbox}`")
c1.caption("Keep this folder synced to your phone with Syncthing (peer-to-peer, no cloud).")
c2.metric("Notes waiting", pending)

if st.button("🔄 Scan inbox now", type="primary"):
    ingested = sync.scan_inbox(conn, inbox)
    if ingested:
        st.success(f"Ingested {len(ingested)} note(s).")
        for item in ingested:
            st.write(f"• `{item['file']}` → {item['created_at']}")
    else:
        st.info("No new notes found.")

st.divider()
st.subheader("Recently ingested from phone")
phone_entries = notebook.list_entries(conn, source="phone", limit=25)
if not phone_entries:
    st.caption("Nothing yet. Dictate a note on your phone and save it into the synced folder.")
for e in phone_entries:
    exp = f" · *{e['experiment_name']}*" if e["experiment_name"] else ""
    st.markdown(f"**{e['created_at'][:16].replace('T', ' ')}**{exp}  \n{e['text']}")

st.divider()
with st.expander("ℹ️ How phone dictation works"):
    st.markdown(
        """
        1. On your phone, dictate (Wispr Flow / built-in dictation) or type a note
           into a text file and save it into the Syncthing folder shared with this PC.
        2. Syncthing copies it here automatically (peer-to-peer, end-to-end encrypted).
        3. Seshat ingests new notes on launch and whenever you press **Scan inbox now**,
           timestamps them, and files the originals under `inbox/processed/`.

        **Optional markers** (each on its own line at the very top of a note):
        ```
        [ts: 2026-06-16T14:30]     explicit time (else the file's saved time is used)
        #exp: CRISPR knock-in       link the note to an experiment by name
        #type: observation          note / observation / result / deviation / task_done
        ```
        """
    )
