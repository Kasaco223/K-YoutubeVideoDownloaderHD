@echo off
title Instalador Completo - YouTube Ultra HD Video Downloader
color 0A

echo.
echo ========================================
echo    🚀 INSTALADOR COMPLETO
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

echo 📥 Descargando proyecto desde GitHub...
echo.

REM Crear directorio temporal
if not exist "temp_download" mkdir temp_download
cd temp_download

REM Descargar archivo ZIP del repositorio
echo 🔄 Descargando archivo ZIP...
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/Kasaco223/K-YoutubeVideoDownloaderHD/archive/refs/heads/master.zip' -OutFile 'project.zip'"

if not exist "project.zip" (
    echo ❌ Error descargando el proyecto
    echo.
    echo 🔧 Solución alternativa:
    echo 1. Ve a: https://github.com/Kasaco223/K-YoutubeVideoDownloaderHD
    echo 2. Haz clic en "Code" -^> "Download ZIP"
    echo 3. Extrae el ZIP en esta carpeta
    echo 4. Ejecuta este script nuevamente
    echo.
    pause
    exit /b 1
)

echo ✅ Proyecto descargado
echo.

echo 📦 Extrayendo archivos...
powershell -Command "Expand-Archive -Path 'project.zip' -DestinationPath '.' -Force"

REM Buscar la carpeta extraída
for /d %%i in (K-YoutubeVideoDownloaderHD-*) do (
    echo ✅ Archivos extraídos en: %%i
    cd "%%i"
    goto :continue
)

:continue

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
echo 📁 Moviendo archivos al directorio principal...
cd ..

REM Crear directorio final
if not exist "YouTubeUltraHDDownloader" mkdir YouTubeUltraHDDownloader

REM Copiar archivos importantes
xcopy "temp_download\K-YoutubeVideoDownloaderHD-*\dist\*" "YouTubeUltraHDDownloader\" /E /I /Y
copy "temp_download\K-YoutubeVideoDownloaderHD-*\youtube_360_downloader.py" "YouTubeUltraHDDownloader\" /Y
copy "temp_download\K-YoutubeVideoDownloaderHD-*\requirements.txt" "YouTubeUltraHDDownloader\" /Y
copy "temp_download\K-YoutubeVideoDownloaderHD-*\README.md" "YouTubeUltraHDDownloader\" /Y

echo.
echo 🧹 Limpiando archivos temporales...
rmdir /s /q temp_download

echo.
echo 🎉 ¡INSTALACIÓN COMPLETADA!
echo ========================================
echo.
echo 📁 Archivos creados en: YouTubeUltraHDDownloader\
echo    • YouTubeUltraHDDownloader.exe (Ejecutable)
echo    • youtube_360_downloader.py (Código fuente)
echo    • requirements.txt (Dependencias)
echo    • README.md (Documentación)
echo.
echo 🚀 Para ejecutar el programa:
echo    1. Doble clic en YouTubeUltraHDDownloader.exe
echo    2. O ejecuta: python youtube_360_downloader.py
echo.
echo ¡Disfruta descargando videos en Ultra HD!
echo.
pause
