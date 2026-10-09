"""Contenedor de servicios de la app: los crea, los conecta y arma el estado que ve la UI."""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path
from typing import Any

from . import __version__, paths, winintegration
from .constants import ENGINE_HINTS_URL, WEB_BASE
from .downloads import DownloadManager, Job
from .engine.binaries import EngineManager
from .engine.hints import HintsStore
from .history import History
from .media import MediaService, engine_config_factory
from .selfupdate import SelfUpdater
from .settings import SettingsStore
from .uipump import UiPump
from .util import log

APPROX_SIZES = {"ytdlp": 3_100_000, "ffmpeg": 115_000_000, "deno": 42_600_000}


def system_language() -> str:
    if sys.platform == "win32":
        try:
            import ctypes

            # Español si lo es el idioma de Windows o el formato regional (muchas PCs en Latinoamérica
            # tienen Windows en inglés con formato regional en español).
            k32 = ctypes.windll.kernel32
            spanish = 0x0A
            if (k32.GetUserDefaultUILanguage() & 0x3FF) == spanish or (k32.GetUserDefaultLCID() & 0x3FF) == spanish:
                return "es"
            return "en"
        except OSError:
            pass
    lang = (os.environ.get("LANG") or "es").lower()
    return "en" if lang.startswith("en") else "es"


class Services:
    def __init__(self):
        self.pump = UiPump()
        self.settings = SettingsStore()
        self.history = History(paths.history_file())
        self.hints = HintsStore(paths.data_dir() / "hints.json", ENGINE_HINTS_URL)
        self.engine = EngineManager(paths.engine_dir(), paths.console_python(), on_change=self._engine_changed,
                                    use_system_tools=os.environ.get("KD_NO_SYSTEM_TOOLS") != "1")
        self.config = engine_config_factory(self.engine, self.settings, self.hints)
        self.media = MediaService(self.engine, self.settings, self.hints, self.config, self.lang)
        self.downloads = DownloadManager(self.settings, self.engine, self.history, self.hints, self.config,
                                         self.pump.emit, self.lang, on_finished=self._job_finished,
                                         prevent_sleep=winintegration.prevent_sleep)
        self.updater = SelfUpdater(paths.data_dir() / "update.json")
        self.update_view: dict[str, Any] | None = None
        self.window = None
        self.hwnd = 0
        self.force_quit = False
        self._bg_lock = threading.Lock()

    # ------------------------------------------------------------------ estado para la UI
    def lang(self) -> str:
        pref = self.settings.get().language
        return pref if pref in ("es", "en") else system_language()

    def engine_view(self, status: dict[str, Any] | None = None) -> dict[str, Any]:
        status = status or self.engine.status()
        comps = {}
        for name in ("ytdlp", "ffmpeg", "deno"):
            comp = dict(status.get(name) or {})
            comp.pop("name", None)
            comp["approx_size"] = APPROX_SIZES[name]
            comps[name] = comp
        return {"ready": bool(status.get("ready")), "busy": bool(status.get("busy")),
                "channel": self.settings.get().engine_channel, "components": comps}

    def state(self) -> dict[str, Any]:
        s = self.settings.get()
        notice = self.hints.hints.notice or None
        return {
            "version": __version__, "lang": self.lang(), "platform": sys.platform,
            "settings": s.to_dict(), "engine": self.engine_view(), "jobs": self.downloads.views(),
            "first_run": not s.first_run_done, "update": self.update_view, "notice": notice,
            "web_base": WEB_BASE,
        }

    def emit_settings(self) -> None:
        self.pump.emit({"type": "settings", "settings": self.settings.get().to_dict()}, "settings")

    def _engine_changed(self, status: dict[str, Any]) -> None:
        # Se llama al construir EngineManager, antes de que existan los demás servicios.
        if getattr(self, "settings", None) is None:
            return
        self.pump.emit({"type": "engine", "engine": self.engine_view(status)}, "engine")

    # ------------------------------------------------------------------ tareas de fondo
    def run_bg(self, name: str, fn) -> None:
        def wrapper() -> None:
            try:
                fn()
            except Exception:  # noqa: BLE001
                log.exception("Tarea de fondo %s falló", name)
        threading.Thread(target=wrapper, daemon=True, name=f"kd-{name}").start()

    def start_background(self) -> None:
        self.downloads.start()
        self.run_bg("startup", self._startup_checks)

    def _startup_checks(self) -> None:
        hints = self.hints.refresh()
        if hints.notice:
            self.pump.emit({"type": "notice", "notice": hints.notice}, "notice")
        s = self.settings.get()
        if s.first_run_done:
            with self._bg_lock:
                if not self.engine.ready():
                    self.engine.ensure(channel=s.engine_channel)
                elif s.auto_update_engine:
                    self.engine.check_updates(channel=s.engine_channel, minimum=hints.min_ytdlp.get(s.engine_channel))
                if self.engine.states["deno"].state != "ready":
                    self.engine.ensure(channel=s.engine_channel)
        if s.check_app_updates and paths.install_root() is not None:
            view = self.updater.check()
            if view:
                self.update_view = view
                self.pump.emit({"type": "update", "update": view}, "update")

    # ------------------------------------------------------------------ fin de trabajos
    def _job_finished(self, job: Job) -> None:
        s = self.settings.get()
        focused = self.hwnd and winintegration.foreground_hwnd() == self.hwnd
        es = self.lang() == "es"
        if job.state == "done":
            if s.notify_on_finish and not focused:
                winintegration.notify("Descarga lista" if es else "Download finished", job.title or job.url)
            if s.open_folder_on_finish and job.file_path and os.path.exists(job.file_path):
                winintegration.show_in_folder(Path(job.file_path))
        elif job.state == "error" and not focused:
            winintegration.flash_window(self.hwnd)

    def shutdown(self) -> None:
        try:
            self.downloads.shutdown()
        finally:
            self.pump.stop()
