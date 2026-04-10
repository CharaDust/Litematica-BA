@echo off
setlocal EnableExtensions
pushd "%~dp0.."
if errorlevel 1 (
  echo [dev-win] ERROR: cannot change to project directory.
  pause
  exit /b 1
)

REM Optional: set PYTHON=full\path\python.exe
REM On Windows, amulet-nbt 2.1.3 has wheels for 3.9-3.11 only (no cp312 wheel). Prefer Python 3.11.
REM Optional: set ALLOW_PY314=1 to skip the Python 3.14 block (you still need MSVC to build deps.)
REM If you switch Python version, delete the .venv folder once.
if defined PYTHON (
  set "PYEXE=%PYTHON%"
  goto :pyexe_done
)

set "PYEXE="
for /f "delims=" %%i in ('py -3.11 -c "import sys; print(sys.executable)" 2^>nul') do set "PYEXE=%%i"
if defined PYEXE goto :pyexe_done

set "PYEXE="
for /f "delims=" %%i in ('py -3.10 -c "import sys; print(sys.executable)" 2^>nul') do set "PYEXE=%%i"
if defined PYEXE goto :pyexe_done

set "PYEXE="
for /f "delims=" %%i in ('py -3.12 -c "import sys; print(sys.executable)" 2^>nul') do set "PYEXE=%%i"
if defined PYEXE goto :pyexe_done

set "PYEXE="
for /f "delims=" %%i in ('py -3.13 -c "import sys; print(sys.executable)" 2^>nul') do set "PYEXE=%%i"
if defined PYEXE goto :pyexe_done

set "PYEXE=python"

:pyexe_done
"%PYEXE%" -c "import sys" 2>nul
if errorlevel 1 (
  echo [dev-win] ERROR: Python not found. Install Python 3.11 x64 from https://www.python.org/downloads/
  echo           Enable "py launcher", then delete .venv and run again. Or set PYTHON=path\to\python.exe
  goto :error
)

if exist ".venv\Scripts\python.exe" (
  for /f "delims=" %%a in ('"%PYEXE%" -c "import sys; print(str(sys.version_info[0])+chr(46)+str(sys.version_info[1]))" 2^>nul') do set "WANTV=%%a"
  for /f "delims=" %%b in ('".venv\Scripts\python.exe" -c "import sys; print(str(sys.version_info[0])+chr(46)+str(sys.version_info[1]))" 2^>nul') do set "HAVEV=%%b"
  if defined WANTV if defined HAVEV if not "%WANTV%"=="%HAVEV%" (
    echo.
    echo [dev-win] Python mismatch: selected interpreter is %WANTV% but .venv is %HAVEV%.
    echo           Delete the .venv folder in this project, then run this script again.
    echo.
    goto :error
  )
)

if not defined ALLOW_PY314 (
  "%PYEXE%" -c "import sys; sys.exit(0 if sys.version_info < (3,14) else 1)" 2>nul
  if errorlevel 1 (
    echo.
    echo [dev-win] Python 3.14 has no prebuilt wheels for matplotlib/pillow on Windows yet.
    echo           pip will try to compile from source and fail without Visual Studio C++ tools.
    echo.
    echo Fix: Install Python 3.11 x64 from https://www.python.org/downloads/
    echo      Tick "Add python.exe to PATH" and "py launcher", then DELETE the .venv folder here and run this script again.
    echo      Or set PYTHON to 3.11\python.exe before running.
    echo      Advanced: set ALLOW_PY314=1 to try anyway ^(needs MSVC Build Tools^).
    echo.
    goto :error
  )
)

if not exist ".venv\Scripts\python.exe" (
  echo [dev-win] Creating virtual environment .venv ...
  "%PYEXE%" -m venv .venv
  if errorlevel 1 goto :error
)

call ".venv\Scripts\activate.bat"
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\pip.exe" install -r requirements.txt
if errorlevel 1 (
  echo.
  echo [dev-win] pip install failed. On Windows, use Python 3.11 ^(recommended^) or 3.10, delete .venv, run again.
  echo           amulet-nbt 2.1.3 has no cp312 wheel on PyPI; 3.12 needs MSVC Build Tools to compile it.
  echo           Python 3.14 also needs MSVC or a supported Python version.
  goto :error
)

echo [dev-win] Starting LitematicaViewer ...
".venv\Scripts\python.exe" script\LitematicaViewer.py
set "EXITCODE=%ERRORLEVEL%"
if not "%EXITCODE%"=="0" (
  echo.
  echo [dev-win] Process exited with code: %EXITCODE%
  pause
)
popd
exit /b %EXITCODE%

:error
echo.
pause
popd
exit /b 1
