@echo off
cd /d "%~dp0"
if exist "dist\HAND-v2-M08-20261117-r2\HAND-v2.exe" (
  if exist "%LOCALAPPDATA%\HAND-v2\user.json" (
    start "" "dist\HAND-v2-M08-20261117-r2\HAND-v2.exe"
  ) else (
    start "" "dist\HAND-v2-M08-20261117-r2\HAND-v2.exe" --camera 1
  )
) else (
  start "" ".venv\Scripts\pythonw.exe" run.py --mode WINDOWS_REAL --camera 1
)
