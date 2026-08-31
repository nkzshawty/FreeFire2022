@echo off
REM ===========================================================================
REM  Free Fire Server - runner local (Windows)
REM  Sobe os 4 servidores Node (live/login/main/tcp) usando SQLite + .env local.
REM  Uso: da dois cliques neste arquivo, ou rode `start-local.bat` no terminal.
REM ===========================================================================
setlocal
cd /d "%~dp0"

if not exist "node_modules\" (
  echo [setup] Instalando dependencias pela primeira vez...
  call npm install
  if errorlevel 1 (
    echo [erro] npm install falhou. Corrija os erros acima e rode de novo.
    pause
    exit /b 1
  )
)

echo [start] Subindo os servidores locais...
echo         live  http://127.0.0.1:19134
echo         login http://127.0.0.1:19132
echo         main  http://127.0.0.1:19133
echo         tcp   127.0.0.1:8084
echo.
call npm start

pause
