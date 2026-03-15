@echo off
title ProspectLocal - Sistema Completo
color 0B
cd /d "%~dp0"

echo.
echo  ============================================
echo   ProspectLocal - Sistema Completo
echo   Flask (porta 5000) + WhatsApp (porta 3001)
echo  ============================================
echo.

REM ---- Verificar Python ----
python --version >nul 2>&1
if %errorlevel% neq 0 (
  echo  ERRO: Python nao encontrado no PATH.
  echo  Use o INICIAR AQUI.bat que ja funcionava antes.
  pause
  exit /b 1
)
echo  Python OK

REM ---- Instalar deps Python ----
python -m pip install flask apify-client requests reportlab --quiet 2>nul

REM ---- Verificar Node.js ----
node --version >nul 2>&1
if %errorlevel% neq 0 (
  echo  AVISO: Node.js nao encontrado. Iniciando so o Flask.
  goto start_flask
)
echo  Node.js OK

REM ---- Instalar deps Node se necessario ----
if not exist "%~dp0whatsapp-service\node_modules" (
  echo  Instalando dependencias WhatsApp pela primeira vez...
  cd /d "%~dp0whatsapp-service"
  call npm install
  cd /d "%~dp0"
  echo  OK!
)

REM ---- Criar e rodar script auxiliar para WA service ----
echo @echo off > "%TEMP%\wa_start.bat"
echo cd /d "%~dp0whatsapp-service" >> "%TEMP%\wa_start.bat"
echo node server.js >> "%TEMP%\wa_start.bat"
echo pause >> "%TEMP%\wa_start.bat"

start "WhatsApp - Porta 3001" "%TEMP%\wa_start.bat"
echo  Servico WhatsApp iniciado!
timeout /t 3 /nobreak >nul

:start_flask
echo.
echo  Iniciando Flask na porta 5000...
start /b cmd /c "timeout /t 5 /nobreak >nul && start http://localhost:5000"
echo  Acesse: http://localhost:5000
echo  Para parar: feche esta janela (CTRL+C)
echo.
echo  ============================================
echo.
cd /d "%~dp0"
python app.py

pause
