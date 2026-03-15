@echo off
title ProspectLocal

echo.
echo  ====================================================
echo   ProspectLocal - Sistema de Prospeccao Local
echo  ====================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  ERRO: Python nao encontrado no computador!
    echo.
    echo  Instale o Python em: https://www.python.org/downloads/
    echo  IMPORTANTE: marque "Add Python to PATH" na instalacao!
    echo.
    echo  Abrindo o site para download...
    start https://www.python.org/downloads/
    echo.
    pause
    exit /b
)

echo  Python encontrado! OK
echo.
echo  Instalando dependencias (aguarde...)
echo.

pip install flask apify-client requests reportlab --quiet

echo.
echo  Dependencias OK!
echo.
echo  ====================================================
echo   Servidor iniciando em: http://localhost:5000
echo   Para parar: feche esta janela
echo  ====================================================
echo.

start /b cmd /c "timeout /t 4 /nobreak >nul && start http://localhost:5000"

cd /d "%~dp0"
python app.py

echo.
echo  Servidor encerrado.
pause
