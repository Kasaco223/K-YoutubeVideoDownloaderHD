"""Descargas HTTP verificadas, sin dependencias externas.

- `latest_tag` resuelve la última versión de un repo siguiendo el redirect de /releases/latest (sin cuota de API).
- `download` escribe a un `.part`, calcula SHA-256 al vuelo y solo renombra si el hash coincide.
"""

from __future__ import annotations

import hashlib
import re
import threading
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

from ..constants import USER_AGENT

CHUNK = 256 * 1024
_HEX64 = re.compile(r"\b([0-9a-fA-F]{64})\b")


class Cancelled(Exception):
    """El usuario o la app cancelaron la descarga."""


class IntegrityError(Exception):
    """El archivo descargado no coincide con el hash publicado."""


def _request(url: str, method: str = "GET") -> urllib.request.Request:
    return urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method=method)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def latest_tag(repo: str, timeout: float = 30) -> str:
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        opener.open(_request(f"https://github.com/{repo}/releases/latest", "HEAD"), timeout=timeout)
    except urllib.error.HTTPError as exc:
        location = exc.headers.get("Location", "")
        m = re.search(r"/releases/tag/([^/?#]+)$", location)
        if m:
            return urllib.request.unquote(m.group(1))
        raise RuntimeError(f"No se pudo resolver la última versión de {repo} ({exc.code})") from exc
    raise RuntimeError(f"Respuesta inesperada al consultar {repo}")


def get_text(url: str, timeout: float = 30, limit: int = 2_000_000) -> str:
    with urllib.request.urlopen(_request(url), timeout=timeout) as resp:
        return resp.read(limit).decode("utf-8", "replace")


def find_sha256(sums_text: str, filename: str | None = None) -> str | None:
    """Busca el hash de `filename` en un archivo de sumas (formato GNU o el de Get-FileHash).

    Sin `filename`, devuelve el primer hash del texto (archivos .sha256 de un solo elemento).
    """
    if filename:
        for line in sums_text.splitlines():
            parts = line.strip().split()
            if len(parts) >= 2 and parts[-1].lstrip("*") == filename and _HEX64.fullmatch(parts[0]):
                return parts[0].lower()
        return None
    m = _HEX64.search(sums_text)
    return m.group(1).lower() if m else None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def download(
    url: str,
    dest: Path,
    *,
    expected_sha256: str | None,
    on_progress: Callable[[int, int], None] | None = None,
    cancel: threading.Event | None = None,
    timeout: float = 60,
) -> str:
    """Descarga `url` a `dest` verificando SHA-256. Devuelve el hash. Nunca deja un archivo inválido en `dest`."""
    if not expected_sha256:
        raise IntegrityError("No hay hash publicado para verificar la descarga")
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    h = hashlib.sha256()
    done = 0
    try:
        with urllib.request.urlopen(_request(url), timeout=timeout) as resp, open(part, "wb") as out:
            total = int(resp.headers.get("Content-Length") or 0)
            if on_progress:
                on_progress(0, total)
            while True:
                if cancel is not None and cancel.is_set():
                    raise Cancelled()
                chunk = resp.read(CHUNK)
                if not chunk:
                    break
                out.write(chunk)
                h.update(chunk)
                done += len(chunk)
                if on_progress:
                    on_progress(done, total)
        digest = h.hexdigest()
        if digest != expected_sha256.lower():
            raise IntegrityError(f"Hash distinto: esperado {expected_sha256[:12]}…, obtenido {digest[:12]}…")
        part.replace(dest)
        return digest
    finally:
        if part.exists():
            try:
                part.unlink()
            except OSError:
                pass
