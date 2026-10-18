@echo off
rem Gera um ScannerFull.exe unico com PyInstaller (opcional).
rem Execute DEPOIS do instalar.bat.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Ambiente nao instalado. Execute instalar.bat primeiro.
    pause
    exit /b 1
)
echo Instalando PyInstaller...
".venv\Scripts\python" -m pip install pyinstaller
echo.
echo Gerando o executavel... pode demorar alguns minutos.
".venv\Scripts\python" -m PyInstaller --noconfirm --onefile --windowed --name "ScannerFull" --add-data "pecas;pecas" scanner_full.py
echo.
if exist "dist\ScannerFull.exe" (
    echo PRONTO: dist\ScannerFull.exe
    echo Copie esse arquivo para o notebook e execute. Nao precisa instalar nada.
) else (
    echo [ERRO] O executavel nao foi gerado. Veja as mensagens acima.
)
pause
