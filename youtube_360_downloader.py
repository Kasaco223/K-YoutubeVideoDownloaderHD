import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import sys
import yt_dlp
from datetime import datetime
import pytz
import shutil
import zipfile
import tempfile
import platform
import subprocess
import requests

class ModernYouTubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("Ultra HD Video Downloader")
        self.root.geometry("1000x700")
        self.root.configure(bg="#0a0a0a")
        self.root.resizable(True, True)
        
        # Variables
        self.download_path = tk.StringVar(value=os.path.expanduser("~/Downloads"))
        self.url_var = tk.StringVar()
        self.quality_var = tk.StringVar(value="1080p")
        self.downloading = False
        self.cookies_path = tk.StringVar(value="")
        
        # Configure custom styles
        self.setup_styles()
        self.setup_ui()
        
    def _get_base_dir(self):
        """Devuelve la carpeta base del programa (soporta ejecutable PyInstaller)."""
        try:
            if getattr(sys, 'frozen', False):
                return os.path.dirname(sys.executable)
            return os.path.dirname(os.path.abspath(__file__))
        except Exception:
            return os.getcwd()

    def _find_ffmpeg(self):
        """Busca ffmpeg/ffprobe y asegura su disponibilidad.

        Orden:
        1) bin local preferente (junto al exe/carpeta base)
        2) Si no existe, PATH del sistema (shutil.which)
        3) Si en Windows y no está, descarga FFmpeg portable a un directorio escribible y devuélvelo

        Devuelve: ruta del directorio que contiene ffmpeg/ffprobe o None si confiar en PATH
        """
        base_dir = self._get_base_dir()
        local_bin = os.path.join(base_dir, 'bin')
        ffmpeg_exe = 'ffmpeg.exe' if os.name == 'nt' else 'ffmpeg'
        ffprobe_exe = 'ffprobe.exe' if os.name == 'nt' else 'ffprobe'

        local_ffmpeg = os.path.join(local_bin, ffmpeg_exe)
        local_ffprobe = os.path.join(local_bin, ffprobe_exe)
        if os.path.exists(local_ffmpeg) and os.path.exists(local_ffprobe):
            self.log_message(f"🎬 FFmpeg encontrado en carpeta local: {local_bin}")
            return local_bin

        # Si no está en bin, intentar en PATH
        ffmpeg_in_path = shutil.which(ffmpeg_exe)
        ffprobe_in_path = shutil.which(ffprobe_exe)
        if ffmpeg_in_path and ffprobe_in_path:
            self.log_message("🔎 FFmpeg encontrado en PATH del sistema.")
            return None  # yt-dlp lo encontrará en PATH

        # En Windows, intentar auto-descargar FFmpeg portable
        if os.name == 'nt':
            try:
                self.log_message("📥 FFmpeg no encontrado. Descargando FFmpeg portable (Windows)...")
                bin_dir = self._get_writable_bin_dir()
                os.makedirs(bin_dir, exist_ok=True)

                ffmpeg_zip_url = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'
                with tempfile.TemporaryDirectory() as tmpdir:
                    zip_path = os.path.join(tmpdir, 'ffmpeg.zip')
                    # Descargar
                    r = requests.get(ffmpeg_zip_url, timeout=60)
                    r.raise_for_status()
                    with open(zip_path, 'wb') as f:
                        f.write(r.content)
                    # Extraer y copiar binarios
                    with zipfile.ZipFile(zip_path, 'r') as zf:
                        zf.extractall(tmpdir)
                    # Buscar carpeta ffmpeg-*
                    found = False
                    for name in os.listdir(tmpdir):
                        if name.lower().startswith('ffmpeg-'):
                            cand_bin = os.path.join(tmpdir, name, 'bin')
                            src_ffmpeg = os.path.join(cand_bin, 'ffmpeg.exe')
                            src_ffprobe = os.path.join(cand_bin, 'ffprobe.exe')
                            if os.path.exists(src_ffmpeg) and os.path.exists(src_ffprobe):
                                shutil.copy2(src_ffmpeg, os.path.join(bin_dir, 'ffmpeg.exe'))
                                shutil.copy2(src_ffprobe, os.path.join(bin_dir, 'ffprobe.exe'))
                                found = True
                                break
                    if found and os.path.exists(os.path.join(bin_dir, 'ffmpeg.exe')) and os.path.exists(os.path.join(bin_dir, 'ffprobe.exe')):
                        self.log_message(f"✅ FFmpeg portable instalado en: {bin_dir}")
                        return bin_dir
                    else:
                        self.log_message("⚠️ No se pudo ubicar ffmpeg.exe/ffprobe.exe en el ZIP descargado.")
            except Exception as e:
                self.log_message(f"⚠️ Falló la descarga automática de FFmpeg: {e}")

        # Último recurso: confiar en PATH (puede fallar si no está)
        self.log_message("ℹ️ FFmpeg no encontrado. Se intentará usar el del sistema (PATH).")
        return None

    def _get_writable_bin_dir(self):
        """Devuelve una carpeta 'bin' escribible para almacenar FFmpeg portable.
        Prioriza la carpeta base; si no es escribible, usa AppData Local en Windows.
        """
        base_dir = self._get_base_dir()
        candidate = os.path.join(base_dir, 'bin')
        try:
            os.makedirs(candidate, exist_ok=True)
            test_file = os.path.join(candidate, '.write_test')
            with open(test_file, 'w') as f:
                f.write('ok')
            os.remove(test_file)
            return candidate
        except Exception:
            pass

        if os.name == 'nt':
            local_appdata = os.environ.get('LOCALAPPDATA') or os.path.expanduser('~')
            fallback = os.path.join(local_appdata, 'YouTubeUltraHD', 'bin')
            return fallback
        else:
            # Unix-like fallback en HOME
            return os.path.join(os.path.expanduser('~'), '.local', 'share', 'youtube_ultra_hd', 'bin')

    def setup_styles(self):
        """Configura estilos personalizados modernos"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure modern colors
        style.configure("Modern.TFrame", background="#0a0a0a")
        style.configure("Card.TFrame", background="#1a1a1a", relief="flat")
        style.configure("Modern.TLabel", background="#1a1a1a", foreground="#ffffff", font=("Segoe UI", 10))
        style.configure("Title.TLabel", background="#0a0a0a", foreground="#ffffff", font=("Segoe UI", 24, "bold"))
        style.configure("Subtitle.TLabel", background="#0a0a0a", foreground="#888888", font=("Segoe UI", 14))
        style.configure("Modern.TButton", 
                       background="#6366f1", 
                       foreground="white",
                       font=("Segoe UI", 11, "bold"),
                       relief="flat",
                       borderwidth=0)
        style.configure("Modern.TButton:hover", background="#4f46e5")
        style.configure("Accent.TButton", 
                       background="linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                       foreground="white",
                       font=("Segoe UI", 12, "bold"),
                       relief="flat",
                       borderwidth=0)
        style.configure("Modern.TEntry", 
                       fieldbackground="#2a2a2a", 
                       foreground="#ffffff",
                       borderwidth=0,
                       relief="flat")
        style.configure("Modern.TCombobox", 
                       fieldbackground="#2a2a2a", 
                       foreground="#ffffff",
                       background="#2a2a2a",
                       borderwidth=0,
                       relief="flat")
        style.configure("Modern.TProgressbar", 
                       background="#6366f1",
                       troughcolor="#2a2a2a",
                       borderwidth=0,
                       relief="flat")
        
    def setup_ui(self):
        """Configura la interfaz moderna"""
        # Main container with gradient effect using grid
        main_container = tk.Frame(self.root, bg="#0a0a0a")
        main_container.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        
        # Configure root grid weights
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Configure main container grid weights
        main_container.grid_rowconfigure(1, weight=1)
        main_container.grid_columnconfigure(0, weight=1)
        
        # Add subtle border effect
        border_frame = tk.Frame(main_container, bg="#6366f1", height=2)
        border_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        
        # Create scrollable canvas with proper expansion
        canvas = tk.Canvas(main_container, bg="#0a0a0a", highlightthickness=0)
        scrollbar = tk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#0a0a0a")
        
        # Configure scrollable frame to expand
        scrollable_frame.columnconfigure(0, weight=1)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        # Create window that expands with the frame
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=canvas.winfo_width())
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Bind canvas resize to update window width
        def on_canvas_configure(event):
            canvas.itemconfig(canvas.find_withtag("all")[0], width=event.width)
        
        canvas.bind("<Configure>", on_canvas_configure)
        
        # Header section with gradient background
        header_frame = tk.Frame(scrollable_frame, bg="#1a1a1a", relief="flat", bd=0)
        header_frame.pack(fill=tk.X, pady=(0, 30))
        
        # Title with modern typography
        title_label = tk.Label(header_frame, 
                              text="Ultra HD Video Downloader", 
                              font=("Segoe UI", 32, "bold"),
                              bg="#1a1a1a", fg="#ffffff")
        title_label.pack(pady=(30, 10))
        
        subtitle_label = tk.Label(header_frame, 
                                 text="Descarga videos de YouTube, TikTok, Instagram, etc. hasta 4K 60fps", 
                                 font=("Segoe UI", 16),
                                 bg="#1a1a1a", fg="#888888")
        subtitle_label.pack(pady=(0, 30))
        
        # Main content area with proper expansion
        content_frame = tk.Frame(scrollable_frame, bg="#0a0a0a")
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configure content frame to expand
        content_frame.columnconfigure(0, weight=1)
        
        # URL input card
        url_card = tk.Frame(content_frame, bg="#1a1a1a", relief="flat", bd=0)
        url_card.pack(fill=tk.X, pady=(0, 20))
        url_card.columnconfigure(0, weight=1)
        
        url_label = tk.Label(url_card, text="🔗 URL del Video (YouTube, TikTok, Instagram, ...)", 
                            font=("Segoe UI", 14, "bold"),
                            bg="#1a1a1a", fg="#ffffff")
        url_label.pack(anchor=tk.W, pady=(20, 10), padx=20)
        
        url_entry = tk.Entry(url_card, 
                            textvariable=self.url_var,
                            font=("Segoe UI", 12),
                            bg="#2a2a2a", fg="#ffffff",
                            insertbackground="#6366f1",
                            relief="flat", bd=0,
                            highlightthickness=1,
                            highlightbackground="#3a3a3a",
                            highlightcolor="#6366f1")
        url_entry.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        # Quality selection card
        quality_card = tk.Frame(content_frame, bg="#1a1a1a", relief="flat", bd=0)
        quality_card.pack(fill=tk.X, pady=(0, 20))
        quality_card.columnconfigure(0, weight=1)
        
        quality_label = tk.Label(quality_card, text="🎬 Calidad del Video", 
                                font=("Segoe UI", 14, "bold"),
                                bg="#1a1a1a", fg="#ffffff")
        quality_label.pack(anchor=tk.W, pady=(20, 10), padx=20)
        
        # Modern quality selector
        quality_frame = tk.Frame(quality_card, bg="#1a1a1a")
        quality_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        qualities = ["2160p60", "2160p", "1440p", "1080p", "720p", "480p", "360p"]
        self.quality_buttons = []
        
        for i, quality in enumerate(qualities):
            btn = tk.Button(quality_frame, 
                           text=quality,
                           font=("Segoe UI", 10, "bold"),
                           bg="#2a2a2a" if quality != "1080p" else "#6366f1",
                           fg="#ffffff" if quality != "1080p" else "#ffffff",
                           relief="flat", bd=0,
                           padx=15, pady=8,
                           command=lambda q=quality: self.select_quality(q))
            
            # Add hover effects
            btn.bind("<Enter>", lambda e, b=btn: self.on_button_hover(b, True))
            btn.bind("<Leave>", lambda e, b=btn: self.on_button_hover(b, False))
            
            btn.pack(side=tk.LEFT, padx=(0, 10))
            self.quality_buttons.append(btn)
        
        # Destination folder card
        dest_card = tk.Frame(content_frame, bg="#1a1a1a", relief="flat", bd=0)
        dest_card.pack(fill=tk.X, pady=(0, 20))
        dest_card.columnconfigure(0, weight=1)
        
        dest_label = tk.Label(dest_card, text="📁 Carpeta de Destino", 
                             font=("Segoe UI", 14, "bold"),
                             bg="#1a1a1a", fg="#ffffff")
        dest_label.pack(anchor=tk.W, pady=(20, 10), padx=20)
        
        dest_frame = tk.Frame(dest_card, bg="#1a1a1a")
        dest_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        dest_frame.columnconfigure(0, weight=1)
        
        dest_entry = tk.Entry(dest_frame, 
                             textvariable=self.download_path,
                             font=("Segoe UI", 12),
                             bg="#2a2a2a", fg="#ffffff",
                             insertbackground="#6366f1",
                             relief="flat", bd=0,
                             highlightthickness=1,
                             highlightbackground="#3a3a3a",
                             highlightcolor="#6366f1")
        dest_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        browse_btn = tk.Button(dest_frame, 
                              text="Examinar",
                              font=("Segoe UI", 10, "bold"),
                              bg="#4a4a4a", fg="#ffffff",
                              relief="flat", bd=0,
                              padx=20, pady=8,
                              command=self.browse_folder)
        browse_btn.pack(side=tk.RIGHT, padx=(10, 0))

        # Optional cookies.txt card (useful for Instagram/TikTok private or rate-limited)
        cookies_card = tk.Frame(content_frame, bg="#1a1a1a", relief="flat", bd=0)
        cookies_card.pack(fill=tk.X, pady=(0, 20))
        cookies_card.columnconfigure(0, weight=1)

        cookies_label = tk.Label(cookies_card, text="🍪 Archivo cookies.txt (opcional)", 
                                 font=("Segoe UI", 14, "bold"),
                                 bg="#1a1a1a", fg="#ffffff")
        cookies_label.pack(anchor=tk.W, pady=(20, 10), padx=20)

        cookies_frame = tk.Frame(cookies_card, bg="#1a1a1a")
        cookies_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        cookies_frame.columnconfigure(0, weight=1)

        cookies_entry = tk.Entry(cookies_frame, 
                                 textvariable=self.cookies_path,
                                 font=("Segoe UI", 12),
                                 bg="#2a2a2a", fg="#ffffff",
                                 insertbackground="#6366f1",
                                 relief="flat", bd=0,
                                 highlightthickness=1,
                                 highlightbackground="#3a3a3a",
                                 highlightcolor="#6366f1")
        cookies_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        cookies_browse_btn = tk.Button(cookies_frame, 
                                       text="Examinar cookies",
                                       font=("Segoe UI", 10, "bold"),
                                       bg="#4a4a4a", fg="#ffffff",
                                       relief="flat", bd=0,
                                       padx=20, pady=8,
                                       command=self.browse_cookies_file)
        cookies_browse_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Download button card
        download_card = tk.Frame(content_frame, bg="#1a1a1a", relief="flat", bd=0)
        download_card.pack(fill=tk.X, pady=(0, 20))
        download_card.columnconfigure(0, weight=1)
        
        self.download_btn = tk.Button(download_card, 
                                     text="🚀 DESCARGAR VIDEO",
                                     font=("Segoe UI", 16, "bold"),
                                     bg="#6366f1", fg="#ffffff",
                                     relief="flat", bd=0,
                                     padx=40, pady=15,
                                     command=self.start_download)
        self.download_btn.pack(pady=20)
        
        # Progress section
        progress_card = tk.Frame(content_frame, bg="#1a1a1a", relief="flat", bd=0)
        progress_card.pack(fill=tk.X, pady=(0, 20))
        progress_card.columnconfigure(0, weight=1)
        
        self.progress = tk.Canvas(progress_card, 
                                 height=6, 
                                 bg="#2a2a2a", 
                                 highlightthickness=0)
        self.progress.pack(fill=tk.X, padx=20, pady=20)
        
        # Create animated progress bar
        self.progress_rect = self.progress.create_rectangle(0, 0, 0, 6, fill="#6366f1", outline="")
        
        self.status_label = tk.Label(progress_card, 
                                    text="✨ Listo para descargar",
                                    font=("Segoe UI", 12),
                                    bg="#1a1a1a", fg="#888888")
        self.status_label.pack(pady=(0, 20))
        
        # Log section with proper expansion
        log_card = tk.Frame(content_frame, bg="#1a1a1a", relief="flat", bd=0)
        log_card.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        log_card.columnconfigure(0, weight=1)
        log_card.rowconfigure(1, weight=1)
        
        log_header = tk.Frame(log_card, bg="#1a1a1a")
        log_header.pack(fill=tk.X, padx=20, pady=(20, 10))
        
        log_title = tk.Label(log_header, 
                            text="📋 Registro de Descarga",
                            font=("Segoe UI", 14, "bold"),
                            bg="#1a1a1a", fg="#ffffff")
        log_title.pack(side=tk.LEFT)
        
        clear_log_btn = tk.Button(log_header, 
                                 text="🧹 Limpiar",
                                 font=("Segoe UI", 10),
                                 bg="#4a4a4a", fg="#ffffff",
                                 relief="flat", bd=0,
                                 padx=15, pady=5,
                                 command=self.clear_log)
        clear_log_btn.pack(side=tk.RIGHT)
        
        # Log text area with modern styling and proper expansion
        log_frame = tk.Frame(log_card, bg="#1a1a1a")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = tk.Text(log_frame, 
                               height=8,
                               font=("Consolas", 10),
                               bg="#2a2a2a", fg="#ffffff",
                               insertbackground="#6366f1",
                               relief="flat", bd=0,
                               highlightthickness=1,
                               highlightbackground="#3a3a3a",
                               highlightcolor="#6366f1")
        
        log_scrollbar = tk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Grid canvas and scrollbar with proper expansion
        canvas.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        scrollbar.grid(row=1, column=1, sticky="ns")
        
        # Configure canvas to expand properly
        canvas.configure(width=main_container.winfo_reqwidth())
        
        # Bind mouse wheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
    def select_quality(self, quality):
        """Selecciona la calidad del video"""
        self.quality_var.set(quality)
        
        # Update button styles
        for btn in self.quality_buttons:
            if btn.cget("text") == quality:
                btn.configure(bg="#6366f1")
            else:
                btn.configure(bg="#2a2a2a")
    
    def start_progress_animation(self):
        """Inicia la animación del progressbar"""
        self.progress_animating = True
        self.animate_progress()
    
    def stop_progress_animation(self):
        """Detiene la animación del progressbar"""
        self.progress_animating = False
        self.progress.coords(self.progress_rect, 0, 0, 0, 6)
    
    def animate_progress(self):
        """Anima el progressbar"""
        if not self.progress_animating:
            return
        
        # Get canvas width
        width = self.progress.winfo_width()
        if width <= 1:
            self.root.after(100, self.animate_progress)
            return
        
        # Animate progress bar
        import math
        import time
        
        current_time = time.time()
        progress = (math.sin(current_time * 2) + 1) / 2  # 0 to 1
        bar_width = int(width * progress)
        
        self.progress.coords(self.progress_rect, 0, 0, bar_width, 6)
        self.root.after(50, self.animate_progress)
    
    def on_button_hover(self, button, entering):
        """Maneja los efectos hover de los botones"""
        if entering:
            if button.cget("bg") != "#6366f1":  # Si no es el botón activo
                button.configure(bg="#3a3a3a")
        else:
            if button.cget("bg") != "#6366f1":  # Si no es el botón activo
                button.configure(bg="#2a2a2a")
    
    def get_colombian_datetime(self):
        """Obtiene la fecha y hora actual de Colombia"""
        try:
            colombia_tz = pytz.timezone('America/Bogota')
            now = datetime.now(colombia_tz)
            return now.strftime("%Y%m%d_%H%M%S")
        except Exception:
            # Fallback si pytz no está disponible
            now = datetime.now()
            return now.strftime("%Y%m%d_%H%M%S")
    
    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.download_path.get())
        if folder:
            self.download_path.set(folder)

    def browse_cookies_file(self):
        file_path = filedialog.askopenfilename(
            title="Selecciona cookies.txt",
            filetypes=[("cookies.txt", "*.txt"), ("Todos los archivos", "*.*")]
        )
        if file_path:
            self.cookies_path.set(file_path)
            
    def log_message(self, message):
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def clear_log(self):
        """Limpia el área de registro"""
        self.log_text.delete(1.0, tk.END)
        self.log_message("🧹 Log limpiado")
        
    def start_download(self):
        if self.downloading:
            return
            
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Error", "Por favor ingresa la URL del video")
            return
            
        if not url.startswith(('http://', 'https://')):
            messagebox.showerror("Error", "Por favor ingresa una URL válida")
            return
            # Asegurar que la carpeta de descarga exista
        try:
            os.makedirs(self.download_path.get(), exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo crear la carpeta de destino:\n{e}")
            return

        self.downloading = True
        self.download_btn.config(state='disabled')
        self.start_progress_animation()
        self.status_label.config(text="Descargando...")
        
        # Start download in separate thread
        thread = threading.Thread(target=self.download_video, args=(url,))
        thread.daemon = True
        thread.start()
        
    def download_video(self, url):
        try:
            self.log_message("🚀 Iniciando descarga directa...")
            self.log_message("💡 No se requiere verificación previa - descarga inmediata")
            self.log_message(f"URL: {url}")
            self.log_message(f"Calidad seleccionada: {self.quality_var.get()}")
            self.log_message(f"Carpeta de destino: {self.download_path.get()}")
            
            # Configure yt-dlp options for high quality video
            quality = self.quality_var.get()
            
            # Selección de formato más flexible (no fuerza MP4/M4A)
            # Preferimos video+audio adaptativo hasta la altura elegida, con fallback a "best".
            # Esto evita errores cuando YouTube solo ofrece WebM/Opus o AV1/VP9.
            if quality == "2160p60":
                format_spec = "bv*[height<=2160][fps<=60]+ba/b[height<=2160][fps<=60]/b"
            elif quality == "2160p":
                format_spec = "bv*[height<=2160]+ba/b[height<=2160]/b"
            elif quality == "1440p":
                format_spec = "bv*[height<=1440]+ba/b[height<=1440]/b"
            elif quality == "1080p":
                format_spec = "bv*[height<=1080]+ba/b[height<=1080]/b"
            elif quality == "720p":
                format_spec = "bv*[height<=720]+ba/b[height<=720]/b"
            elif quality == "480p":
                format_spec = "bv*[height<=480]+ba/b[height<=480]/b"
            else:  # 360p
                format_spec = "bv*[height<=360]+ba/b[height<=360]/b"
            
            # Si la calidad seleccionada no está disponible, usar la mejor calidad posible
            self.log_message("🎯 Si la calidad seleccionada no está disponible, se descargará la mejor calidad posible")
            self.log_message("💡 No se fuerza MP4/M4A. Se aceptan WebM/Opus/AV1/VP9 y se fusiona automáticamente")
            self.log_message(f"🎬 Intentando descargar en {quality} - si no está disponible, se usará la mejor calidad")
            self.log_message("📹 Solo se descargará el video individual (no la playlist completa)")
            
            # Generate filename with Colombian datetime
            colombian_datetime = self.get_colombian_datetime()
            filename = f"K-{colombian_datetime}.%(ext)s"
            
            ffmpeg_loc = self._find_ffmpeg()

            ydl_opts = {
                'format': format_spec,
                'outtmpl': os.path.join(self.download_path.get(), filename),
                'progress_hooks': [self.progress_hook],
                'writesubtitles': False,
                'writethumbnail': False,
                'ignoreerrors': False,
                'no_warnings': False,
                'postprocessors': [],
                # Usamos MKV para compatibilidad (mezcla VP9/AV1 + Opus sin recodificar)
                'merge_output_format': 'mkv',
                'noplaylist': True,  # Solo descargar el video individual, no la playlist
                'geo_bypass': True,
            }

            if ffmpeg_loc:
                ydl_opts['ffmpeg_location'] = ffmpeg_loc
                self.log_message(f"🔧 Usando FFmpeg desde: {ffmpeg_loc}")
            else:
                self.log_message("🔎 Intentando usar FFmpeg desde el PATH del sistema.")

            # Adjuntar cookies si el usuario proporcionó un archivo
            cookies_file = self.cookies_path.get().strip()
            if cookies_file:
                ydl_opts['cookiefile'] = cookies_file
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Get video info first
                self.log_message("Obteniendo información del video...")
                info = ydl.extract_info(url, download=False)
                
                if info:
                    title = info.get('title', 'N/A')
                    duration = info.get('duration', 'N/A')
                    format_info = info.get('format', 'N/A')
                    
                    self.log_message(f"Título: {title}")
                    self.log_message(f"Duración: {duration} segundos" if duration != 'N/A' else "Duración: N/A")
                    self.log_message(f"Formato disponible: {format_info}")
                    
                    # Show file size estimate for selected quality
                    selected_quality = self.quality_var.get()
                    if selected_quality in ["2160p60", "2160p", "1440p"]:
                        self.log_message("⚠️  Nota: Videos de alta calidad pueden ser muy grandes")
                        if selected_quality == "2160p60":
                            self.log_message("🎯 Descargando en 4K 60fps - Máxima calidad disponible")
                        elif selected_quality == "2160p":
                            self.log_message("🎬 Descargando en 4K - Calidad ultra alta")
                        elif selected_quality == "1440p":
                            self.log_message("📺 Descargando en 2K - Calidad muy alta")
                    
                    # Check for special features
                    formats = info.get('formats', [])
                    has_360deg = False
                    has_4k = False
                    has_60fps = False
                    
                    if formats:
                        for f in formats:
                            height = f.get('height')
                            fps = f.get('fps')
                            projection = f.get('projection') or f.get('projection_type')
                            is_360_flag = f.get('is_360')
                            
                            if height:
                                if height >= 2160:
                                    has_4k = True
                            
                            if fps and fps >= 60:
                                has_60fps = True

                            # Detección de video 360° real (esférico)
                            if (is_360_flag is True) or (isinstance(projection, str) and projection.lower() in (
                                '360', 'equirectangular', 'spherical', 'cubemap'
                            )):
                                has_360deg = True
                    
                    # Log special features
                    if has_4k:
                        self.log_message("🎬 Video 4K (2160p) disponible!")
                    if has_60fps:
                        self.log_message("⚡ Video 60fps disponible!")
                    if has_360deg:
                        self.log_message("✓ Video 360° (esférico) detectado!")
                    
                    if not has_360deg and not has_4k:
                        self.log_message("📹 Video estándar - se descargará en la mejor calidad disponible")
                    
                    # Start actual download
                    self.log_message("Iniciando descarga del video...")
                    ydl.download([url])
                    
                    self.log_message("✓ Descarga completada exitosamente!")
                    self.log_message("🎯 El video se descargó en la mejor calidad disponible para tu selección")
                    self.root.after(0, lambda: self.status_label.config(text="Descarga completada"))
                    
                else:
                    self.log_message("❌ No se pudo obtener información del video")
                    
        except Exception as e:
            error_msg = f"❌ Error durante la descarga: {str(e)}"
            self.log_message(error_msg)
            self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
            self.root.after(0, lambda: self.status_label.config(text="Error en la descarga"))
            
        finally:
            self.downloading = False
            self.root.after(0, lambda: self.download_btn.config(state='normal'))
            self.root.after(0, lambda: self.stop_progress_animation())
            
    def progress_hook(self, d):
        try:
            if d['status'] == 'downloading':
                downloaded_bytes = d.get('downloaded_bytes', 0)
                total_bytes = d.get('total_bytes', 0)
                speed = d.get('speed', 0)
                
                if total_bytes and total_bytes > 0:
                    percent = (downloaded_bytes / total_bytes) * 100
                    if speed and speed > 0:
                        speed_mb = speed / 1024 / 1024
                        self.root.after(0, lambda: self.status_label.config(
                            text=f"Descargando... {percent:.1f}% - {speed_mb:.1f} MB/s"))
                    else:
                        self.root.after(0, lambda: self.status_label.config(
                            text=f"Descargando... {percent:.1f}%"))
                else:
                    downloaded_mb = downloaded_bytes / 1024 / 1024
                    self.root.after(0, lambda: self.status_label.config(
                        text=f"Descargando... {downloaded_mb:.1f} MB"))
                        
            elif d['status'] == 'finished':
                self.log_message("✓ Archivo descargado, procesando...")
                
        except Exception as e:
            self.log_message(f"⚠ Error en progreso: {str(e)}")

def main():
    root = tk.Tk()
    
    # Configure styles
    style = ttk.Style()
    style.theme_use('clam')
    
    # Create accent button style
    style.configure("Accent.TButton", 
                   background="#0078d4", 
                   foreground="white",
                   font=("Arial", 12, "bold"))
    
    app = ModernYouTubeDownloader(root)
    
    # Center window
    root.update_idletasks()
    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
    root.geometry(f"+{x}+{y}")
    
    root.mainloop()

if __name__ == "__main__":
    main()
