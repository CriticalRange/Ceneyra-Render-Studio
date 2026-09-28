@echo off
set "PATH=%SystemRoot%\System32;%SystemRoot%;%PATH%"
chcp 65001 >nul
title CENEYRA | Render Stüdyosu

set "STUDIO_DIR=%~dp0"
call "%STUDIO_DIR%CENEYRA_STUDIO.bat" %*
exit /b 0