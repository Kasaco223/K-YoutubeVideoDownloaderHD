"""Un único hilo envía los eventos a la UI con `run_js`, agrupados y a ≤10 Hz.

`run_js` es bloqueante y se marshalea al hilo de la ventana: llamarlo desde varios hilos o desde
callbacks de la UI puede interbloquear. Por eso todo pasa por esta cola, que conserva solo el último
evento de cada clave (p. ej. el progreso más reciente de cada descarga).
"""

from __future__ import annotations

import json
import threading
from collections import OrderedDict
from typing import Any

from .util import log

INTERVAL = 0.1
MAX_BATCH = 50


class UiPump:
    def __init__(self):
        self._window = None
        self._pending: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._lock = threading.Lock()
        self._ready = threading.Event()
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._seq = 0
        self._thread = threading.Thread(target=self._loop, daemon=True, name="kd-uipump")
        self._thread.start()

    def attach(self, window) -> None:
        self._window = window

    def ready(self) -> None:
        """La UI llamó a ui_ready(): ya existe window.kd.emit."""
        self._ready.set()
        self._wake.set()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()

    def emit(self, event: dict[str, Any], key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._seq += 1
                key = f"_{self._seq}"
            self._pending.pop(key, None)
            self._pending[key] = event
        self._wake.set()

    def _loop(self) -> None:
        while not self._stop.is_set():
            self._wake.wait(1.0)
            if self._stop.is_set():
                break
            if not self._ready.is_set() or self._window is None:
                continue
            self._wake.clear()
            with self._lock:
                batch = []
                while self._pending and len(batch) < MAX_BATCH:
                    batch.append(self._pending.popitem(last=False)[1])
            if batch:
                script = "".join(f"window.kd&&window.kd.emit({json.dumps(ev, ensure_ascii=True)});" for ev in batch)
                try:
                    self._window.run_js(script)
                except Exception as exc:  # noqa: BLE001 - la ventana pudo cerrarse
                    log.debug("run_js falló: %s", exc)
                if self._pending:
                    self._wake.set()
            self._stop.wait(INTERVAL)
