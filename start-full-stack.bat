@echo off
REM ===========================================================================
REM  Free Fire Server - sobe a STACK COMPLETA automaticamente (sem Docker):
REM    1) Redis (127.0.0.1:6379)
REM    2) os 4 servidores Node (live/login/main/tcp)  -> npm start
REM    3) matchmaker  (MM_MIN_PLAYERS=1, MATCH_PUBLIC_HOST=192.168.1.2)
REM    4) match-server Go (UDP :10100, MATCH_BOT=1)
REM  Cada peca abre na propria janela. Feche as janelas pra parar tudo.
REM ===========================================================================
setlocal
cd /d "%~dp0"

echo [1/4] Verificando Redis na porta 6379...
powershell -NoProfile -Command "try{(New-Object Net.Sockets.TcpClient).Connect('127.0.0.1',6379);exit 0}catch{exit 1}" >nul 2>&1
if errorlevel 1 (
  echo        Redis nao respondeu - tentando iniciar em nova janela...
  where memurai >nul 2>&1 && start "Redis-Memurai" cmd /k memurai
  where redis-server >nul 2>&1 && start "Redis" cmd /k redis-server
  timeout /t 3 >nul
) else (
  echo        Redis OK.
)

echo [2/4] Subindo os 4 servidores Node (live/login/main/tcp)...
start "FF Servers" cmd /k "cd /d ""%~dp0"" & npm start"

echo [3/4] Subindo o matchmaker...
start "FF Matchmaker" cmd /k "cd /d ""%~dp0"" & set ""MM_MIN_PLAYERS=1"" & set ""MATCH_PUBLIC_HOST=192.168.1.2"" & npm run matchmaker"

echo [4/4] Compilando e subindo o match-server Go (UDP :10100)...
start "FF Match Server" cmd /k "cd /d ""%~dp0match-server"" & go build -o match-server.exe . && set ""MATCH_BOT=1"" && match-server.exe -addr :10100"

echo.
echo ============================================================
echo  Tudo iniciado em janelas separadas. Confira cada uma:
echo    FF Servers      -^> [bus] shared instance connected (sem ECONNREFUSED)
echo    FF Matchmaker   -^> [mm] ACQUIRED leadership
echo    FF Match Server -^> [mm-udp] match server listening on :10100
echo ============================================================
echo.
echo Agora abra o jogo: login - selecao de modo - Treinamento - Matching.
pause
