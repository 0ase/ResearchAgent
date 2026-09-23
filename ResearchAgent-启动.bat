@echo off
setlocal
title Research Agent - New

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
set "RESEARCH_API_PORT=8000"
set "RESEARCH_WEB_PORT=3000"

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_agent.ps1"
set "exit_code=%ERRORLEVEL%"

if not "%exit_code%"=="0" (
  echo.
  echo Research Agent failed to start. Exit code: %exit_code%
  pause
)

exit /b %exit_code%
