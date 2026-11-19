@echo off
setlocal
set "PAWN_TOOL_ROOT=%~dp0"
set "PAWN_BUNDLED_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%PAWN_BUNDLED_PY%" (
  "%PAWN_BUNDLED_PY%" -X utf8 "%PAWN_TOOL_ROOT%gui.py" "%~1"
) else (
  py -3 -X utf8 "%PAWN_TOOL_ROOT%gui.py" "%~1"
)
if errorlevel 1 (
  echo.
  echo Install Python 3.10+ and run: py -3 -m pip install -r "%PAWN_TOOL_ROOT%requirements.txt"
  pause
)
