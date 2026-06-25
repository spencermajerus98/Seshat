"""Convert DOCX files to PDF for high-fidelity, in-browser viewing.

docx-preview (client-side) renders most Word documents well, but stumbles on
complex tables and exotic formatting. Converting to PDF with a real layout
engine and reusing the browser's native PDF viewer gives faithful output.

Two backends, tried in order:

* **LibreOffice** (``soffice --headless``) — cross-platform; preferred when
  installed because it needs no GUI session.
* **Microsoft Word** via COM automation (``win32com``) — Windows + Word only.

Both are optional. When neither is available, :func:`convert_docx_to_pdf`
returns ``None`` and callers fall back to the client-side docx-preview viewer.
Conversions are serialised: Word is a single COM server and LibreOffice dislikes
concurrent headless invocations on the same profile.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import threading
from typing import Optional

_convert_lock = threading.Lock()

# wdFormatPDF — the Word SaveAs constant for PDF export.
_WD_FORMAT_PDF = 17


def _libreoffice_exe() -> Optional[str]:
    """Locate a LibreOffice/soffice binary, if one is installed."""
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    candidates = [
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def _word_available() -> bool:
    """True if Microsoft Word can be driven via COM (Windows + Word installed)."""
    if os.name != "nt":
        return False
    try:
        import win32com.client  # noqa: F401  (import side-effect only)
    except Exception:
        return False
    return True


def converter_available() -> bool:
    """Whether any DOCX→PDF backend is usable on this machine."""
    return bool(_libreoffice_exe()) or _word_available()


def _convert_with_libreoffice(exe: str, src: str, outdir: str) -> Optional[str]:
    subprocess.run(
        [exe, "--headless", "--convert-to", "pdf", "--outdir", outdir, src],
        check=True,
        capture_output=True,
        timeout=120,
    )
    out = os.path.join(outdir, os.path.splitext(os.path.basename(src))[0] + ".pdf")
    return out if os.path.exists(out) else None


def _convert_with_word(src: str, outdir: str) -> Optional[str]:
    import pythoncom  # type: ignore
    import win32com.client  # type: ignore

    out = os.path.join(outdir, os.path.splitext(os.path.basename(src))[0] + ".pdf")
    pythoncom.CoInitialize()
    word = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        doc = word.Documents.Open(os.path.abspath(src), ReadOnly=True)
        try:
            doc.SaveAs(os.path.abspath(out), FileFormat=_WD_FORMAT_PDF)
        finally:
            doc.Close(False)
        return out if os.path.exists(out) else None
    finally:
        if word is not None:
            try:
                word.Quit()
            except Exception:
                pass
        pythoncom.CoUninitialize()


def convert_docx_to_pdf(data: bytes) -> Optional[bytes]:
    """Convert DOCX bytes to PDF bytes, or ``None`` if conversion isn't possible.

    Never raises: any backend failure (no converter, Word busy, malformed file)
    results in ``None`` so the caller can fall back gracefully.
    """
    exe = _libreoffice_exe()
    with _convert_lock:
        with tempfile.TemporaryDirectory(prefix="seshat_pdf_") as td:
            src = os.path.join(td, "document.docx")
            with open(src, "wb") as fh:
                fh.write(data)
            try:
                if exe:
                    out = _convert_with_libreoffice(exe, src, td)
                elif _word_available():
                    out = _convert_with_word(src, td)
                else:
                    return None
            except Exception:
                return None
            if not out or not os.path.exists(out):
                return None
            with open(out, "rb") as fh:
                return fh.read()
