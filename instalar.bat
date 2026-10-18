@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title Instalador - Scanner Full

echo ================================================
echo   SCANNER FULL - Instalador
echo ================================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [1/4] Python nao encontrado. Tentando instalar via winget...
    echo.
    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    echo.
    echo ------------------------------------------------
    echo Python instalado. Feche esta janela e execute o
    echo instalar.bat NOVAMENTE para concluir.
    echo ------------------------------------------------
    pause
    exit /b 0
)

echo [1/4] Python OK:
python --version
echo.

echo [2/4] Criando ambiente virtual...
if not exist ".venv" (
    python -m venv .venv
)
echo OK.
echo.

echo [3/4] Instalando dependencias. Pode demorar alguns minutos...
".venv\Scripts\python" -m pip install --upgrade pip
".venv\Scripts\python" -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Falha ao instalar as dependencias. Verifique a internet e tente de novo.
    pause
    exit /b 1
)
echo OK.
echo.

echo [4/4] Criando atalho na Area de Trabalho...
powershell -NoProfile -Command "try { $ws = New-Object -ComObject WScript.Shell; $dt = [Environment]::GetFolderPath('Desktop'); $sc = $ws.CreateShortcut($dt + '\Scanner Full.lnk'); $sc.TargetPath = '%CD%\iniciar_scanner.bat'; $sc.WorkingDirectory = '%CD%'; $sc.Save(); Write-Host 'OK.' } catch { Write-Host ('[AVISO] Nao foi possivel criar o atalho: ' + $_.Exception.Message); Write-Host 'Use o iniciar_scanner.bat para abrir o app.' }"
echo.

echo ================================================
echo  INSTALACAO CONCLUIDA!
echo.
echo  Use o atalho "Scanner Full" na Area de Trabalho
echo  ou execute iniciar_scanner.bat
echo ================================================
pause
