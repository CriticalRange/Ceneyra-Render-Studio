@echo off
chcp 65001 >nul
setlocal
title CENEYRA Render Studio - Live Console

set "STUDIO_DIR=%~dp0"
set "UI_SCRIPT=%STUDIO_DIR%ceneyra_gui.py"

REM Detect 3ds Max Python with built-in PySide6
set "PY_EXE="
if exist "C:\Program Files\Autodesk\3ds Max 2027\Python\python.exe" (
    set "PY_EXE=C:\Program Files\Autodesk\3ds Max 2027\Python\python.exe"
) else if exist "C:\Program Files\Autodesk\3ds Max 2026\Python\python.exe" (
    set "PY_EXE=C:\Program Files\Autodesk\3ds Max 2026\Python\python.exe"
) else if exist "C:\Program Files\Autodesk\3ds Max 2025\Python\python.exe" (
    set "PY_EXE=C:\Program Files\Autodesk\3ds Max 2025\Python\python.exe"
) else if exist "C:\Program Files\Autodesk\3ds Max 2024\Python\python.exe" (
    set "PY_EXE=C:\Program Files\Autodesk\3ds Max 2024\Python\python.exe"
) else (
    set "PY_EXE=python"
)

echo =======================================================================
echo   CENEYRA RENDER STUDIO - CANLI KONSOL GUNLUGU
echo   Python  : %PY_EXE%
echo   Script  : %UI_SCRIPT%
echo =======================================================================
echo.

"%PY_EXE%" "%UI_SCRIPT%" %*

echo.
echo =======================================================================
echo   Ceneyra Render Studio kapandi.
echo =======================================================================
pause
endlocal
exit /b 0
