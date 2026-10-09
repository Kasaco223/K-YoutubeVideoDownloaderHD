"""Integración con Windows: AppUserModelID, portapapeles, abrir archivos, suspensión, parpadeo y toasts."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from .constants import APP_ID, APP_NAME
from .util import log

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _user32.OpenClipboard.argtypes = [wintypes.HWND]
    _user32.OpenClipboard.restype = wintypes.BOOL
    _user32.GetClipboardData.argtypes = [wintypes.UINT]
    _user32.GetClipboardData.restype = wintypes.HANDLE
    _user32.CloseClipboard.restype = wintypes.BOOL
    _user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
    _user32.IsClipboardFormatAvailable.restype = wintypes.BOOL
    _kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    _kernel32.GlobalLock.restype = ctypes.c_void_p
    _kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    _kernel32.SetThreadExecutionState.argtypes = [wintypes.DWORD]
    _kernel32.SetThreadExecutionState.restype = wintypes.DWORD

    class _FLASHWINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.UINT), ("hwnd", wintypes.HWND), ("dwFlags", wintypes.DWORD),
                    ("uCount", wintypes.UINT), ("dwTimeout", wintypes.DWORD)]

CF_UNICODETEXT = 13
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001


def set_app_id() -> None:
    if IS_WINDOWS:
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
        except OSError:
            pass


def read_clipboard_text(max_len: int = 4096) -> str | None:
    """Texto del portapapeles (solo lectura, nunca se registra en los logs)."""
    if not IS_WINDOWS:
        return None
    for _ in range(5):
        if _user32.OpenClipboard(None):
            break
        _kernel32.Sleep(20)
    else:
        return None
    try:
        if not _user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
            return None
        handle = _user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return None
        ptr = _kernel32.GlobalLock(handle)
        if not ptr:
            return None
        try:
            return ctypes.wstring_at(ptr)[:max_len]
        finally:
            _kernel32.GlobalUnlock(handle)
    finally:
        _user32.CloseClipboard()


def open_path(path: Path) -> None:
    if IS_WINDOWS:
        os.startfile(str(path))  # noqa: S606 - abre con la app asociada del usuario
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def show_in_folder(path: Path) -> None:
    if IS_WINDOWS:
        subprocess.Popen(["explorer.exe", "/select,", str(path)], creationflags=0x08000000)
    else:
        open_path(path.parent)


def open_url(url: str) -> None:
    import webbrowser

    if url.startswith(("https://", "http://")):
        webbrowser.open(url)


def prevent_sleep(active: bool) -> None:
    """Evita que la PC se suspenda mientras hay descargas (por hilo: llamar siempre desde el mismo)."""
    if IS_WINDOWS:
        _kernel32.SetThreadExecutionState(ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if active else 0))


def flash_window(hwnd: int) -> None:
    if not IS_WINDOWS or not hwnd:
        return
    info = _FLASHWINFO(ctypes.sizeof(_FLASHWINFO), hwnd, 0x0000000F, 3, 0)  # FLASHW_ALL | FLASHW_TIMERNOFG
    _user32.FlashWindowEx(ctypes.byref(info))


def foreground_hwnd() -> int:
    return int(_user32.GetForegroundWindow() or 0) if IS_WINDOWS else 0


_toaster = None


def notify(title: str, message: str) -> None:
    """Notificación de Windows si `windows-toasts` está disponible; si no, no hace nada."""
    global _toaster
    try:
        from windows_toasts import Toast, WindowsToaster  # type: ignore[import-not-found]
    except Exception:  # noqa: BLE001 - dependencia opcional
        return
    try:
        if _toaster is None:
            _toaster = WindowsToaster(APP_NAME)
        toast = Toast()
        toast.text_fields = [title, message]
        _toaster.show_toast(toast)
    except Exception as exc:  # noqa: BLE001
        log.debug("No se pudo mostrar la notificación: %s", exc)
