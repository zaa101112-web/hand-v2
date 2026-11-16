@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" run.py --mode DEV_SIMULATED
if errorlevel 1 pause
