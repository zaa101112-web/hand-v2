@echo off
cd /d "%~dp0"
if exist "dist\HAND-v2-M04-20261116-231932\HAND-v2.exe" (
  start "" "dist\HAND-v2-M04-20261116-231932\HAND-v2.exe" --camera 1
) else (
  start "" ".venv\Scripts\pythonw.exe" run.py --mode WINDOWS_REAL --camera 1
)
