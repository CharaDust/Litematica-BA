@echo off
setlocal EnableExtensions
set "ROOT=%~dp0.."
cd /d "%ROOT%" 2>nul
if errorlevel 1 (
  echo [dev-win-qt] Cannot cd to: %ROOT%
  goto :pause_fail
)

if exist "%ROOT%\.venv\Scripts\python.exe" goto :install_deps

set "PYEXE="
for /f "delims=" %%i in ('py -3.11 -c "import sys; print(sys.executable)" 2^>nul') do set "PYEXE=%%i"
if defined PYEXE goto :make_venv

where python >nul 2>&1
if errorlevel 1 (
  echo [dev-win-qt] Python not found. Install Python 3.11/3.10 and ensure py launcher or python is available.
  goto :pause_fail
)
set "PYEXE=python"

:make_venv
echo [dev-win-qt] First run: creating .venv ...
"%PYEXE%" -m venv "%ROOT%\.venv"
if errorlevel 1 (
  echo [dev-win-qt] python -m venv failed.
  goto :pause_fail
)

:install_deps
echo [dev-win-qt] Installing dependencies ...
"%ROOT%\.venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
  echo [dev-win-qt] pip upgrade failed.
  goto :pause_fail
)
"%ROOT%\.venv\Scripts\python.exe" -m pip install -r "%ROOT%\requirements.txt"
if errorlevel 1 (
  echo [dev-win-qt] pip install requirements failed.
  goto :pause_fail
)

echo [dev-win-qt] Starting LitematicaBA Qt ...
set "PYTHONPATH=%ROOT%\src"
"%ROOT%\.venv\Scripts\python.exe" -m litematicaba
if errorlevel 1 (
  echo.
  echo [dev-win-qt] App exited with error. See traceback above.
  goto :pause_fail
)

exit /b 0

:pause_fail
echo.
pause
exit /b 1
pause