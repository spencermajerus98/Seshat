@echo off
REM ============================================================
REM  Seshat launcher (Windows)
REM  - Creates a local virtual environment on first run
REM  - Installs dependencies
REM  - Starts the app at http://127.0.0.1:8501 (localhost only)
REM ============================================================
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [Seshat] First run: creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [Seshat] ERROR: could not create venv. Is Python installed and on PATH?
        pause
        exit /b 1
    )
    call ".venv\Scripts\activate.bat"
    echo [Seshat] Installing dependencies...
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
) else (
    call ".venv\Scripts\activate.bat"
)

echo [Seshat] Starting... your browser will open at http://127.0.0.1:8501
python -m streamlit run app.py

pause
endlocal
