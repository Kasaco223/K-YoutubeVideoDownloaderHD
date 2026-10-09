"""Instancia única: un mutex con nombre y un named pipe para pasarle enlaces a la ventana abierta."""

from __future__ import annotations

import getpass
import hashlib
import secrets
import sys
import threading
import time
from collections.abc import Callable
from multiprocessing.connection import Client, Listener
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .constants import MUTEX_NAME, PIPE_PREFIX, PROTOCOL
from .util import log

IS_WINDOWS = sys.platform == "win32"
ERROR_ALREADY_EXISTS = 183


def parse_protocol(uri: str) -> str | None:
    """`kdownloader://download?url=<URL>` → URL http(s) validada; cualquier otra cosa → None."""
    if not isinstance(uri, str) or len(uri) > 8192:
        return None
    parsed = urlparse(uri.strip())
    if parsed.scheme.lower() != PROTOCOL:
        return None
    target = (parse_qs(parsed.query).get("url") or [""])[0].strip()
    t = urlparse(target)
    if t.scheme not in ("http", "https") or not t.hostname or len(target) > 4096:
        return None
    return target


def url_from_argv(argv: list[str]) -> str | None:
    for i, arg in enumerate(argv):
        if arg == "--protocol" and i + 1 < len(argv):
            return parse_protocol(argv[i + 1])
        if arg.startswith(f"{PROTOCOL}:"):
            return parse_protocol(arg)
    return None


def _pipe_name() -> str:
    user = hashlib.sha1(getpass.getuser().encode("utf-8", "replace")).hexdigest()[:12]
    return f"{PIPE_PREFIX}{user}"


def _authkey(data_dir: Path) -> bytes:
    path = data_dir / "instance.key"
    try:
        key = path.read_bytes()
        if len(key) >= 32:
            return key
    except OSError:
        pass
    key = secrets.token_bytes(32)
    try:
        path.write_bytes(key)
    except OSError:
        pass
    return key


class InstanceGuard:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self._mutex = None
        self._listener: Listener | None = None
        self._on_url: Callable[[str], None] | None = None
        self._stop = threading.Event()

    def acquire(self) -> bool:
        """True si esta es la primera instancia."""
        if not IS_WINDOWS:
            return True
        import ctypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateMutexW.restype = ctypes.c_void_p
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        if self._mutex:
            kernel32.CloseHandle(self._mutex)
        self._mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
        return ctypes.get_last_error() != ERROR_ALREADY_EXISTS

    def wait_for_release(self, timeout: float = 15.0) -> bool:
        """Tras una actualización: espera a que la instancia anterior termine de cerrarse."""
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if self.acquire():
                return True
            time.sleep(0.5)
        return False

    def forward(self, argv: list[str]) -> bool:
        """Envía los argumentos a la instancia abierta (que se trae al frente)."""
        if IS_WINDOWS:
            import ctypes

            ctypes.windll.user32.AllowSetForegroundWindow(-1)  # ASFW_ANY: deja que la otra ventana pase al frente
        try:
            with Client(_pipe_name(), family="AF_PIPE", authkey=_authkey(self.data_dir)) as conn:
                conn.send({"argv": argv[:8]})
            return True
        except OSError as exc:
            log.warning("No se pudo contactar a la instancia abierta: %s", exc)
            return False

    def serve(self, on_message: Callable[[dict], None]) -> None:
        if not IS_WINDOWS:
            return

        def loop() -> None:
            try:
                self._listener = Listener(_pipe_name(), family="AF_PIPE", authkey=_authkey(self.data_dir))
            except OSError as exc:
                log.warning("No se pudo abrir el canal de instancia única: %s", exc)
                return
            while not self._stop.is_set():
                try:
                    with self._listener.accept() as conn:
                        msg = conn.recv()
                        if isinstance(msg, dict):
                            on_message(msg)
                except Exception as exc:  # noqa: BLE001 - un cliente defectuoso no debe tumbar el canal
                    if self._stop.is_set():
                        break
                    log.debug("Mensaje de instancia descartado: %s", exc)

        threading.Thread(target=loop, daemon=True, name="kd-instance").start()

    def close(self) -> None:
        self._stop.set()
        if self._listener is not None:
            try:
                self._listener.close()
            except OSError:
                pass
