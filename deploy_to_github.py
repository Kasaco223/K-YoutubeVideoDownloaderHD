#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de despliegue automático para GitHub
Sube todos los archivos del proyecto al repositorio
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(command, description):
    """Ejecuta un comando y maneja errores"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completado")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en {description}: {e}")
        if e.stderr:
            print(f"   Error: {e.stderr}")
        return False

def check_git_status():
    """Verifica el estado de git"""
    print("🔍 Verificando estado de Git...")
    
    # Verificar si es un repositorio git
    if not os.path.exists(".git"):
        print("❌ No es un repositorio Git")
        print("   Ejecuta: git init")
        return False
    
    # Verificar estado
    try:
        result = subprocess.run("git status", shell=True, capture_output=True, text=True)
        print("✅ Repositorio Git detectado")
        print(f"   {result.stdout}")
        return True
    except Exception as e:
        print(f"❌ Error verificando estado: {e}")
        return False

def setup_git_repo():
    """Configura el repositorio Git"""
    print("🔧 Configurando repositorio Git...")
    
    # Inicializar si no existe
    if not os.path.exists(".git"):
        if not run_command("git init", "Inicializando repositorio Git"):
            return False
    
    # Configurar remoto
    remote_url = "https://github.com/Kasaco223/K-YoutubeVideoDownloaderHD.git"
    
    # Verificar si ya existe el remoto
    try:
        result = subprocess.run("git remote -v", shell=True, capture_output=True, text=True)
        if remote_url not in result.stdout:
            if not run_command(f'git remote add origin {remote_url}', "Agregando remoto"):
                return False
        else:
            print("✅ Remoto ya configurado")
    except Exception as e:
        print(f"❌ Error configurando remoto: {e}")
        return False
    
    return True

def add_files():
    """Agrega todos los archivos al staging"""
    print("📁 Agregando archivos...")
    
    # Agregar todos los archivos
    if not run_command("git add .", "Agregando archivos al staging"):
        return False
    
    # Verificar qué se agregó
    try:
        result = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True)
        if result.stdout.strip():
            print("📋 Archivos agregados:")
            for line in result.stdout.strip().split('\n'):
                if line:
                    print(f"   {line}")
        else:
            print("ℹ️  No hay cambios para commitear")
    except Exception as e:
        print(f"⚠️  No se pudo verificar archivos: {e}")
    
    return True

def commit_changes():
    """Hace commit de los cambios"""
    print("💾 Haciendo commit...")
    
    commit_message = "🚀 Actualización completa: Interfaz moderna, instalador automático y documentación"
    
    if not run_command(f'git commit -m "{commit_message}"', "Haciendo commit"):
        return False
    
    return True

def push_to_github():
    """Sube los cambios a GitHub"""
    print("🚀 Subiendo a GitHub...")
    
    # Intentar push
    if not run_command("git push -u origin main", "Subiendo a rama main"):
        # Si falla, intentar con master
        print("⚠️  Falló con main, intentando con master...")
        if not run_command("git push -u origin master", "Subiendo a rama master"):
            return False
    
    return True

def create_release_notes():
    """Crea notas de release"""
    print("📝 Creando notas de release...")
    
    release_notes = """# 🎉 Release v1.0.0 - YouTube Ultra HD Video Downloader

## ✨ Nuevas Características

### 🎨 **Interfaz Moderna**
- Diseño oscuro inspirado en Nea Studio
- Colores contemporáneos con acentos púrpura
- Efectos hover en botones
- Progressbar animado personalizado
- Scroll vertical para navegación fluida

### 🚀 **Funcionalidades Avanzadas**
- Soporte para calidad hasta 4K 60fps
- Descarga directa sin verificación previa
- Fallback automático a la mejor calidad disponible
- Nombres de archivo con formato colombiano
- Solo descarga videos individuales (no playlists)

### 🔧 **Instalador Automático**
- Instalación automática de dependencias
- Creación de ejecutable (.exe en Windows)
- Acceso directo en el escritorio
- Archivo .bat para ejecución rápida

### 📚 **Documentación Completa**
- README atractivo y detallado
- Guía de instalación paso a paso
- Solución de problemas comunes
- Script de pruebas del sistema

## 🛠️ **Instalación**

### Opción 1: Instalador Automático (Recomendado)
```bash
python installer.py
```

### Opción 2: Instalación Manual
```bash
pip install -r requirements.txt
python youtube_360_downloader.py
```

## 🎯 **Cómo Usar**

1. **Pegar URL** del video de YouTube
2. **Seleccionar calidad** deseada
3. **Elegir carpeta** de destino
4. **¡Descargar!** con un clic

## 🔧 **Requisitos**

- Python 3.8+
- Windows 10/11, macOS 10.15+, Ubuntu 18.04+
- Conexión a Internet

## 🚨 **Cambios Importantes**

- ✅ Interfaz completamente rediseñada
- ✅ Sistema de descarga simplificado
- ✅ Instalador automático incluido
- ✅ Documentación completa en español
- ✅ Soporte multiplataforma mejorado

## 🙏 **Agradecimientos**

- **yt-dlp** - Motor de descarga
- **Nea Studio** - Inspiración del diseño
- **Python Community** - Librerías y herramientas

---

**¡Disfruta descargando videos en Ultra HD! 🎬✨**
"""
    
    with open("RELEASE_NOTES.md", "w", encoding="utf-8") as f:
        f.write(release_notes)
    
    print("✅ Notas de release creadas: RELEASE_NOTES.md")
    return True

def main():
    """Función principal"""
    print("=" * 60)
    print("🚀 DESPLIEGUE AUTOMÁTICO A GITHUB")
    print("YouTube Ultra HD Video Downloader")
    print("=" * 60)
    print()
    
    # Verificar que estamos en el directorio correcto
    if not os.path.exists("youtube_360_downloader.py"):
        print("❌ Error: No se encontró youtube_360_downloader.py")
        print("   Asegúrate de estar en el directorio del proyecto")
        return False
    
    # Paso 1: Verificar estado de Git
    if not check_git_status():
        print("❌ No se pudo verificar el estado de Git")
        return False
    
    # Paso 2: Configurar repositorio
    if not setup_git_repo():
        print("❌ No se pudo configurar el repositorio")
        return False
    
    # Paso 3: Agregar archivos
    if not add_files():
        print("❌ No se pudieron agregar archivos")
        return False
    
    # Paso 4: Hacer commit
    if not commit_changes():
        print("❌ No se pudo hacer commit")
        return False
    
    # Paso 5: Subir a GitHub
    if not push_to_github():
        print("❌ No se pudo subir a GitHub")
        return False
    
    # Paso 6: Crear notas de release
    create_release_notes()
    
    print("\n" + "=" * 60)
    print("🎉 ¡DESPLIEGUE COMPLETADO EXITOSAMENTE!")
    print("✅ El proyecto está ahora en GitHub")
    print("=" * 60)
    
    print("\n📋 Archivos incluidos:")
    files_to_show = [
        "youtube_360_downloader.py",
        "installer.py",
        "requirements.txt",
        "README.md",
        "LICENSE",
        ".gitignore",
        "build_config.spec",
        "test_program.py",
        "instalar_rapido.bat"
    ]
    
    for file in files_to_show:
        if os.path.exists(file):
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file} (no encontrado)")
    
    print(f"\n🌐 Repositorio: https://github.com/Kasaco223/K-YoutubeVideoDownloaderHD")
    print("📖 README: https://github.com/Kasaco223/K-YoutubeVideoDownloaderHD#readme")
    
    input("\nPresiona Enter para salir...")
    return True

if __name__ == "__main__":
    main()
