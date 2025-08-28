@echo off
title Instalador - YouTube Ultra HD Video Downloader
color 0B

echo.
echo ========================================
echo    🚀 INSTALADOR COMPLETO
echo    YouTube Ultra HD Video Downloader
echo ========================================
echo.
echo ⚡ Este instalador descargará TODO automáticamente
echo    desde GitHub y creará el programa listo para usar
echo.

echo 🔍 Verificando Python...
echo.

REM Intentar diferentes comandos de Python
set PYTHON_CMD=
set PYTHON_VERSION=

REM Probar python
python --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    goto :python_found
)

REM Probar python3
python3 --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python3
    for /f "tokens=2" %%i in ('python3 --version 2^>^&1') do set PYTHON_VERSION=%%i
    goto :python_found
)

REM Probar py (Windows Python Launcher)
py --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=py
    for /f "tokens=2" %%i in ('py --version 2^>^&1') do set PYTHON_VERSION=%%i
    goto :python_found
)

REM Probar python.exe directamente
python.exe --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python.exe
    for /f "tokens=2" %%i in ('python.exe --version 2^>^&1') do set PYTHON_VERSION=%%i
    goto :python_found
)

:python_not_found
echo ❌ Python no está instalado o no está en el PATH
echo.
echo 📥 Descargando Python automáticamente...
echo.
echo ⚠️  IMPORTANTE: 
echo    1. Marca "Add Python to PATH" durante la instalación
echo    2. Marca "Install for all users" si es posible
echo    3. Reinicia la consola después de instalar
echo.
start https://www.python.org/downloads/
echo.
echo 🔄 Después de instalar Python:
echo    1. Cierra esta ventana
echo    2. Abre una NUEVA consola
echo    3. Ejecuta este script nuevamente
echo.
pause
exit /b 1

:python_found
echo ✅ Python detectado: %PYTHON_VERSION%
echo 🔧 Comando: %PYTHON_CMD%

REM Verificar versión mínima (3.8+)
for /f "tokens=2 delims=." %%a in ("%PYTHON_VERSION%") do set MAJOR_VERSION=%%a
for /f "tokens=3 delims=." %%b in ("%PYTHON_VERSION%") do set MINOR_VERSION=%%b

if %MAJOR_VERSION% LSS 3 (
    echo ❌ Python %PYTHON_VERSION% no es compatible
    echo 📋 Se requiere Python 3.8 o superior
    goto :python_not_found
)

if %MAJOR_VERSION% EQU 3 (
    if %MINOR_VERSION% LSS 8 (
        echo ❌ Python %PYTHON_VERSION% no es compatible
        echo 📋 Se requiere Python 3.8 o superior
        goto :python_not_found
    )
)

echo ✅ Versión compatible: %PYTHON_VERSION%
echo.

REM Verificar pip
echo 🔍 Verificando pip...
%PYTHON_CMD% -m pip --version >nul 2>&1
if errorlevel 1 (
    echo ❌ pip no está disponible
    echo 🔧 Instalando pip...
    %PYTHON_CMD% -m ensurepip --upgrade
    if errorlevel 1 (
        echo ❌ Error instalando pip
        pause
        exit /b 1
    )
)
echo ✅ pip disponible
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
echo 🔧 Usando: %PYTHON_CMD% -m pip install -r requirements.txt
%PYTHON_CMD% -m pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Error instalando dependencias
    echo 🔧 Intentando con --user...
    %PYTHON_CMD% -m pip install --user -r requirements.txt
    if errorlevel 1 (
        echo ❌ Error persistente con dependencias
        echo.
        echo 🔍 Diagnóstico:
        echo - Python: %PYTHON_CMD% %PYTHON_VERSION%
        echo - pip: %PYTHON_CMD% -m pip --version
        echo - Directorio actual: %CD%
        echo - Archivo requirements: %CD%\requirements.txt
        echo.
        pause
        exit /b 1
    )
)

echo ✅ Dependencias instaladas
echo.

echo 🔧 Instalando PyInstaller...
%PYTHON_CMD% -m pip install pyinstaller
if errorlevel 1 (
    echo ❌ Error instalando PyInstaller
    echo 🔧 Intentando con --user...
    %PYTHON_CMD% -m pip install --user pyinstaller
    if errorlevel 1 (
        echo ❌ Error persistente con PyInstaller
        pause
        exit /b 1
    )
)

echo ✅ PyInstaller instalado
echo.

echo 🎨 Creando icono...
%PYTHON_CMD% -c "from PIL import Image, ImageDraw; img = Image.new('RGBA', (256, 256), (0, 0, 0, 0)); draw = ImageDraw.Draw(img); draw.ellipse([20, 20, 236, 236], fill=(99, 102, 241, 255)); img.save('icon.ico', format='ICO', sizes=[(256, 256)])"
if errorlevel 1 (
    echo ⚠️  No se pudo crear el icono (continuando...)
) else (
    echo ✅ Icono creado
)

echo.
echo ⚙️  Creando ejecutable...
echo 🔨 Esto puede tomar varios minutos...
echo 🔧 Usando: %PYTHON_CMD% -m PyInstaller
echo.

%PYTHON_CMD% -m PyInstaller --onefile --windowed --name=YouTubeUltraHDDownloader --icon=icon.ico youtube_360_downloader.py

if errorlevel 1 (
    echo ❌ Error creando ejecutable
    echo 🔧 Continuando con versión Python...
    echo.
    echo ✅ El programa funcionará con: %PYTHON_CMD% youtube_360_downloader.py
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
    echo 🚀 Ejecuta: %PYTHON_CMD% youtube_360_downloader.py
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
