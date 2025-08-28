@echo off
title Diagnóstico - Python y Dependencias
color 0E

echo.
echo ========================================
echo    🔍 DIAGNÓSTICO DEL SISTEMA
echo    Python y Dependencias
echo ========================================
echo.

echo 📋 Información del Sistema:
echo ===========================
echo.
echo 🖥️  Sistema Operativo:
ver
echo.
echo 📁 Directorio actual: %CD%
echo.

echo 🐍 Verificando Python:
echo ======================
echo.

REM Probar diferentes comandos de Python
echo 🔍 Probando 'python'...
python --version >nul 2>&1
if not errorlevel 1 (
    echo ✅ python: Disponible
    python --version
) else (
    echo ❌ python: No disponible
)

echo.
echo 🔍 Probando 'python3'...
python3 --version >nul 2>&1
if not errorlevel 1 (
    echo ✅ python3: Disponible
    python3 --version
) else (
    echo ❌ python3: No disponible
)

echo.
echo 🔍 Probando 'py'...
py --version >nul 2>&1
if not errorlevel 1 (
    echo ✅ py: Disponible
    py --version
) else (
    echo ❌ py: No disponible
)

echo.
echo 🔍 Probando 'python.exe'...
python.exe --version >nul 2>&1
if not errorlevel 1 (
    echo ✅ python.exe: Disponible
    python.exe --version
) else (
    echo ❌ python.exe: No disponible
)

echo.
echo 🔍 Verificando PATH:
echo ===================
echo.
echo %PATH%
echo.

echo 🔍 Verificando pip:
echo ==================
echo.

REM Probar pip con diferentes comandos
echo 🔍 Probando 'pip'...
pip --version >nul 2>&1
if not errorlevel 1 (
    echo ✅ pip: Disponible
    pip --version
) else (
    echo ❌ pip: No disponible
)

echo.
echo 🔍 Probando 'pip3'...
pip3 --version >nul 2>&1
if not errorlevel 1 (
    echo ✅ pip3: Disponible
    pip3 --version
) else (
    echo ❌ pip3: No disponible
)

echo.
echo 🔍 Probando 'python -m pip'...
python -m pip --version >nul 2>&1
if not errorlevel 1 (
    echo ✅ python -m pip: Disponible
    python -m pip --version
) else (
    echo ❌ python -m pip: No disponible
)

echo.
echo 🔍 Verificando dependencias:
echo ===========================
echo.

REM Verificar si requirements.txt existe
if exist "requirements.txt" (
    echo ✅ requirements.txt encontrado
    echo 📋 Contenido:
    type requirements.txt
) else (
    echo ❌ requirements.txt no encontrado
    echo 🔍 Buscando en directorios padres...
    if exist "..\requirements.txt" (
        echo ✅ requirements.txt encontrado en directorio padre
        echo 📋 Contenido:
        type "..\requirements.txt"
    ) else (
        echo ❌ requirements.txt no encontrado en directorios padres
    )
)

echo.
echo 🔍 Verificando espacio en disco:
echo ===============================
echo.
wmic logicaldisk get size,freespace,caption

echo.
echo 🔍 Verificando permisos:
echo ========================
echo.
whoami /groups | findstr "Administrators"

echo.
echo ========================================
echo    📊 RESUMEN DEL DIAGNÓSTICO
echo ========================================
echo.

REM Determinar el mejor comando de Python
set BEST_PYTHON=
if not errorlevel 1 (
    python --version >nul 2>&1
    if not errorlevel 1 (
        set BEST_PYTHON=python
        goto :summary
    )
)

python3 --version >nul 2>&1
if not errorlevel 1 (
    set BEST_PYTHON=python3
    goto :summary
)

py --version >nul 2>&1
if not errorlevel 1 (
    set BEST_PYTHON=py
    goto :summary
)

python.exe --version >nul 2>&1
if not errorlevel 1 (
    set BEST_PYTHON=python.exe
    goto :summary
)

:summary
if defined BEST_PYTHON (
    echo ✅ Python disponible: %BEST_PYTHON%
    echo 📋 Recomendación: Usar %BEST_PYTHON% para instalaciones
) else (
    echo ❌ Python no disponible
    echo 📋 Recomendación: Instalar Python 3.8+ desde python.org
)

echo.
echo 🔧 Soluciones comunes:
echo =====================
echo.
echo 1. Si Python no está en PATH:
echo    - Reinstalar Python marcando "Add Python to PATH"
echo    - Reiniciar la consola después de instalar
echo.
echo 2. Si pip no funciona:
echo    - Ejecutar: python -m ensurepip --upgrade
echo    - Usar: python -m pip en lugar de pip
echo.
echo 3. Si hay problemas de permisos:
echo    - Ejecutar como administrador
echo    - Usar: pip install --user
echo.
echo 4. Si hay problemas de espacio:
echo    - Liberar espacio en disco
echo    - Verificar que haya al menos 2GB libres
echo.

echo 📁 Archivo de diagnóstico guardado en: diagnostico.txt
echo.
echo 🔍 Para más ayuda, visita: https://github.com/Kasaco223/K-YoutubeVideoDownloaderHD
echo.

pause
