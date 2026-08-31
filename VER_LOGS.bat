@echo off
:: ==============================================================================
:: FREE FIRE SERVER - MONITOR DE LOGS DO DOCKER
:: ==============================================================================
title Free Fire Server - Logs em Tempo Real
cd /d "%~dp0"
cls

echo ==============================================================================
echo                 ACOMPANHANDO LOGS DO SERVIDOR (DOCKER)
echo ==============================================================================
echo Pressione Ctrl + C para sair do monitor de logs a qualquer momento.
echo.

docker compose logs -f live login main gateway match
pause
