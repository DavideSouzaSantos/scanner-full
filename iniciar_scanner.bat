@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Ambiente nao instalado. Execute instalar.bat primeiro.
    pause
    exit /b 1
)
".venv\Scripts\python" scanner_full.py
if %errorlevel% neq 0 pause
