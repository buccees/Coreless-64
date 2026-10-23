@echo off
setlocal
cd /d "%~dp0"
title CORELESS-64 Operator Startup
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 scripts\coreless-start.py
) else (
  python scripts\coreless-start.py
)
if errorlevel 1 (
  echo.
  echo Coreless startup exited with an error. Read the message above.
  pause
)
endlocal
