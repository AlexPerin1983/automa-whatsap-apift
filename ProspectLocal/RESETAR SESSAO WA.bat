@echo off
title Resetar Sessao WhatsApp
color 0C

echo.
echo ============================================================
echo   RESETAR SESSAO WHATSAPP
echo   Isso vai apagar a sessao e voce precisara escanear
echo   o QR Code novamente no ProspectLocal.
echo ============================================================
echo.
echo ATENCAO: Feche o INICIAR TUDO / INICIAR WHATSAPP antes!
echo.
set /p CONFIRMA=Deseja continuar? (S/N):

if /i not "%CONFIRMA%"=="S" (
    echo Cancelado.
    pause
    exit /b
)

echo.
echo Parando servico Node.js (se estiver rodando)...
taskkill /f /im node.exe >nul 2>&1

echo.
echo Apagando sessoes...
if exist "%~dp0whatsapp-service\sessions\" (
    rmdir /s /q "%~dp0whatsapp-service\sessions\"
    echo Sessoes apagadas com sucesso!
) else (
    echo Nenhuma sessao encontrada.
)

echo.
echo ============================================================
echo   PRONTO! Sessao resetada.
echo.
echo   Agora:
echo   1. Abra o INICIAR TUDO.bat
echo   2. Va em WhatsApp no ProspectLocal
echo   3. Clique em "Conectar" e escaneie o QR Code
echo ============================================================
echo.
pause
