@echo off
setlocal
cd /d "%~dp0"

echo Creating the local LibreTranslate environment...
if not exist "libretranslate-venv\Scripts\python.exe" (
    py -m venv libretranslate-venv
    if errorlevel 1 goto :failed
)

echo Installing LibreTranslate...
"libretranslate-venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :failed

"libretranslate-venv\Scripts\python.exe" -m pip install libretranslate
if errorlevel 1 goto :python_version

echo.
echo LibreTranslate is installed. Start it with run_libretranslate.cmd.
exit /b 0

:python_version
echo.
echo LibreTranslate could not be installed with the available Python version.
echo If the error mentions an unsupported package, install Python 3.12 and run this script again.
exit /b 1

:failed
echo.
echo LibreTranslate setup failed.
exit /b 1
