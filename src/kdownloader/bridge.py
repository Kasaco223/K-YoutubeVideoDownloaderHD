"""API expuesta a JavaScript (`window.pywebview.api.*`). Contrato: docs/architecture.md §4.

Cada método corre en su propio hilo (así lo hace pywebview) y devuelve siempre `{ok: true, ...}` o
`{ok: false, error: ErrorView}`. JS nunca manda rutas ni URLs para abrir: solo IDs y claves.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from . import paths, winintegration
from .constants import WEB_PAGES
from .engine import errors
from .engine.ytdlp import EngineFailure
from .media import validate_url
from .selfupdate import relaunch
from .services import Services
from .util import log

_CODE_RE = re.compile(r"^[a-z0-9_]{1,40}$")
_PROTECTED_SETTINGS = {"download_dir", "cookies_file", "accepted_terms", "first_run_done", "version"}


def _ok(**data: Any) -> dict[str, Any]:
    return {"ok": True, **data}


def _fail(code: str, lang: str, details: str = "") -> dict[str, Any]:
    data = errors.catalog()
    rule = next((r for r in data["rules"] if r["code"] == code), None)
    if rule is None:
        texts = _LOCAL_ERRORS.get(code) or _LOCAL_ERRORS["unknown"]
        return {"ok": False, "error": {"code": code, "action": texts.get("action", "none"), "auto": None,
                                       "title": texts[lang]["title"], "message": texts[lang]["message"],
                                       "details": details, "texts": {"es": texts["es"], "en": texts["en"]}}}
    return {"ok": False, "error": {"code": rule["code"], "action": rule["action"], "auto": rule.get("auto"),
                                   "title": rule[lang]["title"], "message": rule[lang]["message"],
                                   "details": details, "texts": {"es": rule["es"], "en": rule["en"]}}}


_LOCAL_ERRORS: dict[str, dict[str, Any]] = {
    "engine_not_ready": {
        "action": "repair_engine",
        "es": {"title": "Preparando el motor", "message": "Espera a que terminen de bajar los componentes."},
        "en": {"title": "Preparing the engine", "message": "Wait for the components to finish downloading."}},
    "canceled": {
        "es": {"title": "Cancelado", "message": "Se canceló el análisis."},
        "en": {"title": "Canceled", "message": "The analysis was canceled."}},
    "timeout": {
        "action": "retry",
        "es": {"title": "El análisis tardó demasiado", "message": "Revisa tu conexión y vuelve a intentarlo."},
        "en": {"title": "The analysis took too long", "message": "Check your connection and try again."}},
    "busy": {
        "es": {"title": "Hay descargas en curso", "message": "Espera a que terminen para actualizar."},
        "en": {"title": "Downloads in progress", "message": "Wait for them to finish before updating."}},
    "not_found": {
        "es": {"title": "No encontramos el archivo", "message": "Puede que lo hayas movido o borrado."},
        "en": {"title": "File not found", "message": "You may have moved or deleted it."}},
    "invalid": {
        "es": {"title": "Datos no válidos", "message": "La solicitud no es válida."},
        "en": {"title": "Invalid data", "message": "The request isn't valid."}},
    "unknown": {
        "action": "retry",
        "es": {"title": "Algo salió mal", "message": "Vuelve a intentarlo."},
        "en": {"title": "Something went wrong", "message": "Please try again."}},
}


class Api:
    def __init__(self, services: Services):
        self._s = services

    # ------------------------------------------------------------------ utilidades internas
    def _lang(self) -> str:
        return self._s.lang()

    def _ui_thread(self, fn):
        """Ejecuta `fn` en el hilo de la ventana (evita el interbloqueo de diálogos de pywebview #1823)."""
        result: dict[str, Any] = {}

        def call():
            result["value"] = fn()
            return None

        window = self._s.window
        try:
            from System import Func, Object  # type: ignore[import-not-found]  # pythonnet

            window.native.Invoke(Func[Object](call))
        except Exception:  # noqa: BLE001 - otras plataformas o sin pythonnet
            call()
        return result.get("value")

    def _job_path(self, job_id: str) -> Path | None:
        job = self._s.downloads.get(job_id)
        path = job.file_path if job else None
        if not path:
            item = self._s.history.get(job_id)
            path = item.file_path if item else None
        return Path(path) if path else None

    def _job_url(self, job_id: str) -> str | None:
        job = self._s.downloads.get(job_id)
        url = job.url if job else None
        if not url:
            item = self._s.history.get(job_id)
            url = item.url if item else None
        return url if url and validate_url(url) else None

    # ------------------------------------------------------------------ estado y primer uso
    def ui_ready(self) -> dict[str, Any]:
        self._s.pump.ready()
        return _ok(state=self._s.state())

    def get_state(self) -> dict[str, Any]:
        return _ok(state=self._s.state())

    def accept_terms(self) -> dict[str, Any]:
        return _ok(settings=self._s.settings.update({"accepted_terms": True}).to_dict())

    def finish_onboarding(self, patch: dict[str, Any] | None = None) -> dict[str, Any]:
        patch = {k: v for k, v in (patch or {}).items() if k not in _PROTECTED_SETTINGS}
        try:
            s = self._s.settings.update({**patch, "first_run_done": True, "accepted_terms": True})
        except ValueError as exc:
            return _fail("invalid", self._lang(), str(exc))
        self._s.emit_settings()
        return _ok(settings=s.to_dict())

    # ------------------------------------------------------------------ motor
    def engine_setup(self) -> dict[str, Any]:
        channel = self._s.settings.get().engine_channel
        self._s.run_bg("engine-setup", lambda: self._s.engine.ensure(channel=channel))
        return _ok()

    def engine_update(self, force: bool = False) -> dict[str, Any]:
        s = self._s.settings.get()
        minimum = self._s.hints.hints.min_ytdlp.get(s.engine_channel)
        self._s.run_bg("engine-update", lambda: self._s.engine.check_updates(
            channel=s.engine_channel, force=bool(force), minimum=minimum))
        return _ok()

    def engine_repair(self, component: str | None = None) -> dict[str, Any]:
        if component not in (None, "ytdlp", "ffmpeg", "deno"):
            return _fail("invalid", self._lang())
        channel = self._s.settings.get().engine_channel
        self._s.run_bg("engine-repair", lambda: self._s.engine.repair(component, channel=channel))
        return _ok()

    # ------------------------------------------------------------------ análisis y cola
    def probe(self, url: str, playlist: bool = False) -> dict[str, Any]:
        lang = self._lang()
        if not self._s.engine.ready():
            return _fail("engine_not_ready", lang)
        try:
            return _ok(media=self._s.media.probe(url, bool(playlist)))
        except EngineFailure as exc:
            return {"ok": False, "error": exc.error.to_dict()}
        except ValueError:
            return _fail("unsupported_url", lang)
        except InterruptedError:
            return _fail("canceled", lang)
        except TimeoutError:
            return _fail("timeout", lang)
        except Exception as exc:  # noqa: BLE001
            log.exception("probe falló")
            return _fail("unknown", lang, repr(exc))

    def cancel_probe(self) -> dict[str, Any]:
        self._s.media.cancel()
        return _ok()

    def enqueue(self, token: str, option: str, items: Any = None) -> dict[str, Any]:
        media = self._s.media.get(str(token))
        if media is None:
            return _fail("invalid", self._lang(), "token")
        if items not in (None, "all") and not (isinstance(items, list) and all(isinstance(i, str) for i in items)):
            return _fail("invalid", self._lang(), "items")
        try:
            return _ok(job_ids=self._s.downloads.enqueue(media, str(option), items))
        except ValueError as exc:
            return _fail("invalid", self._lang(), str(exc))

    def quick_download(self, url: str) -> dict[str, Any]:
        res = self.probe(url, False)
        if not res.get("ok"):
            return res
        favorite = self._s.settings.get().favorite_preset
        return self.enqueue(res["media"]["token"], favorite, None)

    def cancel(self, job_id: str) -> dict[str, Any]:
        self._s.downloads.cancel(str(job_id))
        return _ok()

    def retry(self, job_id: str, mode: str = "normal") -> dict[str, Any]:
        if mode not in ("normal", "with_cookies", "best"):
            return _fail("invalid", self._lang())
        self._s.downloads.retry(str(job_id), mode)
        return _ok()

    def remove(self, job_id: str) -> dict[str, Any]:
        self._s.downloads.remove(str(job_id))
        return _ok()

    def cancel_all(self) -> dict[str, Any]:
        self._s.downloads.cancel_all()
        return _ok()

    def clear_finished(self) -> dict[str, Any]:
        self._s.downloads.clear_finished()
        return _ok()

    # ------------------------------------------------------------------ archivos y enlaces
    def open_file(self, job_id: str) -> dict[str, Any]:
        path = self._job_path(str(job_id))
        if not path or not path.exists():
            return _fail("not_found", self._lang())
        winintegration.open_path(path)
        return _ok()

    def show_in_folder(self, job_id: str) -> dict[str, Any]:
        path = self._job_path(str(job_id))
        if not path or not path.exists():
            return _fail("not_found", self._lang())
        winintegration.show_in_folder(path)
        return _ok()

    def open_source(self, job_id: str) -> dict[str, Any]:
        url = self._job_url(str(job_id))
        if not url:
            return _fail("not_found", self._lang())
        winintegration.open_url(url)
        return _ok()

    def copy_details(self, job_id: str) -> dict[str, Any]:
        return _ok(text=self._s.downloads.details(str(job_id)))

    def open_help(self, code: str = "") -> dict[str, Any]:
        code = str(code or "")
        url = WEB_PAGES["help"] + (f"#{code}" if _CODE_RE.match(code) else "")
        winintegration.open_url(url)
        return _ok()

    def open_page(self, key: str) -> dict[str, Any]:
        url = WEB_PAGES.get(str(key))
        if not url:
            return _fail("invalid", self._lang())
        winintegration.open_url(url)
        return _ok()

    # ------------------------------------------------------------------ ajustes
    def choose_folder(self) -> dict[str, Any]:
        import webview

        current = self._s.settings.get().download_dir
        start = current if Path(current).exists() else str(paths.downloads_dir())
        result = self._ui_thread(lambda: self._s.window.create_file_dialog(webview.FileDialog.FOLDER, directory=start))
        if not result:
            return {"ok": False}
        folder = result[0] if isinstance(result, (list, tuple)) else result
        s = self._s.settings.update({"download_dir": str(folder)})
        self._s.emit_settings()
        return _ok(settings=s.to_dict())

    def choose_cookies_file(self) -> dict[str, Any]:
        import webview

        types = ("Cookies (*.txt)", "Todos los archivos (*.*)")
        result = self._ui_thread(lambda: self._s.window.create_file_dialog(
            webview.FileDialog.OPEN, directory=str(paths.downloads_dir()), file_types=types))
        if not result:
            return {"ok": False}
        path = result[0] if isinstance(result, (list, tuple)) else result
        s = self._s.settings.update({"cookies_file": str(path)})
        self._s.emit_settings()
        return _ok(settings=s.to_dict())

    def clear_cookies_file(self) -> dict[str, Any]:
        s = self._s.settings.update({"cookies_file": ""})
        self._s.emit_settings()
        return _ok(settings=s.to_dict())

    def save_settings(self, patch: dict[str, Any] | None = None) -> dict[str, Any]:
        if not isinstance(patch, dict) or set(patch) & _PROTECTED_SETTINGS:
            return _fail("invalid", self._lang())
        before = self._s.settings.get()
        try:
            s = self._s.settings.update(patch)
        except ValueError as exc:
            return _fail("invalid", self._lang(), str(exc))
        if s.engine_channel != before.engine_channel:
            self.engine_update(force=True)
        self._s.emit_settings()
        return _ok(settings=s.to_dict())

    def read_clipboard(self) -> dict[str, Any]:
        text = winintegration.read_clipboard_text() or ""
        return _ok(url=validate_url(text) if text.strip() else None)

    # ------------------------------------------------------------------ historial
    def history(self, query: str = "") -> dict[str, Any]:
        return _ok(items=self._s.history.list(str(query or "")))

    def history_remove(self, item_id: str) -> dict[str, Any]:
        self._s.history.remove(str(item_id))
        return _ok()

    def history_clear(self) -> dict[str, Any]:
        self._s.history.clear()
        return _ok()

    # ------------------------------------------------------------------ actualizaciones de la app y cierre
    def check_app_update(self) -> dict[str, Any]:
        view = self._s.updater.check(force=True)
        self._s.update_view = view
        return _ok(update=view)

    def apply_app_update(self) -> dict[str, Any]:
        if self._s.downloads.active_count():
            return _fail("busy", self._lang())
        try:
            outcome = self._s.updater.apply()
        except Exception as exc:  # noqa: BLE001
            log.exception("No se pudo aplicar la actualización")
            return _fail("unknown", self._lang(), str(exc))
        if outcome == "installer":
            winintegration.open_url(WEB_PAGES["download"])
            return _ok(outcome="installer")
        relaunch()
        self._s.force_quit = True
        self._s.run_bg("close", lambda: self._s.window.destroy())
        return _ok(outcome="restart")

    def confirm_close(self) -> dict[str, Any]:
        self._s.force_quit = True
        self._s.run_bg("close", lambda: self._s.window.destroy())
        return _ok()
