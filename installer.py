#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Instalador Automático para YouTube Ultra HD Video Downloader
Descarga todas las dependencias necesarias y crea un ejecutable
"""

import os
import sys
import subprocess
import platform
import urllib.request
import zipfile
import tarfile
import shutil
from pathlib import Path

class YouTubeDownloaderInstaller:
    def __init__(self):
        self.system = platform.system().lower()
        self.is_windows = self.system == "windows"
        self.is_macos = self.system == "darwin"
        self.is_linux = self.system == "linux"
        
        # Colores para la consola
        self.colors = {
            'reset': '\033[0m',
            'bold': '\033[1m',
            'red': '\033[91m',
            'green': '\033[92m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'purple': '\033[95m',
            'cyan': '\033[96m'
        }
        
        # Directorio del proyecto
        self.project_dir = Path(__file__).parent
        self.requirements_file = self.project_dir / "requirements.txt"
        
    def print_colored(self, text, color='reset'):
        """Imprime texto con color"""
        if self.is_windows:
            print(text)
        else:
            print(f"{self.colors.get(color, '')}{text}{self.colors['reset']}")
    
    def print_header(self):
        """Imprime el encabezado del instalador"""
        self.print_colored("=" * 60, 'cyan')
        self.print_colored("🚀 INSTALADOR AUTOMÁTICO", 'bold')
        self.print_colored("YouTube Ultra HD Video Downloader", 'purple')
        self.print_colored("=" * 60, 'cyan')
        print()
    
    def check_python_version(self):
        """Verifica la versión de Python"""
        self.print_colored("🔍 Verificando versión de Python...", 'blue')
        
        if sys.version_info < (3, 8):
            self.print_colored("❌ Error: Se requiere Python 3.8 o superior", 'red')
            self.print_colored(f"   Versión actual: {sys.version}", 'red')
            return False
        
        self.print_colored(f"✅ Python {sys.version.split()[0]} detectado", 'green')
        return True
    
    def create_requirements_file(self):
        """Crea el archivo requirements.txt"""
        self.print_colored("📝 Creando archivo requirements.txt...", 'blue')
        
        requirements = [
            "yt-dlp>=2023.12.30",
            "Pillow>=10.0.0",
            "requests>=2.31.0",
            "pytz>=2023.3"
        ]
        
        with open(self.requirements_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(requirements))
        
        self.print_colored("✅ Archivo requirements.txt creado", 'green')
    
    def install_dependencies(self):
        """Instala las dependencias de Python"""
        self.print_colored("📦 Instalando dependencias...", 'blue')
        
        try:
            # Actualizar pip
            self.print_colored("   🔄 Actualizando pip...", 'yellow')
            subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], 
                         check=True, capture_output=True)
            
            # Instalar dependencias
            self.print_colored("   📥 Instalando paquetes...", 'yellow')
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(self.requirements_file)], 
                         check=True, capture_output=True)
            
            self.print_colored("✅ Dependencias instaladas correctamente", 'green')
            return True
            
        except subprocess.CalledProcessError as e:
            self.print_colored(f"❌ Error instalando dependencias: {e}", 'red')
            return False
    
    def install_pyinstaller(self):
        """Instala PyInstaller para crear el ejecutable"""
        self.print_colored("🔧 Instalando PyInstaller...", 'blue')
        
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], 
                         check=True, capture_output=True)
            self.print_colored("✅ PyInstaller instalado correctamente", 'green')
            return True
            
        except subprocess.CalledProcessError as e:
            self.print_colored(f"❌ Error instalando PyInstaller: {e}", 'red')
            return False
    
    def create_executable(self):
        """Crea el ejecutable del programa"""
        self.print_colored("⚙️ Creando ejecutable...", 'blue')
        
        try:
            # Configuración de PyInstaller
            pyinstaller_cmd = [
                sys.executable, "-m", "PyInstaller",
                "--onefile",  # Un solo archivo ejecutable
                "--windowed",  # Sin consola (solo en Windows)
                "--name=YouTubeUltraHDDownloader",  # Nombre del ejecutable
                "--icon=icon.ico" if self.is_windows else "",  # Icono (solo Windows)
                "youtube_360_downloader.py"
            ]
            
            # Filtrar argumentos vacíos
            pyinstaller_cmd = [arg for arg in pyinstaller_cmd if arg]
            
            self.print_colored("   🔨 Compilando...", 'yellow')
            subprocess.run(pyinstaller_cmd, check=True, capture_output=True)
            
            # Verificar que se creó el ejecutable
            dist_dir = self.project_dir / "dist"
            if dist_dir.exists():
                executable_name = "YouTubeUltraHDDownloader.exe" if self.is_windows else "YouTubeUltraHDDownloader"
                executable_path = dist_dir / executable_name
                
                if executable_path.exists():
                    self.print_colored(f"✅ Ejecutable creado: {executable_path}", 'green')
                    return True
                else:
                    self.print_colored("❌ No se pudo encontrar el ejecutable", 'red')
                    return False
            else:
                self.print_colored("❌ No se creó el directorio dist", 'red')
                return False
                
        except subprocess.CalledProcessError as e:
            self.print_colored(f"❌ Error creando ejecutable: {e}", 'red')
            return False
    
    def create_icon(self):
        """Crea un icono básico para la aplicación"""
        if not self.is_windows:
            return
        
        self.print_colored("🎨 Creando icono básico...", 'blue')
        
        try:
            # Crear un icono simple usando Pillow
            from PIL import Image, ImageDraw
            
            # Crear imagen 256x256
            size = 256
            img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Dibujar un círculo con el color principal
            margin = 20
            draw.ellipse([margin, margin, size-margin, size-margin], 
                        fill=(99, 102, 241, 255))  # #6366f1
            
            # Guardar como ICO
            icon_path = self.project_dir / "icon.ico"
            img.save(icon_path, format='ICO', sizes=[(256, 256)])
            
            self.print_colored("✅ Icono creado: icon.ico", 'green')
            
        except Exception as e:
            self.print_colored(f"⚠️ No se pudo crear el icono: {e}", 'yellow')
    
    def create_shortcut(self):
        """Crea un acceso directo en el escritorio"""
        if not self.is_windows:
            return
        
        self.print_colored("🔗 Creando acceso directo...", 'blue')
        
        try:
            import winshell
            from win32com.client import Dispatch
            
            desktop = winshell.desktop()
            shortcut_path = os.path.join(desktop, "YouTube Ultra HD Downloader.lnk")
            
            executable_path = self.project_dir / "dist" / "YouTubeUltraHDDownloader.exe"
            
            if executable_path.exists():
                shell = Dispatch('WScript.Shell')
                shortcut = shell.CreateShortCut(shortcut_path)
                shortcut.Targetpath = str(executable_path)
                shortcut.WorkingDirectory = str(self.project_dir)
                shortcut.IconLocation = str(executable_path)
                shortcut.save()
                
                self.print_colored("✅ Acceso directo creado en el escritorio", 'green')
            else:
                self.print_colored("⚠️ No se pudo crear el acceso directo", 'yellow')
                
        except Exception as e:
            self.print_colored(f"⚠️ No se pudo crear el acceso directo: {e}", 'yellow')
    
    def create_batch_file(self):
        """Crea un archivo .bat para ejecutar el programa"""
        self.print_colored("📄 Creando archivo de ejecución...", 'blue')
        
        try:
            batch_content = f"""@echo off
title YouTube Ultra HD Video Downloader
echo Iniciando YouTube Ultra HD Video Downloader...
echo.

REM Cambiar al directorio del proyecto
cd /d "{self.project_dir}"

REM Ejecutar el programa
python youtube_360_downloader.py

REM Pausar para ver cualquier error
pause
"""
            
            batch_path = self.project_dir / "ejecutar_programa.bat"
            with open(batch_path, 'w', encoding='utf-8') as f:
                f.write(batch_content)
            
            self.print_colored("✅ Archivo ejecutar_programa.bat creado", 'green')
            
        except Exception as e:
            self.print_colored(f"❌ Error creando archivo .bat: {e}", 'red')
    
    def cleanup(self):
        """Limpia archivos temporales"""
        self.print_colored("🧹 Limpiando archivos temporales...", 'blue')
        
        try:
            # Eliminar directorios de PyInstaller
            build_dir = self.project_dir / "build"
            if build_dir.exists():
                shutil.rmtree(build_dir)
            
            # Eliminar archivo .spec
            spec_file = self.project_dir / "YouTubeUltraHDDownloader.spec"
            if spec_file.exists():
                spec_file.unlink()
            
            self.print_colored("✅ Limpieza completada", 'green')
            
        except Exception as e:
            self.print_colored(f"⚠️ Error durante la limpieza: {e}", 'yellow')
    
    def run(self):
        """Ejecuta el instalador completo"""
        self.print_header()
        
        # Verificar Python
        if not self.check_python_version():
            input("Presiona Enter para salir...")
            return False
        
        print()
        
        # Crear requirements.txt
        self.create_requirements_file()
        print()
        
        # Instalar dependencias
        if not self.install_dependencies():
            input("Presiona Enter para salir...")
            return False
        print()
        
        # Instalar PyInstaller
        if not self.install_pyinstaller():
            input("Presiona Enter para salir...")
            return False
        print()
        
        # Crear icono
        self.create_icon()
        print()
        
        # Crear ejecutable
        if not self.create_executable():
            input("Presiona Enter para salir...")
            return False
        print()
        
        # Crear acceso directo
        self.create_shortcut()
        print()
        
        # Crear archivo .bat
        self.create_batch_file()
        print()
        
        # Limpiar
        self.cleanup()
        print()
        
        # Mensaje final
        self.print_colored("🎉 ¡INSTALACIÓN COMPLETADA!", 'green')
        self.print_colored("=" * 60, 'cyan')
        self.print_colored("El programa está listo para usar:", 'bold')
        print()
        
        if self.is_windows:
            self.print_colored("• Ejecutable: dist/YouTubeUltraHDDownloader.exe", 'green')
            self.print_colored("• Acceso directo: Escritorio", 'green')
            self.print_colored("• Archivo .bat: ejecutar_programa.bat", 'green')
        else:
            self.print_colored("• Ejecutable: dist/YouTubeUltraHDDownloader", 'green')
            self.print_colored("• Archivo Python: youtube_360_downloader.py", 'green')
        
        print()
        self.print_colored("¡Disfruta descargando videos en Ultra HD!", 'purple')
        
        input("\nPresiona Enter para salir...")
        return True

def main():
    """Función principal"""
    installer = YouTubeDownloaderInstaller()
    installer.run()

if __name__ == "__main__":
    main()
