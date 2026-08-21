@echo off
setlocal
title Research Agent

set "repo_root=%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%repo_root%scripts\start_agent.ps1"
set "exit_code=%ERRORLEVEL%"

if not "%exit_code%"=="0" (
  echo.
  echo Research Agent failed to start. Exit code: %exit_code%
  pause
)

exit /b %exit_code%
