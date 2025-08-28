#!/usr/bin/env python3
"""
Script de instalación para YouTube 360° Video Downloader
"""

import subprocess
import sys
import os

def check_python_version():
    """Verifica que la versión de Python sea compatible"""
    if sys.version_info < (3, 7):
        print("❌ Error: Se requiere Python 3.7 o superior")
        print(f"   Versión actual: {sys.version}")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detectado")
    return True

def install_requirements():
    """Instala las dependencias requeridas"""
    print("\n📦 Instalando dependencias...")
    
    try:
        # Actualizar pip primero
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
        print("✅ pip actualizado")
        
        # Instalar dependencias
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencias instaladas correctamente")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error al instalar dependencias: {e}")
        return False
    except FileNotFoundError:
        print("❌ Error: No se encontró pip. Asegúrate de que Python esté instalado correctamente")
        return False

def test_installation():
    """Prueba que la instalación sea exitosa"""
    print("\n🧪 Probando instalación...")
    
    try:
        import yt_dlp
        print("✅ yt-dlp importado correctamente")
        
        import tkinter
        print("✅ tkinter disponible")
        
        from PIL import Image
        print("✅ Pillow importado correctamente")
        
        import requests
        print("✅ requests importado correctamente")
        
        return True
        
    except ImportError as e:
        print(f"❌ Error de importación: {e}")
        return False

def main():
    """Función principal de instalación"""
    print("🚀 Instalador de YouTube 360° Video Downloader")
    print("=" * 50)
    
    # Verificar versión de Python
    if not check_python_version():
        sys.exit(1)
    
    # Instalar dependencias
    if not install_requirements():
        print("\n❌ La instalación falló. Por favor, revisa los errores anteriores.")
        sys.exit(1)
    
    # Probar instalación
    if not test_installation():
        print("\n❌ La instalación no se completó correctamente.")
        sys.exit(1)
    
    print("\n🎉 ¡Instalación completada exitosamente!")
    print("\n📖 Para usar la aplicación:")
    print("   python youtube_360_downloader.py")
    print("\n📚 Lee el archivo README.md para más información")
    print("\n✨ ¡Disfruta descargando videos 360°!")

if __name__ == "__main__":
    main()
