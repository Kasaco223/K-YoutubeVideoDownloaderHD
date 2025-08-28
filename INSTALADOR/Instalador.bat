@echo off
title DESCARGAR Y USAR - YouTube Ultra HD Video Downloader
color 0B

echo.
echo ========================================
echo    🚀 DESCARGAR Y USAR
echo    YouTube Ultra HD Video Downloader
echo ========================================
echo.
echo ⚡ Este instalador descargará TODO automáticamente
echo    desde GitHub y creará el programa listo para usar
echo.

echo 🔍 Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python no está instalado
    echo.
    echo 📥 Descargando Python automáticamente...
    echo.
    echo ⚠️  IMPORTANTE: Marca "Add Python to PATH" durante la instalación
    echo.
    start https://www.python.org/downloads/
    echo.
    echo 🔄 Después de instalar Python, ejecuta este script nuevamente
    echo.
    pause
    exit /b 1
)

echo ✅ Python detectado
echo.

echo 📥 Descargando proyecto completo desde GitHub...
echo.

REM Crear directorio de trabajo
if not exist "YouTubeUltraHD" mkdir YouTubeUltraHD
cd YouTubeUltraHD

REM Descargar ZIP del repositorio
echo 🔄 Descargando archivos...
powershell -Command "try { Invoke-WebRequest -Uri 'https://github.com/Kasaco223/K-YoutubeVideoDownloaderHD/archive/refs/heads/master.zip' -OutFile 'project.zip' -UseBasicParsing; Write-Host '✅ Descarga completada' } catch { Write-Host '❌ Error en descarga: ' $_.Exception.Message }"

if not exist "project.zip" (
    echo.
    echo ❌ Error descargando automáticamente
    echo.
    echo 🔧 Descarga manual:
    echo 1. Ve a: https://github.com/Kasaco223/K-YoutubeVideoDownloaderHD
    echo 2. Haz clic en "Code" -^> "Download ZIP"
    echo 3. Guarda el ZIP en esta carpeta
    echo 4. Renómbralo a: project.zip
    echo 5. Presiona cualquier tecla para continuar
    echo.
    pause
)

echo.
echo 📦 Extrayendo archivos...
powershell -Command "try { Expand-Archive -Path 'project.zip' -DestinationPath '.' -Force; Write-Host '✅ Extracción completada' } catch { Write-Host '❌ Error en extracción: ' $_.Exception.Message }"

REM Buscar carpeta extraída
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
    echo 🔧 Intentando con pip3...
    pip3 install -r requirements.txt
    if errorlevel 1 (
        echo ❌ Error persistente con dependencias
        pause
        exit /b 1
    )
)

echo ✅ Dependencias instaladas
echo.

echo 🔧 Instalando PyInstaller...
pip install pyinstaller
if errorlevel 1 (
    echo ❌ Error instalando PyInstaller
    echo 🔧 Intentando con pip3...
    pip3 install pyinstaller
    if errorlevel 1 (
        echo ❌ Error persistente con PyInstaller
        pause
        exit /b 1
    )
)

echo ✅ PyInstaller instalado
echo.

echo 🎨 Creando icono...
python -c "from PIL import Image, ImageDraw; img = Image.new('RGBA', (256, 256), (0, 0, 0, 0)); draw = ImageDraw.Draw(img); draw.ellipse([20, 20, 236, 236], fill=(99, 102, 241, 255)); img.save('icon.ico', format='ICO', sizes=[(256, 256)])"
if errorlevel 1 (
    echo ⚠️  No se pudo crear el icono (continuando...)
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
    echo 🔧 Continuando con versión Python...
    echo.
    echo ✅ El programa funcionará con: python youtube_360_downloader.py
) else (
    echo ✅ Ejecutable creado exitosamente!
)

echo.
echo 🧹 Limpiando archivos temporales...
if exist build rmdir /s /q build
if exist *.spec del *.spec
if exist project.zip del project.zip

echo.
echo 📁 Moviendo archivos al directorio principal...
cd ..

REM Crear directorio final
if not exist "Programa_Listo" mkdir Programa_Listo

REM Copiar archivos importantes
xcopy "K-YoutubeVideoDownloaderHD-*\dist\*" "Programa_Listo\" /E /I /Y 2>nul
copy "K-YoutubeVideoDownloaderHD-*\youtube_360_downloader.py" "Programa_Listo\" /Y
copy "K-YoutubeVideoDownloaderHD-*\requirements.txt" "Programa_Listo\" /Y
copy "K-YoutubeVideoDownloaderHD-*\README.md" "Programa_Listo\" /Y

echo.
echo 🧹 Limpieza final...
rmdir /s /q K-YoutubeVideoDownloaderHD-*

echo.
echo 🎉 ¡PROGRAMA LISTO PARA USAR!
echo ========================================
echo.
echo 📁 Archivos en: Programa_Listo\
echo.
if exist "Programa_Listo\YouTubeUltraHDDownloader.exe" (
    echo ✅ YouTubeUltraHDDownloader.exe (Ejecutable)
    echo 🚀 Doble clic para ejecutar
) else (
    echo ✅ youtube_360_downloader.py (Código fuente)
    echo 🚀 Ejecuta: python youtube_360_downloader.py
)
echo.
echo 📖 README.md (Documentación)
echo 📋 requirements.txt (Dependencias)
echo.
echo 🌐 Repositorio: https://github.com/Kasaco223/K-YoutubeVideoDownloaderHD
echo.
echo ¡Disfruta descargando videos en Ultra HD! 🎬✨
echo.
pause
