@echo off
chcp 65001 >nul
title Kuri IA - Assistente Pessoal

echo ================================================
echo   Kuri IA - Iniciando...
echo ================================================
echo.

:: Vai para o diretorio onde o .bat esta
cd /d "%~dp0"

echo Escolha como deseja executar a Kuri IA:
echo [1] Rodar via Python (Recomendado - Mais estavel, com whisper-small)
echo [2] Rodar versao Compilada (dist\KuriIA\KuriIA.exe)
echo.
set /p opcao="Escolha uma opcao [1 ou 2] (Padrao: 1): "

if "%opcao%"=="2" (
    if exist "dist\KuriIA\KuriIA.exe" (
        echo [OK] Iniciando versao compilada...
        start "" "dist\KuriIA\KuriIA.exe"
        goto :eof
    ) else (
        echo [AVISO] Executavel compilado nao encontrado. Iniciando via Python...
        echo.
    )
)

if not exist ".venv\Scripts\activate.bat" (
    echo [ERRO] Ambiente virtual nao encontrado!
    echo.
    echo Por favor, crie o ambiente virtual primeiro:
    echo   python -m venv .venv
    echo   .venv\Scripts\activate
    echo   pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

echo [OK] Ambiente virtual ativado.
echo [INFO] Iniciando Kuri IA (interface grafica)...
echo.

python kuri_desktop.py

if %errorlevel% neq 0 (
    echo.
    echo [AVISO] O programa foi encerrado com codigo de erro %errorlevel%.
    echo.
    pause
)
