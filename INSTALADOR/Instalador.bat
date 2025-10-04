@echo off
title Instalador Inteligente - YouTube Ultra HD Video Downloader
color 0B

echo.
echo ========================================
echo    🚀 INSTALADOR INTELIGENTE
echo    YouTube Ultra HD Video Downloader
echo ========================================
echo.
echo ⚡ Este instalador detecta y repara Python automáticamente
echo    y luego instala todo el programa desde GitHub
echo.

REM ========================================
REM    🔍 DETECCIÓN Y REPARACIÓN DE PYTHON
REM ========================================

echo 🔍 Verificando Python...
echo.

set PYTHON_CMD=
set PYTHON_VERSION=
set PYTHON_PATH=
set PYTHON_NEEDS_REPAIR=0

REM Probar diferentes comandos de Python
python --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    goto :python_working
)

python3 --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python3
    for /f "tokens=2" %%i in ('python3 --version 2^>^&1') do set PYTHON_VERSION=%%i
    goto :python_working
)

py --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=py
    for /f "tokens=2" %%i in ('py --version 2^>^&1') do set PYTHON_VERSION=%%i
    goto :python_working
)

python.exe --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python.exe
    for /f "tokens=2" %%i in ('python.exe --version 2^>^&1') do set PYTHON_VERSION=%%i
    goto :python_working
)

REM Python no está en PATH, buscar instalado
echo ❌ Python no está en PATH
echo 🔍 Buscando Python instalado en el sistema...
echo.

set PYTHON_NEEDS_REPAIR=1

REM Buscar en ubicaciones comunes
if exist "C:\Program Files\Python*" (
    for /d %%i in ("C:\Program Files\Python*") do (
        if exist "%%i\python.exe" (
            set PYTHON_PATH=%%i
            echo ✅ Python encontrado en: %%i
            goto :found_installed_python
        )
    )
)

if exist "C:\Program Files (x86)\Python*" (
    for /d %%i in ("C:\Program Files (x86)\Python*") do (
        if exist "%%i\python.exe" (
            set PYTHON_PATH=%%i
            echo ✅ Python encontrado en: %%i
            goto :found_installed_python
        )
    )
)

if exist "%LOCALAPPDATA%\Programs\Python*" (
    for /d %%i in ("%LOCALAPPDATA%\Programs\Python*") do (
        if exist "%%i\python.exe" (
            set PYTHON_PATH=%%i
            echo ✅ Python encontrado en: %%i
            goto :found_installed_python
        )
    )
)

if exist "%USERPROFILE%\AppData\Local\Programs\Python*" (
    for /d %%i in ("%USERPROFILE%\AppData\Local\Programs\Python*") do (
        if exist "%%i\python.exe" (
            set PYTHON_PATH=%%i
            echo ✅ Python encontrado en: %%i
            goto :found_installed_python
        )
    )
)

if exist "%USERPROFILE%\Python*" (
    for /d %%i in ("%USERPROFILE%\Python*") do (
        if exist "%%i\python.exe" (
            set PYTHON_PATH=%%i
            echo ✅ Python encontrado en: %%i
            goto :found_installed_python
        )
    )
)

REM --- NUEVO BLOQUE: Instalación automática de Python si no está ---
:python_not_found

echo ❌ No se encontró Python instalado

echo.
echo 📥 Descargando instalador oficial de Python...
set PYTHON_VERSION_URL=https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe
set PYTHON_INSTALLER=python-installer.exe

REM Descargar el instalador de Python
powershell -Command "Invoke-WebRequest -Uri '%PYTHON_VERSION_URL%' -OutFile '%PYTHON_INSTALLER%'"
if not exist "%PYTHON_INSTALLER%" (
    echo ❌ No se pudo descargar el instalador de Python
    echo.
    echo Descarga manual: %PYTHON_VERSION_URL%
    pause
    exit /b 1
)

echo ✅ Instalador descargado: %PYTHON_INSTALLER%
echo.
echo 🚀 Instalando Python en modo PASIVO (verás una barra de progreso)...
echo    Por favor, espera a que termine la instalación.
echo    Si ves algún error, toma nota o haz captura de pantalla.
"%PYTHON_INSTALLER%" /passive InstallAllUsers=1 PrependPath=1 Include_pip=1
if errorlevel 1 (
    echo ❌ Error instalando Python
    pause
    exit /b 1
)

echo ✅ Python instalado correctamente.
echo.
del "%PYTHON_INSTALLER%"
echo 🔄 Reiniciando detección de Python...
goto :REINICIAR_DETECCION_PYTHON

REM --- FIN BLOQUE NUEVO ---

REM Justo antes de la detección de Python, agregar etiqueta para reinicio
:REINICIAR_DETECCION_PYTHON
REM Re-detección automática de Python tras la instalación
set PYTHON_CMD=
set PYTHON_VERSION=
set PYTHON_PATH=

REM Intentar con 'python'
python --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    for /f "usebackq tokens=*" %%p in (`python -c "import sys,os;print(os.path.dirname(sys.executable))"`) do set PYTHON_PATH=%%p
    goto :found_installed_python
)

REM Intentar con 'python3'
python3 --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python3
    for /f "tokens=2" %%i in ('python3 --version 2^>^&1') do set PYTHON_VERSION=%%i
    for /f "usebackq tokens=*" %%p in (`python3 -c "import sys,os;print(os.path.dirname(sys.executable))"`) do set PYTHON_PATH=%%p
    goto :found_installed_python
)

REM Intentar con 'py'
py --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=py
    for /f "tokens=2" %%i in ('py --version 2^>^&1') do set PYTHON_VERSION=%%i
    for /f "usebackq tokens=*" %%p in (`py -c "import sys,os;print(os.path.dirname(sys.executable))"`) do set PYTHON_PATH=%%p
    goto :found_installed_python
)

REM Intentar con 'python.exe'
python.exe --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python.exe
    for /f "tokens=2" %%i in ('python.exe --version 2^>^&1') do set PYTHON_VERSION=%%i
    for /f "usebackq tokens=*" %%p in (`python.exe -c "import sys,os;print(os.path.dirname(sys.executable))"`) do set PYTHON_PATH=%%p
    goto :found_installed_python
)

REM Si aún no se detecta, volver al flujo de instalación
goto :python_not_found

:found_installed_python
echo.
echo 📋 Información de Python:
echo - Ruta: %PYTHON_PATH%
echo - Ejecutable: %PYTHON_PATH%\python.exe
echo.

REM Verificar versión
echo 🔍 Verificando versión...
"%PYTHON_PATH%\python.exe" --version >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=2" %%i in ('"%PYTHON_PATH%\python.exe" --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo ✅ Versión: %PYTHON_VERSION%
) else (
    echo ❌ No se pudo obtener la versión
    set PYTHON_VERSION=Desconocida
)

REM Verificar versión mínima
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

REM Reparar Python si es necesario
if %PYTHON_NEEDS_REPAIR% EQU 1 (
    echo 🔧 Python necesita ser agregado al PATH
    echo.
    echo ⚠️  IMPORTANTE: Este script necesita permisos de administrador
    echo para modificar las variables de entorno del sistema.
    echo.
    echo 🔒 Verificando permisos de administrador...
    net session >nul 2>&1
    if errorlevel 1 (
        echo ❌ No tienes permisos de administrador
        echo.
        echo 🔧 Soluciones:
        echo 1. Hacer clic derecho en este archivo
        echo 2. Seleccionar "Ejecutar como administrador"
        echo 3. O ejecutar CMD como administrador y navegar aquí
        echo.
        pause
        exit /b 1
    )

    echo ✅ Permisos de administrador confirmados
    echo.

    echo 🔧 Agregando Python al PATH del sistema...
    echo.

    REM Agregar Python al PATH del sistema
    setx PATH "%PATH%;%PYTHON_PATH%" /M
    if errorlevel 1 (
        echo ❌ Error agregando Python al PATH del sistema
        echo.
        echo 🔧 Intentando método alternativo...
        echo.
        
        REM Método alternativo: modificar PATH del usuario
        echo 🔧 Agregando Python al PATH del usuario...
        setx PATH "%PATH%;%PYTHON_PATH%"
        if errorlevel 1 (
            echo ❌ Error agregando Python al PATH del usuario
            echo.
            echo 🔧 Método manual requerido:
            echo 1. Presiona Win + R
            echo 2. Escribe: sysdm.cpl
            echo 3. Ve a: Avanzado -^> Variables de entorno
            echo 4. En "Variables del sistema", busca "Path"
            echo 5. Agrega: %PYTHON_PATH%
            echo.
            pause
            exit /b 1
        ) else (
            echo ✅ Python agregado al PATH del usuario
        )
    ) else (
        echo ✅ Python agregado al PATH del sistema
    )

    echo.
    echo 🔧 Agregando Scripts al PATH...
    if exist "%PYTHON_PATH%\Scripts" (
        setx PATH "%PATH%;%PYTHON_PATH%\Scripts" /M
        if not errorlevel 1 (
            echo ✅ Scripts de Python agregados al PATH
        ) else (
            echo ⚠️  No se pudieron agregar los Scripts al PATH
        )
    )

    echo.
    echo 🔄 Reiniciando variables de entorno...
    call refreshenv >nul 2>&1

    echo.
    echo 🧪 Probando Python desde PATH...
    echo.

    REM Probar Python
    python --version >nul 2>&1
    if not errorlevel 1 (
        set PYTHON_CMD=python
        echo ✅ Python funciona correctamente desde PATH
    ) else (
        echo ❌ Python aún no funciona desde PATH
        echo.
        echo 🔧 Solución manual requerida:
        echo 1. Reinicia la consola/terminal
        echo 2. O reinicia el explorador de Windows
        echo 3. O reinicia la computadora
        echo.
        echo 📋 Ruta de Python: %PYTHON_PATH%
        echo.
        pause
        exit /b 1
    )
)

:python_working
echo.
echo 🎉 ¡Python está funcionando correctamente!
echo 📋 Comando: %PYTHON_CMD%
echo 📋 Versión: %PYTHON_VERSION%
echo.

REM ========================================
REM    📥 INSTALACIÓN DEL PROGRAMA
REM ========================================

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
echo 🔁 Sincronizando archivo local actualizado (si existe)...
REM Copiar el .py local del instalador dentro del repo extraído antes de compilar
set LOCAL_DIR=%~dp0
if exist "%LOCAL_DIR%youtube_360_downloader.py" (
    copy "%LOCAL_DIR%youtube_360_downloader.py" "youtube_360_downloader.py" /Y >nul
    echo ✅ Archivo youtube_360_downloader.py actualizado desde el instalador
) else (
    echo ℹ️ No se encontró una versión local para sobrescribir; se usará la del repositorio
)

echo.
echo 📦 Instalando/actualizando dependencias...
echo 🔧 Usando: %PYTHON_CMD% -m pip install --upgrade -r requirements.txt
%PYTHON_CMD% -m pip install --upgrade -r requirements.txt
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

echo ✅ Dependencias instaladas/actualizadas
echo.
echo 🔄 Asegurando la última yt-dlp (cambios recientes de YouTube)...
%PYTHON_CMD% -m pip install --upgrade yt-dlp
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
echo 📁 Moviendo ejecutable al directorio del instalador...
cd ..

REM Directorio del instalador (misma ruta que este .bat)
set DEST_DIR=%~dp0

REM Copiar archivos importantes desde la carpeta extraída
for /d %%i in (K-YoutubeVideoDownloaderHD-*) do (
    if exist "%%i\dist\YouTubeUltraHDDownloader.exe" copy "%%i\dist\YouTubeUltraHDDownloader.exe" "%DEST_DIR%" /Y
    if exist "%%i\youtube_360_downloader.py" copy "%%i\youtube_360_downloader.py" "%DEST_DIR%" /Y
    if exist "%%i\requirements.txt" copy "%%i\requirements.txt" "%DEST_DIR%" /Y
    if exist "%%i\README.md" copy "%%i\README.md" "%DEST_DIR%" /Y
)

REM ========================================
REM     🎬 FFmpeg (para fusionar video+audio)
REM ========================================
echo.
echo 🔎 Comprobando FFmpeg...
set BIN_DIR=%DEST_DIR%bin
if not exist "%BIN_DIR%" mkdir "%BIN_DIR%"

set FF_EXE=%BIN_DIR%ffmpeg.exe
set FP_EXE=%BIN_DIR%ffprobe.exe

if exist "%FF_EXE%" (
    if exist "%FP_EXE%" (
        echo ✅ FFmpeg ya está presente en: %BIN_DIR%
        goto :ffmpeg_done
    )
)

echo ⚙️  Intentando instalar FFmpeg con winget (si está disponible)...
where winget >nul 2>&1
if not errorlevel 1 (
    winget install --id FFmpeg.FFmpeg -e --source winget --accept-source-agreements --accept-package-agreements
)

REM Tras winget, si ffmpeg está en PATH, no necesitamos portable
where ffmpeg >nul 2>&1
if not errorlevel 1 (
    echo ✅ FFmpeg instalado en el sistema (PATH). Se usará automáticamente si es necesario.
    goto :ffmpeg_done
)

echo 📥 Descargando FFmpeg portable (essentials)...
set FFMPEG_ZIP=ffmpeg-release-essentials.zip
powershell -Command "try { Invoke-WebRequest -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile '%FFMPEG_ZIP%' -UseBasicParsing; Write-Host '✅ Descarga FFmpeg completada' } catch { Write-Host '❌ Error descargando FFmpeg: ' $_.Exception.Message }"

if exist "%FFMPEG_ZIP%" (
    echo 📦 Extrayendo FFmpeg...
    rmdir /s /q ffmpeg_tmp >nul 2>&1
    mkdir ffmpeg_tmp
    powershell -Command "try { Expand-Archive -Path '%FFMPEG_ZIP%' -DestinationPath 'ffmpeg_tmp' -Force; Write-Host '✅ Extracción FFmpeg completada' } catch { Write-Host '❌ Error extrayendo FFmpeg: ' $_.Exception.Message }"

    for /d %%j in (ffmpeg_tmp\ffmpeg-*) do (
        if exist "%%j\bin\ffmpeg.exe" copy "%%j\bin\ffmpeg.exe" "%FF_EXE%" /Y
        if exist "%%j\bin\ffprobe.exe" copy "%%j\bin\ffprobe.exe" "%FP_EXE%" /Y
    )

    if exist "%FF_EXE%" (
        echo ✅ FFmpeg copiado a: %FF_EXE%
    ) else (
        echo ⚠️  No se pudo ubicar ffmpeg.exe en el ZIP
    )

    if exist "%FP_EXE%" (
        echo ✅ FFprobe copiado a: %FP_EXE%
    ) else (
        echo ⚠️  No se pudo ubicar ffprobe.exe en el ZIP
    )

    del "%FFMPEG_ZIP%" >nul 2>&1
    rmdir /s /q ffmpeg_tmp >nul 2>&1
) else (
    echo ❌ No se pudo descargar FFmpeg portable.
)

:ffmpeg_done

echo.
echo 🧹 Limpieza final...
rmdir /s /q K-YoutubeVideoDownloaderHD-*

echo.
echo 🎉 ¡PROGRAMA LISTO PARA USAR!
echo ========================================
echo.
echo 📁 Ejecutable en: %DEST_DIR%YouTubeUltraHDDownloader.exe
echo.
if exist "%DEST_DIR%YouTubeUltraHDDownloader.exe" (
    echo ✅ YouTubeUltraHDDownloader.exe (Ejecutable)
    echo 🚀 Doble clic para ejecutar desde esta misma carpeta
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
