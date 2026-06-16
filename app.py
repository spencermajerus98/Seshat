"""Seshat — local experiment planner & automatic lab notebook.

This entry point is the unlock gate. Once unlocked it auto-scans the phone
inbox and hands off to the pages in ``pages/`` via Streamlit's multipage nav.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

import ui_common as ui
from core import db, sync

st.set_page_config(page_title="Seshat", page_icon="🪶", layout="wide")


def _unlock_screen() -> None:
    st.title("🪶 Seshat")
    st.caption("Your local, private experiment planner & automatic lab notebook.")

    ui.encryption_badge()

    existing = __import__("os").path.exists(ui.db_path())
    if existing:
        st.subheader("Unlock your notebook")
        prompt = "Enter your passphrase"
    else:
        st.subheader("Create your notebook")
        st.info(
            "No notebook found yet. Choose a strong passphrase — it encrypts your "
            "data and **cannot be recovered** if lost."
        )
        prompt = "Choose a passphrase"

    with st.form("unlock"):
        passphrase = st.text_input(prompt, type="password")
        if not existing:
            confirm = st.text_input("Confirm passphrase", type="password")
        else:
            confirm = passphrase
        submitted = st.form_submit_button("Open notebook", type="primary")

    if submitted:
        if not passphrase:
            st.error("Please enter a passphrase.")
            return
        if passphrase != confirm:
            st.error("Passphrases do not match.")
            return
        try:
            conn = db.connect(ui.db_path(), passphrase)
        except db.BadPassphrase:
            st.error("Incorrect passphrase.")
            return
        except Exception as exc:  # noqa: BLE001
            st.error(f"Could not open the notebook: {exc}")
            return

        st.session_state["conn"] = conn
        # Pull in any phone notes waiting in the synced inbox.
        try:
            ingested = sync.scan_inbox(conn, ui.inbox_dir())
            if ingested:
                st.session_state["last_sync_count"] = len(ingested)
        except Exception:  # noqa: BLE001 - never block unlock on sync issues
            pass
        st.rerun()


def _home_screen() -> None:
    conn = st.session_state["conn"]
    ui.encryption_badge()
    if st.sidebar.button("🔒 Lock notebook"):
        ui.lock()
        st.rerun()

    st.title("🪶 Seshat")
    st.caption("Your local, private experiment planner & automatic lab notebook.")

    n = st.session_state.pop("last_sync_count", 0)
    if n:
        st.success(f"📥 Ingested {n} note(s) from your phone inbox.")

    today = __import__("datetime").date.today()
    from core.notebook import list_entries

    today_entries = list_entries(conn, on_date=today)
    pending = sync.count_pending(ui.inbox_dir())

    c1, c2, c3 = st.columns(3)
    c1.metric("Entries today", len(today_entries))
    c2.metric("Protocols", conn.execute("SELECT count(*) FROM protocols").fetchone()[0])
    c3.metric("Experiments", conn.execute("SELECT count(*) FROM experiments").fetchone()[0])
    if pending:
        st.info(f"📲 {pending} phone note(s) waiting — open **Sync** to ingest them.")

    st.divider()
    st.markdown(
        """
        ### Where to go
        - **Dashboard** — see today's planned tasks and quick-log what you do.
        - **Notebook** — the full, automatically timestamped record.
        - **Protocols / Experiments** — your imported Word & Excel content.
        - **Import** — bring in `.docx` protocols and `.xlsx` plans.
        - **Sync** — pull dictated notes from your phone inbox.
        - **Daily Summary** — generate the copy-paste text for your real ELN.
        - **Settings** — paths, passphrase, backup.
        """
    )


def main() -> None:
    if ui.is_unlocked():
        _home_screen()
    else:
        _unlock_screen()


if __name__ == "__main__":
    main()
