@echo off
REM ==============================================================================
REM Onítẹ́tẹ́ - Automated Daily Soccer Predictions & 5-Odds Banker Engine
REM Powered by Eighty-Two AI Engine
REM ==============================================================================

echo [i] Starting daily Onítẹ́tẹ́ scrape and 5-odds accumulator generation...
cd /d "%~dp0"

REM 1. Run full crawler and rebuild analytical relational datasets & 5-odds slips
call .\venv\Scripts\python.exe main.py

if %ERRORLEVEL% NEQ 0 (
    echo [!] Error occurred during scraping run.
    pause
    exit /b %ERRORLEVEL%
)

echo [OK] Onítẹ́tẹ́ predictions and 5-odds slips generated successfully.

REM 2. Launch interactive web dashboard on http://localhost:5000
echo [i] Launching Onítẹ́tẹ́ dashboard on http://localhost:5000...
start "" http://localhost:5000
call .\venv\Scripts\python.exe main.py --serve
