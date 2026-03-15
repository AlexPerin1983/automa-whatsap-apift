@echo off
title Limpando dependencias WhatsApp...
color 0E
cd /d "%~dp0whatsapp-service"

echo.
echo  Removendo modulos antigos (better-sqlite3 que causava erro)...
if exist "node_modules" (
  rmdir /s /q "node_modules"
  echo  Removido!
) else (
  echo  Pasta node_modules nao existe, OK.
)

if exist "package-lock.json" del /q "package-lock.json"

echo.
echo  Instalando dependencias novas (sem compilacao nativa)...
echo  Aguarde 1-2 minutos...
echo.
call npm install

if %errorlevel% equ 0 (
  echo.
  echo  ==========================================
  echo   Instalacao concluida com sucesso!
  echo   Agora use o INICIAR WHATSAPP.bat
  echo  ==========================================
) else (
  echo.
  echo  Erro na instalacao. Verifique sua conexao com a internet.
)

echo.
pause
