@echo off
title Verificar Python

echo.
echo  Verificando se Python esta instalado...
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  ============================================
    echo   RESULTADO: Python NAO esta instalado
    echo  ============================================
    echo.
    echo  Acesse python.org/downloads para instalar.
    echo  LEMBRE: marque "Add Python to PATH" !
    echo.
) else (
    echo  ============================================
    echo   RESULTADO: Python JA esta instalado!
    echo  ============================================
    echo.
    python --version
    echo.
    echo  Tudo certo! Pode usar o INICIAR AQUI.bat
    echo.
)

pause
