@echo off
title ProspectLocal - Servico WhatsApp (porta 3001)
color 0A

echo.
echo  ============================================
echo   ProspectLocal - Servico WhatsApp
echo   Porta 3001
echo  ============================================
echo.

REM ---- Detectar Node.js ----
node --version >nul 2>&1
if %errorlevel% neq 0 (
  echo  ERRO: Node.js nao encontrado!
  echo.
  echo  Instale o Node.js em: https://nodejs.org
  echo  Escolha a versao LTS.
  echo  Depois de instalar, reinicie o computador.
  echo.
  start https://nodejs.org
  pause
  exit /b 1
)

echo  Node.js OK:
node --version
echo.

REM ---- Entrar na pasta do servico ----
cd /d "%~dp0whatsapp-service"

REM ---- Instalar dependencias se necessario ----
if not exist "node_modules" (
  echo  Instalando dependencias (apenas na primeira vez)...
  echo  Aguarde, pode demorar 2-3 minutos...
  echo.
  npm install
  echo.
  echo  Dependencias instaladas!
  echo.
)

echo  Iniciando servico WhatsApp...
echo  Acesse a aba WHATSAPP no ProspectLocal para conectar seu numero.
echo  Para parar: feche esta janela ou CTRL+C
echo.
echo  ============================================
echo.

node server.js

pause
