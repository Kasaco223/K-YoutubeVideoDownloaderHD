#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de prueba para YouTube Ultra HD Video Downloader
Verifica que todas las dependencias estén funcionando correctamente
"""

import sys
import os

def test_imports():
    """Prueba que todas las importaciones funcionen"""
    print("🔍 Probando importaciones...")
    
    try:
        import tkinter as tk
        print("✅ tkinter - OK")
    except ImportError as e:
        print(f"❌ tkinter - Error: {e}")
        return False
    
    try:
        from tkinter import ttk, filedialog, messagebox
        print("✅ tkinter.ttk, filedialog, messagebox - OK")
    except ImportError as e:
        print(f"❌ tkinter.ttk, filedialog, messagebox - Error: {e}")
        return False
    
    try:
        import threading
        print("✅ threading - OK")
    except ImportError as e:
        print(f"❌ threading - Error: {e}")
        return False
    
    try:
        import yt_dlp
        print("✅ yt-dlp - OK")
    except ImportError as e:
        print(f"❌ yt-dlp - Error: {e}")
        return False
    
    try:
        from PIL import Image, ImageTk
        print("✅ Pillow (PIL) - OK")
    except ImportError as e:
        print(f"❌ Pillow (PIL) - Error: {e}")
        return False
    
    try:
        import requests
        print("✅ requests - OK")
    except ImportError as e:
        print(f"❌ requests - Error: {e}")
        return False
    
    try:
        import pytz
        print("✅ pytz - OK")
    except ImportError as e:
        print(f"❌ pytz - Error: {e}")
        return False
    
    try:
        from datetime import datetime
        print("✅ datetime - OK")
    except ImportError as e:
        print(f"❌ datetime - Error: {e}")
        return False
    
    return True

def test_basic_functionality():
    """Prueba funcionalidades básicas"""
    print("\n🔧 Probando funcionalidades básicas...")
    
    try:
        # Probar creación de ventana básica
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()  # Ocultar ventana
        
        # Probar creación de variables
        from tkinter import StringVar
        test_var = StringVar(value="test")
        print("✅ Creación de variables tkinter - OK")
        
        # Probar datetime colombiano
        from datetime import datetime
        import pytz
        try:
            colombia_tz = pytz.timezone('America/Bogota')
            now = datetime.now(colombia_tz)
            formatted = now.strftime("%Y%m%d_%H%M%S")
            print(f"✅ Fecha colombiana: {formatted} - OK")
        except Exception as e:
            print(f"⚠️  Fecha colombiana - Fallback: {e}")
        
        root.destroy()
        return True
        
    except Exception as e:
        print(f"❌ Funcionalidades básicas - Error: {e}")
        return False

def test_yt_dlp():
    """Prueba yt-dlp básico"""
    print("\n📹 Probando yt-dlp...")
    
    try:
        import yt_dlp
        
        # Crear instancia básica
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True
        }
        
        ydl = yt_dlp.YoutubeDL(ydl_opts)
        print("✅ Instancia yt-dlp creada - OK")
        
        return True
        
    except Exception as e:
        print(f"❌ yt-dlp - Error: {e}")
        return False

def test_pillow():
    """Prueba Pillow básico"""
    print("\n🎨 Probando Pillow...")
    
    try:
        from PIL import Image, ImageDraw
        
        # Crear imagen básica
        img = Image.new('RGBA', (100, 100), (99, 102, 241, 255))
        draw = ImageDraw.Draw(img)
        draw.ellipse([10, 10, 90, 90], fill=(255, 255, 255, 255))
        
        # Guardar temporalmente
        temp_path = "test_icon.png"
        img.save(temp_path)
        
        # Verificar que se creó
        if os.path.exists(temp_path):
            os.remove(temp_path)
            print("✅ Creación y guardado de imagen - OK")
        else:
            print("❌ No se pudo crear imagen de prueba")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Pillow - Error: {e}")
        return False

def main():
    """Función principal de pruebas"""
    print("=" * 60)
    print("🧪 PRUEBAS DEL SISTEMA")
    print("YouTube Ultra HD Video Downloader")
    print("=" * 60)
    print()
    
    all_tests_passed = True
    
    # Prueba 1: Importaciones
    if not test_imports():
        all_tests_passed = False
    
    # Prueba 2: Funcionalidades básicas
    if not test_basic_functionality():
        all_tests_passed = False
    
    # Prueba 3: yt-dlp
    if not test_yt_dlp():
        all_tests_passed = False
    
    # Prueba 4: Pillow
    if not test_pillow():
        all_tests_passed = False
    
    print("\n" + "=" * 60)
    
    if all_tests_passed:
        print("🎉 ¡TODAS LAS PRUEBAS PASARON!")
        print("✅ El sistema está listo para funcionar")
        print("\n🚀 Puedes ejecutar el programa principal:")
        print("   python youtube_360_downloader.py")
    else:
        print("❌ ALGUNAS PRUEBAS FALLARON")
        print("⚠️  Revisa los errores arriba")
        print("\n🔧 Ejecuta el instalador para corregir problemas:")
        print("   python installer.py")
    
    print("=" * 60)
    
    input("\nPresiona Enter para salir...")

if __name__ == "__main__":
    main()
