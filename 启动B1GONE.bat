@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_project.ps1" %*
set "launch_result=%ERRORLEVEL%"
if not "%launch_result%"=="0" (
    echo.
    echo B1GONE could not start. Read the message above.
    pause
)
exit /b %launch_result%
