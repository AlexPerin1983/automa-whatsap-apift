@echo off
setlocal
title Exemplo Envio Botao - InfiniteAPI

set "ROOT_DIR=%~dp0"
set "APP_DIR="

for /d %%D in ("%ROOT_DIR%exemplo envio*") do (
  if exist "%%~fD\baileys_interactive-main\package.json" (
    set "APP_DIR=%%~fD\baileys_interactive-main"
  )
)

if not defined APP_DIR (
  echo.
  echo [ERRO] Projeto de exemplo nao encontrado em:
  echo %ROOT_DIR%
  echo.
  pause
  exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
  echo.
  echo [ERRO] Node.js nao encontrado no PATH.
  echo Instale o Node.js 20+ e tente novamente.
  echo.
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo.
  echo [ERRO] npm nao encontrado no PATH.
  echo.
  pause
  exit /b 1
)

cd /d "%APP_DIR%"

if not exist ".env" (
  echo [INFO] Criando arquivo .env a partir do .env.example...
  copy /y ".env.example" ".env" >nul
)

if not exist "node_modules" (
  echo.
  echo ==========================================
  echo Instalando dependencias do projeto exemplo
  echo ==========================================
  call npm install
  if errorlevel 1 (
    echo.
    echo [ERRO] Falha ao instalar dependencias.
    echo.
    pause
    exit /b 1
  )
)

echo.
echo ==========================================
echo Exemplo de envio de botao iniciando...
echo Pasta: %APP_DIR%
echo URL:   http://localhost:8787
echo API:   http://localhost:8787/health
echo.
echo Quando abrir, conecte uma instancia e teste o envio de botao por la.
echo ==========================================
echo.

start "" "http://localhost:8787"
call npm run dev

endlocal
