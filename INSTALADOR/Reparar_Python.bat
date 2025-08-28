@echo off
title Reparar Python - Agregar al PATH
color 0C

echo.
echo ========================================
echo    🔧 REPARAR PYTHON
echo    Agregar Python al PATH del sistema
echo ========================================
echo.

echo 🔍 Buscando Python instalado en el sistema...
echo.

set PYTHON_FOUND=
set PYTHON_PATH=
set PYTHON_VERSION=

REM Buscar Python en ubicaciones comunes
echo 📁 Buscando en ubicaciones comunes...
echo.

REM Buscar en Program Files
if exist "C:\Program Files\Python*" (
    for /d %%i in ("C:\Program Files\Python*") do (
        if exist "%%i\python.exe" (
            set PYTHON_FOUND=1
            set PYTHON_PATH=%%i
            echo ✅ Python encontrado en: %%i
            goto :found_python
        )
    )
)

REM Buscar en Program Files (x86)
if exist "C:\Program Files (x86)\Python*" (
    for /d %%i in ("C:\Program Files (x86)\Python*") do (
        if exist "%%i\python.exe" (
            set PYTHON_FOUND=1
            set PYTHON_PATH=%%i
            echo ✅ Python encontrado en: %%i
            goto :found_python
        )
    )
)

REM Buscar en AppData (instalación de usuario)
if exist "%LOCALAPPDATA%\Programs\Python*" (
    for /d %%i in ("%LOCALAPPDATA%\Programs\Python*") do (
        if exist "%%i\python.exe" (
            set PYTHON_FOUND=1
            set PYTHON_PATH=%%i
            echo ✅ Python encontrado en: %%i
            goto :found_python
        )
    )
)

REM Buscar en directorio de usuario
if exist "%USERPROFILE%\AppData\Local\Programs\Python*" (
    for /d %%i in ("%USERPROFILE%\AppData\Local\Programs\Python*") do (
        if exist "%%i\python.exe" (
            set PYTHON_FOUND=1
            set PYTHON_PATH=%%i
            echo ✅ Python encontrado en: %%i
            goto :found_python
        )
    )
)

REM Buscar en directorio raíz de usuario
if exist "%USERPROFILE%\Python*" (
    for /d %%i in ("%USERPROFILE%\Python*") do (
        if exist "%%i\python.exe" (
            set PYTHON_FOUND=1
            set PYTHON_PATH=%%i
            echo ✅ Python encontrado en: %%i
            goto :found_python
        )
    )
)

:python_not_found
echo ❌ No se encontró Python instalado en ubicaciones comunes
echo.
echo 🔧 Soluciones:
echo 1. Instalar Python desde python.org
echo 2. Verificar que Python esté instalado
echo 3. Ejecutar este script como administrador
echo.
pause
exit /b 1

:found_python
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

echo.
echo 🔧 Verificando si Python ya está en PATH...
echo %PATH% | findstr /i "%PYTHON_PATH%" >nul
if not errorlevel 1 (
    echo ✅ Python ya está en PATH
    echo.
    echo 🚀 Probando Python...
    python --version >nul 2>&1
    if not errorlevel 1 (
        echo ✅ Python funciona correctamente desde PATH
        echo.
        echo 🎉 ¡No se necesitan más cambios!
        echo Puedes ejecutar el instalador principal ahora.
        echo.
        pause
        exit /b 0
    ) else (
        echo ❌ Python está en PATH pero no funciona
        echo Continuando con la reparación...
    )
) else (
    echo ❌ Python NO está en PATH
    echo Continuando con la reparación...
)

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
    echo ✅ Python funciona correctamente desde PATH
    echo.
    echo 🎉 ¡Python reparado exitosamente!
    echo.
    echo 📋 Resumen:
    echo - Python encontrado en: %PYTHON_PATH%
    echo - Versión: %PYTHON_VERSION%
    echo - Agregado al PATH del sistema
    echo.
    echo 🚀 Ahora puedes ejecutar el instalador principal
    echo.
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
)

echo.
echo 🔍 Para verificar manualmente:
echo 1. Abre una NUEVA consola
echo 2. Ejecuta: python --version
echo 3. Si funciona, ejecuta el instalador principal
echo.

pause
