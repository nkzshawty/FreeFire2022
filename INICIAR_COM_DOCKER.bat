@echo off
:: ==============================================================================
:: FREE FIRE SERVER 2022 - INICIALIZADOR VIA DOCKER COMPOSE
:: ==============================================================================
title Free Fire Server - Docker Compose
cd /d "%~dp0"
cls

echo ==============================================================================
echo                 FREE FIRE SERVER 2022 - DOCKER COMPOSE
echo ==============================================================================
echo.

docker info >nul 2>&1
if errorlevel 1 (
    echo [ERRO] O Docker Desktop nao esta respondendo ou ainda nao foi iniciado.
    echo.
    echo 1. Abra o Docker Desktop e aguarde ele iniciar.
    echo 2. Tente executar este arquivo novamente.
    echo.
    pause
    exit /b 1
)

echo [1/2] Construindo e iniciando os containers Docker...
docker compose up -d --build

echo.
echo [2/2] Status dos containers:
docker compose ps

echo.
echo ==============================================================================
echo Servidor Docker iniciado! Para ver logs em tempo real execute VER_LOGS.bat
echo Para parar o servidor Docker: docker compose down
echo ==============================================================================
pause
