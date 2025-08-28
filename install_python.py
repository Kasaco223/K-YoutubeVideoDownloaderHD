#!/usr/bin/env python3
"""
Script para ayudar a instalar Python en Windows
"""

import os
import sys
import subprocess
import webbrowser
import platform

def check_python():
    """Verifica si Python está instalado"""
    try:
        result = subprocess.run(['python', '--version'], 
                              capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            print(f"✅ Python ya está instalado: {result.stdout.strip()}")
            return True
    except:
        pass
    
    try:
        result = subprocess.run(['python3', '--version'], 
                              capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            print(f"✅ Python3 ya está instalado: {result.stdout.strip()}")
            return True
    except:
        pass
    
    return False

def check_pip():
    """Verifica si pip está disponible"""
    try:
        result = subprocess.run(['pip', '--version'], 
                              capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            print(f"✅ pip está disponible: {result.stdout.strip()}")
            return True
    except:
        pass
    
    try:
        result = subprocess.run(['pip3', '--version'], 
                              capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            print(f"✅ pip3 está disponible: {result.stdout.strip()}")
            return True
    except:
        pass
    
    return False

def main():
    """Función principal"""
    print("🐍 Verificador de Python para Windows")
    print("=" * 40)
    
    # Verificar sistema operativo
    if platform.system() != 'Windows':
        print("❌ Este script es solo para Windows")
        return
    
    print(f"🖥️  Sistema operativo: {platform.system()} {platform.release()}")
    
    # Verificar Python
    if check_python():
        print("\n🎉 ¡Python ya está instalado!")
        
        if check_pip():
            print("\n🚀 ¡Todo listo! Puedes ejecutar la aplicación:")
            print("   python youtube_360_downloader.py")
            return
        else:
            print("\n⚠️  Python está instalado pero pip no está disponible")
            print("   Esto puede indicar una instalación incompleta")
    else:
        print("\n❌ Python no está instalado")
    
    # Opciones de instalación
    print("\n📥 Opciones para instalar Python:")
    print("1. Microsoft Store (más fácil)")
    print("2. Descarga directa desde python.org (recomendado)")
    print("3. Ver tutorial de instalación")
    
    try:
        choice = input("\nElige una opción (1-3) o presiona Enter para salir: ").strip()
        
        if choice == "1":
            print("\n🔄 Abriendo Microsoft Store...")
            webbrowser.open("ms-windows-store://pdp/?ProductId=9NRWMJP3717K")
            print("✅ Microsoft Store abierto. Busca 'Python 3.11' e instálalo")
            
        elif choice == "2":
            print("\n🌐 Abriendo python.org...")
            webbrowser.open("https://python.org/downloads")
            print("✅ Página de descarga abierta")
            print("📋 IMPORTANTE: Marca 'Add Python to PATH' durante la instalación")
            
        elif choice == "3":
            print("\n📚 Abriendo tutorial...")
            webbrowser.open("https://docs.python.org/3/using/windows.html")
            print("✅ Tutorial abierto")
            
        else:
            print("\n👋 ¡Hasta luego!")
            return
            
    except KeyboardInterrupt:
        print("\n\n👋 Instalación cancelada")
        return
    
    print("\n📋 Pasos después de instalar Python:")
    print("1. Reinicia la terminal/PowerShell")
    print("2. Ejecuta: python --version")
    print("3. Ejecuta: pip --version")
    print("4. Vuelve a esta carpeta y ejecuta: python install.py")
    print("\n✨ ¡Después de instalar Python podrás usar la aplicación!")

if __name__ == "__main__":
    main()
