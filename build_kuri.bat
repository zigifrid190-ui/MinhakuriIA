@echo off
chcp 65001 >nul
title Construindo Kuri IA (PyInstaller)

echo ================================================
echo   Kuri IA - Build com PyInstaller
echo ================================================
echo.

cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo [ERRO] Ambiente virtual nao encontrado!
    echo Execute primeiro:
    echo   python -m venv .venv
    echo   .venv\Scripts\activate
    echo   pip install -r requirements.txt pyinstaller
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

echo [INFO] Instalando/verificando PyInstaller...
pip install pyinstaller --quiet

echo [INFO] Limpando builds anteriores...
if exist "build" rmdir /s /q build >nul 2>&1
if exist "dist" rmdir /s /q dist >nul 2>&1

echo [INFO] Iniciando build (pode demorar alguns minutos)...
echo.

pyinstaller kuri.spec --clean --noconfirm

echo.
if exist "dist\KuriIA\KuriIA.exe" (
    echo [SUCESSO] Executavel criado em:
    echo   dist\KuriIA\KuriIA.exe
    echo.
    echo Agora use o run_kuri.bat para executar (ele vai preferir o .exe).
) else (
    echo [ERRO] Build falhou. Verifique as mensagens acima.
)

echo.
pause
