@echo off
setlocal
cd /d "%~dp0"

if not exist "libretranslate-venv\Scripts\libretranslate.exe" (
    echo LibreTranslate is not installed yet.
    echo Run setup_libretranslate.cmd first.
    exit /b 1
)

echo Starting LibreTranslate at http://127.0.0.1:5002
echo Keep this terminal open while using the application.
"libretranslate-venv\Scripts\libretranslate.exe" --host 127.0.0.1 --port 5002 --load-only en,fr,ro
