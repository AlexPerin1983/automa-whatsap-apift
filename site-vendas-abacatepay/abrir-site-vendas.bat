@echo off
title Site Vendas AbacatePay
cd /d "%~dp0"

echo Iniciando o site de vendas...
start "" cmd /k "cd /d "%~dp0" && npm run dev"

timeout /t 5 /nobreak >nul
start "" http://localhost:3000
