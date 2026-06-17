@echo off
REM ============================================================
REM  Seshat launcher (Windows)
REM  - Creates a local virtual environment on first run
REM  - Installs/repairs dependencies if anything is missing
REM  - Starts the app at http://127.0.0.1:8501 (localhost only)
REM ============================================================
setlocal
cd /d "%~dp0"

REM --- Ensure a virtual environment exists -------------------------------
if not exist ".venv\Scripts\python.exe" (
    echo [Seshat] First run: creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [Seshat] ERROR: could not create venv. Is Python installed and on PATH?
        pause
        exit /b 1
    )
)
call ".venv\Scripts\activate.bat"

REM --- Ensure dependencies are actually installed ------------------------
REM Don't trust that the venv folder exists; verify Streamlit imports. This
REM self-heals a venv left half-installed by an earlier failed install.
python -c "import streamlit, pypdf, altair" >NUL 2>&1
if errorlevel 1 (
    echo [Seshat] Installing dependencies ^(this can take a few minutes^)...
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [Seshat] ERROR: dependency installation failed. See the messages above.
        echo          Check your internet connection and that Python 3.11+ is installed.
        pause
        exit /b 1
    )
)

REM --- Final sanity check ------------------------------------------------
python -c "import streamlit, pypdf, altair" >NUL 2>&1
if errorlevel 1 (
    echo [Seshat] ERROR: Streamlit still isn't installed after setup. Cannot start.
    pause
    exit /b 1
)

echo [Seshat] Starting... your browser will open at http://127.0.0.1:8501
python -m streamlit run app.py

pause
endlocal
