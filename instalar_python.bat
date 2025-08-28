@echo off
chcp 65001 >nul
echo.
echo ========================================
echo    INSTALADOR DE PYTHON PARA WINDOWS
echo ========================================
echo.

echo Verificando si Python esta instalado...
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Python ya esta instalado!
    python --version
    echo.
    echo Verificando pip...
    pip --version >nul 2>&1
    if %errorlevel% equ 0 (
        echo ✅ pip esta disponible!
        pip --version
        echo.
        echo 🎉 ¡Todo listo! Puedes ejecutar la aplicacion:
        echo    python youtube_360_downloader.py
        pause
        exit /b 0
    ) else (
        echo ⚠️  Python esta instalado pero pip no esta disponible
    )
) else (
    echo ❌ Python no esta instalado
)

echo.
echo 📥 Opciones para instalar Python:
echo.
echo 1. Microsoft Store (mas facil)
echo 2. Descarga directa desde python.org (recomendado)
echo 3. Tutorial de instalacion
echo 4. Salir
echo.

set /p choice="Elige una opcion (1-4): "

if "%choice%"=="1" (
    echo.
    echo 🔄 Abriendo Microsoft Store...
    start ms-windows-store://pdp/?ProductId=9NRWMJP3717K
    echo ✅ Microsoft Store abierto. Busca 'Python 3.11' e instalalo
    echo.
    echo 📋 IMPORTANTE: Despues de instalar, reinicia esta ventana
)

if "%choice%"=="2" (
    echo.
    echo 🌐 Abriendo python.org...
    start https://python.org/downloads
    echo ✅ Pagina de descarga abierta
    echo.
    echo 📋 IMPORTANTE: Marca 'Add Python to PATH' durante la instalacion
)

if "%choice%"=="3" (
    echo.
    echo 📚 Abriendo tutorial...
    start https://docs.python.org/3/using/windows.html
    echo ✅ Tutorial abierto
)

if "%choice%"=="4" (
    echo.
    echo 👋 ¡Hasta luego!
    pause
    exit /b 0
)

echo.
echo 📋 Pasos despues de instalar Python:
echo 1. Reinicia esta ventana de comando
echo 2. Ejecuta: python --version
echo 3. Ejecuta: pip --version
echo 4. Vuelve a esta carpeta y ejecuta: python install.py
echo.
echo ✨ ¡Despues de instalar Python podras usar la aplicacion!
echo.
pause
