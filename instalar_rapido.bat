@echo off
title Instalador Rápido - YouTube Ultra HD Video Downloader
color 0A

echo.
echo ========================================
echo    🚀 INSTALADOR RÁPIDO
echo    YouTube Ultra HD Video Downloader
echo ========================================
echo.

echo 🔍 Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python no está instalado o no está en el PATH
    echo.
    echo 📥 Descargando Python...
    echo Abriendo python.org en tu navegador...
    start https://www.python.org/downloads/
    echo.
    echo ⚠️  IMPORTANTE: Marca "Add Python to PATH" durante la instalación
    echo.
    pause
    exit /b 1
)

echo ✅ Python detectado
echo.

echo 📦 Instalando dependencias...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Error instalando dependencias
    pause
    exit /b 1
)

echo ✅ Dependencias instaladas
echo.

echo 🔧 Instalando PyInstaller...
pip install pyinstaller
if errorlevel 1 (
    echo ❌ Error instalando PyInstaller
    pause
    exit /b 1
)

echo ✅ PyInstaller instalado
echo.

echo 🎨 Creando icono...
python -c "from PIL import Image, ImageDraw; img = Image.new('RGBA', (256, 256), (0, 0, 0, 0)); draw = ImageDraw.Draw(img); draw.ellipse([20, 20, 236, 236], fill=(99, 102, 241, 255)); img.save('icon.ico', format='ICO', sizes=[(256, 256)])"
if errorlevel 1 (
    echo ⚠️  No se pudo crear el icono
) else (
    echo ✅ Icono creado
)

echo.
echo ⚙️  Creando ejecutable...
echo 🔨 Esto puede tomar varios minutos...
echo.

pyinstaller --onefile --windowed --name=YouTubeUltraHDDownloader --icon=icon.ico youtube_360_downloader.py

if errorlevel 1 (
    echo ❌ Error creando ejecutable
    pause
    exit /b 1
)

echo ✅ Ejecutable creado exitosamente!
echo.

echo 🧹 Limpiando archivos temporales...
if exist build rmdir /s /q build
if exist *.spec del *.spec

echo.
echo 🎉 ¡INSTALACIÓN COMPLETADA!
echo ========================================
echo.
echo 📁 Archivos creados:
echo    • dist/YouTubeUltraHDDownloader.exe
echo    • ejecutar_programa.bat
echo.
echo 🚀 Para ejecutar el programa:
echo    1. Doble clic en dist/YouTubeUltraHDDownloader.exe
echo    2. O ejecuta ejecutar_programa.bat
echo.
echo ¡Disfruta descargando videos en Ultra HD!
echo.
pause
