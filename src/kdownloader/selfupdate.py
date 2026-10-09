"""Autoactualización de la app: lee latest.json del último Release y aplica el zip de código (~1 MB).

Si cambió el runtime de Python (campo `runtime`), no se actualiza en caliente: se abre la página de
descarga para usar el instalador nuevo.
"""

from __future__ import annotations

import http.client
import json
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from typing import Any

from . import __version__, paths
from .constants import LATEST_JSON_URL, WEB_PAGES
from .engine import fetch
from .util import log, read_json, write_json_atomic

CHECK_EVERY = 24 * 3600
_VER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-rc\.(\d+))?$")


def _ver(v: str) -> tuple[int, ...]:
    """'2.1.0' > '2.1.0-rc.2' > '2.1.0-rc.1' > '2.0.9'. Versiones raras valen (0,0,0)."""
    m = _VER_RE.match(str(v).strip())
    if not m:
        return (0, 0, 0, 0)
    major, minor, patch, rc = m.groups()
    return int(major), int(minor), int(patch), int(rc) if rc else 10**6


def runtime_id(root: Path | None) -> str | None:
    if root is None:
        return None
    data = read_json(root / "runtime" / "kd-runtime.json", default={}) or {}
    return data.get("runtime_id")


class SelfUpdater:
    def __init__(self, state_path: Path):
        self.state_path = state_path
        self.state: dict[str, Any] = read_json(state_path, default={}) or {}
        self.latest: dict[str, Any] | None = None

    def check(self, force: bool = False) -> dict[str, Any] | None:
        """Devuelve UpdateView si hay una versión más nueva (o None)."""
        if not force and time.time() - float(self.state.get("checked_at", 0)) < CHECK_EVERY:
            cached = self.state.get("latest")
            return self._view(cached) if cached else None
        try:
            data = json.loads(fetch.get_text(LATEST_JSON_URL, timeout=15, limit=64_000))
        except (OSError, ValueError, http.client.HTTPException) as exc:
            log.info("No se pudo consultar actualizaciones: %s", exc)
            return None
        if not self._valid(data):
            return None
        self.state = {"checked_at": time.time(), "latest": data}
        write_json_atomic(self.state_path, self.state)
        return self._view(data)

    @staticmethod
    def _valid(data: Any) -> bool:
        if not isinstance(data, dict) or not _VER_RE.match(str(data.get("version", ""))):
            return False
        app = data.get("app")
        return isinstance(app, dict) and str(app.get("url", "")).startswith("https://github.com/") and \
            re.fullmatch(r"[0-9a-fA-F]{64}", str(app.get("sha256", ""))) is not None

    def _view(self, data: dict[str, Any]) -> dict[str, Any] | None:
        if not self._valid(data) or _ver(data["version"]) <= _ver(__version__):
            return None
        self.latest = data
        return {"version": data["version"], "notes_url": data.get("notes_url") or WEB_PAGES["releases"]}

    def apply(self) -> str:
        """Aplica la actualización. Devuelve "restart" (zip aplicado) o "installer" (hay que reinstalar)."""
        data = self.latest or self.state.get("latest")
        if not data or not self._valid(data):
            raise RuntimeError("No hay actualización disponible")
        root = paths.install_root()
        if root is None:
            raise RuntimeError("La app no está instalada (modo desarrollo)")
        if data.get("runtime") and data.get("runtime") != runtime_id(root):
            return "installer"
        version = data["version"]
        archive = paths.updates_dir() / f"kd-app-{version}.zip"
        fetch.download(data["app"]["url"], archive, expected_sha256=data["app"]["sha256"], timeout=60)
        staging = root / "app" / f".{version}.staging"
        shutil.rmtree(staging, ignore_errors=True)
        with zipfile.ZipFile(archive) as z:
            for info in z.infolist():
                name = info.filename.replace("\\", "/")
                prefix = f"app/{version}/"
                if not name.startswith(prefix) or info.is_dir():
                    continue
                target = (staging / name[len(prefix):]).resolve()
                if not str(target).startswith(str(staging.resolve())):
                    raise RuntimeError("Ruta inválida en el paquete de actualización")
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(info) as src, open(target, "wb") as out:
                    shutil.copyfileobj(src, out)
        if not (staging / "kdownloader" / "__init__.py").exists():
            shutil.rmtree(staging, ignore_errors=True)
            raise RuntimeError("El paquete de actualización está incompleto")
        final = root / "app" / version
        shutil.rmtree(final, ignore_errors=True)
        staging.rename(final)
        tmp = root / "current.tmp"
        tmp.write_text(version, encoding="utf-8")
        tmp.replace(root / "current")
        archive.unlink(missing_ok=True)
        log.info("Actualizada a %s", version)
        return "restart"


def relaunch() -> None:
    """Abre una nueva instancia con el lanzador instalado. Con --after-update espera a que esta se cierre."""
    root = paths.install_root()
    if root is None:
        return
    pythonw = root / "runtime" / "pythonw.exe"
    flags = (0x00000008 | 0x00000200) if sys.platform == "win32" else 0  # DETACHED_PROCESS | NEW_PROCESS_GROUP
    subprocess.Popen([str(pythonw), str(root / "launch.pyw"), "--after-update"], cwd=str(root),
                     creationflags=flags, close_fds=True)
