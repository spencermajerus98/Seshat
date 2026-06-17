# 🪶 Seshat

> Named for **Seshat**, the ancient Egyptian goddess of writing, measurement and record-keeping.

A **local, private** experiment planner and **automatic lab notebook** for bench scientists.
Seshat brings your Excel experiment plans and Word protocols into one place, logs everything
you do with an automatic date & time stamp, lets you dictate notes from your phone, and
generates a clean **copy-paste daily summary** for your real (enterprise) electronic lab
notebook (ELN).

It runs entirely on your machine. There are **no cloud services and no outbound network
calls** — your data never leaves your computer.

---

## What it does

- **Automatic timestamped notebook** — every action is recorded with the exact date & time.
  You never type a timestamp.
- **Folder browser** — Seshat reads your own folders: navigate your drives, save favorites, and
  pull `.docx` / `.pdf` / `.txt`/`.md` protocols and `.xlsx` experiment plans straight into the
  database (or upload them).
- **Protocol library** — imported protocols are parsed into title + steps and made searchable.
- **Modular experiments** — create and edit experiments in-app. Define reusable **experiment
  types**, each with **customizable setup-condition fields** (vectors, cells, reagents/media as
  multi-select dropdowns you extend inline; protocol link; planned duration; and any custom
  fields you add). Track tasks/milestones to completion.
- **Calendar** — view your schedule as a **Gantt timeline** or a **month grid**; experiment
  durations are mapped across the dates.
- **Phone dictation sync** — dictate (Wispr Flow / built-in dictation) or type notes on your
  phone; they sync to the PC via Syncthing and are ingested as timestamped entries.
- **Daily summary for Labguru** — one click produces a tidy, dated recap. A **Rich (Labguru)**
  view lets you select-and-copy formatted text (headings, bullets) straight into Labguru's
  editor, plus plain-text and Markdown fallbacks. Each experiment also has a **Copy for Labguru**
  setup report.

---

## Quick start (Windows)

1. Install [Python 3.11+](https://www.python.org/downloads/) (check **"Add Python to PATH"**).
2. Download/clone this repo to a folder on your machine.
3. Double-click **`run_seshat.bat`**. On first run it creates a local virtual environment,
   installs dependencies, and launches the app.
4. Your browser opens at **http://127.0.0.1:8501**. Choose a passphrase to create your notebook.

### Manual start (any OS)

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
streamlit run app.py
```

---

## Phone dictation via Syncthing (no cloud)

[Syncthing](https://syncthing.net/) syncs a folder **directly** between your phone and PC,
peer-to-peer and end-to-end encrypted — no account, no cloud server.

1. Install Syncthing on the **PC** and the **phone** app (e.g. *Syncthing-Fork* on Android,
   *Möbius Sync* on iOS).
2. Share a folder between the two devices and point it at Seshat's **inbox** folder
   (default: the `inbox/` folder in this project; configurable in **Settings**).
3. On your phone, dictate or type a note into a `.txt` / `.md` file saved in that folder.
4. Syncthing copies it to the PC; Seshat ingests it on launch or when you press
   **Scan inbox now** on the **Sync** page, then files the original under `inbox/processed/`.

For the strictest environments, set Syncthing to **LAN-only** (disable global discovery and
relaying) so traffic never leaves your local network.

**Optional markers** — put any of these on their own line at the top of a note:

```
[ts: 2026-06-16T14:30]     explicit time (otherwise the file's saved time is used)
#exp: CRISPR knock-in       link the note to an experiment by name
#type: observation          note / observation / result / deviation / task_done
```

---

## Security model

- **Encrypted at rest.** With the `sqlcipher3-wheels` package installed (it's in
  `requirements.txt`), the database is a fully encrypted SQLCipher file. Your passphrase is the
  key; it is held only in memory while the app runs and is **never written to disk**. The unlock
  screen and badge tell you whether encryption is active.
- **Local only.** Streamlit is bound to `127.0.0.1`, telemetry is disabled, and the code makes
  no outbound network calls.
- **Nothing sensitive in git.** `.gitignore` excludes the database, the inbox, and imported
  `.docx`/`.xlsx` files. Only the application code is tracked.

### Honest caveats — please read

- **Software encryption is bounded by host security.** Seshat encrypts the database file, but it
  can't protect against a compromised machine. Use **full-disk encryption (BitLocker)** and a
  locked OS account, and **confirm with your employer / IT** that running a local app like this
  (and Syncthing) is permitted for your data.
- **There is no passphrase recovery.** If you lose the passphrase, the encrypted data cannot be
  recovered. Keep a secure backup of the passphrase.
- **Phone dictation tools are outside Seshat's boundary.** Wispr Flow, Gboard, or iOS dictation
  convert your speech to text under *their own* privacy policies before the text ever reaches the
  synced folder. Seshat only ever sees the resulting text. Choose dictation tools whose data
  handling meets your lab's requirements (e.g. on-device dictation, or a zero-retention policy).

---

## Project layout

```
app.py            Unlock gate + home; auto-scans the phone inbox
ui_common.py      Shared Streamlit helpers (state, paths, connection)
pages/            Dashboard, Notebook, Protocols, Experiments, Daily Summary, Import, Sync, Settings
core/             db, crypto, importers, sync, summary, notebook, models  (pure Python, testable)
tests/            pytest suite
.streamlit/       localhost-only, telemetry-off config
```

## Running the tests

```bash
pip install pytest python-docx openpyxl pandas
pytest -q
```

---

*Seshat is a personal productivity tool, not a validated GxP/21 CFR Part 11 system. Your
official record of truth remains your institution's electronic lab notebook.*
