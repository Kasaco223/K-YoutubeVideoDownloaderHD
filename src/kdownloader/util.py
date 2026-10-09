"""Utilidades compartidas: JSON atómico, registro de eventos y helpers de texto."""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
import re
import secrets
import tempfile
from pathlib import Path
from typing import Any

log = logging.getLogger("kdownloader")

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def short_id() -> str:
    """Identificador de 8 caracteres para trabajos (mantiene cortas las rutas temporales)."""
    return secrets.token_hex(4)


def read_json(path: Path, default: Any = None) -> Any:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except (OSError, ValueError) as exc:
        log.warning("No se pudo leer %s: %s", path, exc)
        return default


def write_json_atomic(path: Path, data: Any) -> None:
    """Escribe a un temporal en la misma carpeta y lo reemplaza: nunca deja un JSON a medias."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def setup_logging(logs_dir: Path, debug: bool = False) -> None:
    handler = logging.handlers.RotatingFileHandler(
        logs_dir / "app.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(threadName)s %(name)s: %(message)s"))
    root = logging.getLogger("kdownloader")
    root.handlers[:] = [handler]
    root.setLevel(logging.DEBUG if debug else logging.INFO)
    root.propagate = False


def human_size(num: float | None) -> str:
    if not num:
        return ""
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(num)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.0f} {unit}" if unit in ("B", "KB") else f"{size:.1f} {unit}"
        size /= 1024
    return ""
