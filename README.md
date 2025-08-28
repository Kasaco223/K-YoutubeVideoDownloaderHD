# 🚀 YouTube Ultra HD Video Downloader

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)

**Descarga videos de YouTube en calidad Ultra HD hasta 4K 60fps con una interfaz moderna y elegante**

[![YouTube Ultra HD](https://img.shields.io/badge/YouTube-Ultra%20HD-red.svg)](https://github.com/Kasaco223/K-YoutubeVideoDownloaderHD)
[![4K Support](https://img.shields.io/badge/4K-Support-purple.svg)](https://github.com/Kasaco223/K-YoutubeVideoDownloaderHD)
[![360° Support](https://img.shields.io/badge/360°-Support-cyan.svg)](https://github.com/Kasaco223/K-YoutubeVideoDownloaderHD)

</div>

---

## ✨ Características Principales

### 🎬 **Calidad Ultra HD**
- **4K 60fps** - Máxima calidad disponible
- **4K estándar** - Resolución ultra alta
- **2K (1440p)** - Calidad muy alta
- **1080p, 720p, 480p, 360p** - Calidades estándar

### 🔄 **Sistema Inteligente**
- **Descarga directa** - Sin verificación previa
- **Fallback automático** - Si la calidad seleccionada no está disponible, descarga la mejor calidad posible
- **Sin playlists** - Solo descarga videos individuales
- **Nombres automáticos** - Formato colombiano: `K-YYYYMMDD_HHMMSS`

### 🎨 **Interfaz Moderna**
- **Diseño oscuro** inspirado en Nea Studio
- **Colores contemporáneos** con acentos púrpura
- **Efectos hover** en botones
- **Progressbar animado** personalizado
- **Scroll vertical** para navegación fluida

### 🚀 **Funcionalidades Avanzadas**
- **Detección automática** de características especiales (360°, 4K, 60fps)
- **Log detallado** de descargas
- **Selección de carpeta** de destino
- **Interfaz responsive** que se adapta al tamaño de ventana

---

## 🛠️ Instalación

### 📋 **Requisitos Previos**
- **Python 3.8** o superior
- **Conexión a Internet** para descargar dependencias

### 🚀 **Instalación Automática (Recomendada)**

#### **Opción 1: Instalador Completo (Solo 1 archivo)**
1. **Descarga solo este archivo**: [DESCARGAR_Y_USAR.bat](https://github.com/Kasaco223/K-YoutubeVideoDownloaderHD/raw/master/DESCARGAR_Y_USAR.bat)
2. **Ejecuta el archivo** con doble clic
3. **¡Listo!** El instalador descarga TODO automáticamente desde GitHub

#### **Opción 2: Instalador del Proyecto**
1. **Descarga el proyecto**
   ```bash
   git clone https://github.com/Kasaco223/K-YoutubeVideoDownloaderHD.git
   cd K-YoutubeVideoDownloaderHD
   ```

2. **Ejecuta el instalador automático**
   ```bash
   python installer.py
   ```

3. **¡Listo!** El instalador:
   - ✅ Descarga todas las dependencias
   - ✅ Crea un ejecutable (.exe en Windows)
   - ✅ Crea acceso directo en el escritorio
   - ✅ Genera archivo .bat para ejecución rápida

### 📦 **Instalación Manual**

1. **Instala las dependencias**
   ```bash
   pip install -r requirements.txt
   ```

2. **Ejecuta el programa**
   ```bash
   python youtube_360_downloader.py
   ```

---

## 🎯 **Cómo Usar**

### 1️⃣ **Pegar URL**
- Copia la URL del video de YouTube
- Pégalo en el campo "URL del Video"

### 2️⃣ **Seleccionar Calidad**
- Elige la calidad deseada de los botones disponibles
- **Recomendado**: 1080p para balance calidad/tamaño

### 3️⃣ **Elegir Destino**
- Selecciona la carpeta donde guardar el video
- **Por defecto**: Carpeta de Descargas

### 4️⃣ **¡Descargar!**
- Haz clic en "🚀 DESCARGAR VIDEO"
- El programa detectará automáticamente la mejor calidad disponible

---

## 🔧 **Configuración Avanzada**

### 📁 **Personalizar Nombres de Archivo**
Los archivos se guardan con el formato:
```
K-YYYYMMDD_HHMMSS.mp4
```

**Ejemplo**: `K-20241228_143052.mp4`

### 🎬 **Calidades Disponibles**
| Calidad | Resolución | FPS | Uso Recomendado |
|---------|------------|-----|------------------|
| 2160p60 | 4K | 60fps | Máxima calidad, archivos grandes |
| 2160p | 4K | 30fps | Alta calidad, archivos grandes |
| 1440p | 2K | 30fps | Muy alta calidad |
| 1080p | Full HD | 30fps | **Balance perfecto** |
| 720p | HD | 30fps | Calidad estándar |
| 480p | SD | 30fps | Archivos pequeños |
| 360p | SD | 30fps | Archivos muy pequeños |

---

## 🚨 **Solución de Problemas**

### ❌ **Error: "No se pudo obtener información del video"**
- **Verifica** que la URL sea válida
- **Asegúrate** de tener conexión a Internet
- **Comprueba** que el video no esté restringido por región

### ❌ **Error: "Dependencias no encontradas"**
- **Ejecuta** `python installer.py` para reinstalar
- **Verifica** que Python esté en el PATH del sistema

### ❌ **Error: "No se pudo crear ejecutable"**
- **Asegúrate** de tener permisos de administrador
- **Verifica** que haya espacio suficiente en disco
- **Reinstala** PyInstaller: `pip install --upgrade pyinstaller`

---

## 📱 **Compatibilidad**

### 🖥️ **Sistemas Operativos**
- ✅ **Windows 10/11** (Recomendado)
- ✅ **macOS 10.15+**
- ✅ **Ubuntu 18.04+**

### 🐍 **Versiones de Python**
- ✅ **Python 3.8+** (Recomendado: 3.11)
- ❌ **Python 3.7** o inferior

---

## 🎨 **Características de la Interfaz**

### 🌈 **Paleta de Colores**
- **Fondo principal**: `#0a0a0a` (Negro profundo)
- **Tarjetas**: `#1a1a1a` (Gris oscuro)
- **Elementos**: `#2a2a2a` (Gris medio)
- **Acentos**: `#6366f1` (Púrpura moderno)
- **Texto**: `#ffffff` (Blanco puro)

### 🔤 **Tipografía**
- **Título principal**: Segoe UI 32pt Bold
- **Subtítulos**: Segoe UI 16pt
- **Etiquetas**: Segoe UI 14pt Bold
- **Texto**: Segoe UI 12pt
- **Log**: Consolas 10pt

---

## 🤝 **Contribuir**

¡Tus contribuciones son bienvenidas! 

1. **Fork** el proyecto
2. **Crea** una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. **Commit** tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. **Push** a la rama (`git push origin feature/AmazingFeature`)
5. **Abre** un Pull Request

---

## 📄 **Licencia**

Este proyecto está bajo la **Licencia MIT**. Ver el archivo [LICENSE](LICENSE) para más detalles.

---

## 🙏 **Agradecimientos**

- **yt-dlp** - Motor de descarga de videos
- **Nea Studio** - Inspiración para el diseño de la interfaz
- **Python Community** - Librerías y herramientas
- **Contribuidores** - Ideas y mejoras

---

## 📞 **Soporte**

- **Issues**: [GitHub Issues](https://github.com/Kasaco223/K-YoutubeVideoDownloaderHD/issues)
- **Discusiones**: [GitHub Discussions](https://github.com/Kasaco223/K-YoutubeVideoDownloaderHD/discussions)
- **Wiki**: [Documentación completa](https://github.com/Kasaco223/K-YoutubeVideoDownloaderHD/wiki)

---

<div align="center">

**¡Disfruta descargando videos en Ultra HD! 🎬✨**

[![Star](https://img.shields.io/github/stars/Kasaco223/K-YoutubeVideoDownloaderHD?style=social)](https://github.com/Kasaco223/K-YoutubeVideoDownloaderHD)
[![Fork](https://img.shields.io/github/forks/Kasaco223/K-YoutubeVideoDownloaderHD?style=social)](https://github.com/Kasaco223/K-YoutubeVideoDownloaderHD)
[![Watch](https://img.shields.io/github/watchers/Kasaco223/K-YoutubeVideoDownloaderHD?style=social)](https://github.com/Kasaco223/K-YoutubeVideoDownloaderHD)

</div>
