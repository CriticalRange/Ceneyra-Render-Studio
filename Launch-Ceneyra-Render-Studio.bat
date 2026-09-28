@echo off
setlocal
set "MAX_EXE=%ProgramFiles%\Autodesk\3ds Max 2024\3dsmax.exe"
set "SCRIPT=%~dp0Ceneyra_Render_Studio.ms"

if not exist "%MAX_EXE%" (
  echo 3ds Max 2024 was not found: "%MAX_EXE%"
  pause
  exit /b 1
)
if not exist "%SCRIPT%" (
  echo Ceneyra Render Studio script was not found: "%SCRIPT%"
  pause
  exit /b 1
)

set "SCENE="
set /p "SCENE=Optional scene file to open first (leave blank to start without a scene): "
if not "%SCENE%"=="" (
  if not exist "%SCENE%" (
    echo Scene file was not found: "%SCENE%"
    pause
    exit /b 1
  )
  start "Ceneyra Render Studio" "%MAX_EXE%" -q -U MAXScript "%SCRIPT%" "%SCENE%"
) else (
  start "Ceneyra Render Studio" "%MAX_EXE%" -q -U MAXScript "%SCRIPT%"
)