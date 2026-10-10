"""Fixtures compartidas de la suite.

- Cada prueba corre con su propia carpeta de datos (KD_DATA_DIR) y sin herramientas del sistema.
- `make_format` / `make_info` / `make_playlist` arman diccionarios con la forma de `yt-dlp -J`.
- `http_server` levanta un servidor HTTP local (en un hilo) con rutas programables.
"""

from __future__ import annotations

import http.server
import json
import sys
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
YTDLP_FIXTURES = FIXTURES / "ytdlp"


@pytest.fixture(autouse=True)
def _isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Aísla cada prueba: datos en tmp_path y nunca FFmpeg/Deno del sistema."""
    data = tmp_path / "kd-data"
    monkeypatch.setenv("KD_DATA_DIR", str(data))
    monkeypatch.setenv("KD_NO_SYSTEM_TOOLS", "1")
    return data


@pytest.fixture
def data_dir(_isolated_env: Path) -> Path:
    return _isolated_env


@pytest.fixture
def python_exe() -> Path:
    """Intérprete para lanzar procesos hijos en las pruebas (el mismo que corre pytest)."""
    return Path(sys.executable)


# ----------------------------------------------------------------------------- info dicts de yt-dlp


def _make_format(format_id: str, *, height: int | None = None, width: int | None = None,
                 vcodec: str = "none", acodec: str = "none", ext: str = "mp4", fps: float | None = None,
                 dynamic_range: str | None = None, filesize: int | None = None, **extra: Any) -> dict[str, Any]:
    fmt: dict[str, Any] = {
        "format_id": format_id,
        "ext": ext,
        "vcodec": vcodec,
        "acodec": acodec,
        "protocol": "https",
        "url": f"https://media.invalid/{format_id}",
    }
    if height is not None:
        fmt["height"] = height
        fmt["width"] = width if width is not None else round(height * 16 / 9)
    elif width is not None:
        fmt["width"] = width
    if fps is not None:
        fmt["fps"] = fps
    if vcodec != "none":
        fmt["dynamic_range"] = dynamic_range or "SDR"
    if filesize is not None:
        fmt["filesize"] = filesize
    fmt.update(extra)
    return fmt


def _make_info(formats: list[dict[str, Any]] | None = None, *, video_id: str = "abcdefghijk",
               url: str | None = None, title: str = "Video de prueba", **extra: Any) -> dict[str, Any]:
    info: dict[str, Any] = {
        "id": video_id,
        "title": title,
        "channel": "Canal de prueba",
        "uploader": "Uploader de prueba",
        "duration": 120,
        "webpage_url": url or f"https://www.youtube.com/watch?v={video_id}",
        "original_url": url or f"https://www.youtube.com/watch?v={video_id}",
        "extractor": "youtube",
        "extractor_key": "Youtube",
        "thumbnail": f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",
        "thumbnails": [],
        "is_live": False,
        "age_limit": 0,
        "formats": formats if formats is not None else [
            _make_format("140", acodec="mp4a.40.2", ext="m4a"),
            _make_format("299", height=1080, vcodec="avc1.64002A", fps=60),
        ],
    }
    info.update(extra)
    return info


def _make_playlist(entries: list[dict[str, Any] | None], *, playlist_id: str = "PLtest",
                   title: str = "Lista de prueba", **extra: Any) -> dict[str, Any]:
    info: dict[str, Any] = {
        "_type": "playlist",
        "id": playlist_id,
        "title": title,
        "channel": "Canal de la lista",
        "webpage_url": f"https://www.youtube.com/playlist?list={playlist_id}",
        "extractor_key": "YoutubeTab",
        "entries": entries,
    }
    info.update(extra)
    return info


@pytest.fixture
def make_format() -> Callable[..., dict[str, Any]]:
    return _make_format


@pytest.fixture
def make_info() -> Callable[..., dict[str, Any]]:
    return _make_info


@pytest.fixture
def make_playlist() -> Callable[..., dict[str, Any]]:
    return _make_playlist


@pytest.fixture
def bbb_info() -> dict[str, Any]:
    """Info mínima de Big Buck Bunny (aqz-KE-bpKQ) con la escalera de `visionos`, armada a mano."""
    return json.loads((FIXTURES / "info_bbb_min.json").read_text(encoding="utf-8"))


def read_fixture_lines(name: str) -> list[str]:
    """Líneas de una transcripción real (los \\r de las barras de FFmpeg cuentan como saltos)."""
    return (YTDLP_FIXTURES / name).read_text(encoding="utf-8").splitlines()


@pytest.fixture
def fixture_lines() -> Callable[[str], list[str]]:
    return read_fixture_lines


# ----------------------------------------------------------------------------- servidor HTTP local


@dataclass
class Route:
    status: int = 200
    body: bytes = b""
    headers: dict[str, str] = field(default_factory=dict)
    chunk_delay: float = 0.0  # pausa entre bloques de 64 KB (para probar cancelaciones)


class LocalServer:
    """Servidor HTTP en 127.0.0.1 con rutas exactas; registra cada petición recibida."""

    def __init__(self) -> None:
        self.routes: dict[str, Route] = {}
        self.requests: list[tuple[str, str]] = []
        server = self

        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args: Any) -> None:  # silencio en la salida de pytest
                pass

            def _serve(self, with_body: bool) -> None:
                server.requests.append((self.command, self.path))
                route = server.routes.get(self.path)
                if route is None:
                    route = Route(status=404, body=b"not found")
                self.send_response(route.status)
                headers = {"Content-Length": str(len(route.body)), **route.headers}
                for key, value in headers.items():
                    self.send_header(key, value)
                self.end_headers()
                if not with_body:
                    return
                try:
                    if route.chunk_delay:
                        for i in range(0, len(route.body), 65536):
                            self.wfile.write(route.body[i:i + 65536])
                            self.wfile.flush()
                            time.sleep(route.chunk_delay)
                    else:
                        self.wfile.write(route.body)
                except (ConnectionError, OSError):
                    pass  # el cliente cortó (cancelación): es lo esperado

            def do_GET(self) -> None:
                self._serve(True)

            def do_HEAD(self) -> None:
                self._serve(False)

        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.httpd.daemon_threads = True
        self.port = self.httpd.server_address[1]
        self.base = f"http://127.0.0.1:{self.port}"
        self._thread = threading.Thread(target=self.httpd.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True,
                                        name="kd-test-http")

    def start(self) -> LocalServer:
        self._thread.start()
        return self

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    def add(self, path: str, body: bytes | str = b"", status: int = 200, headers: dict[str, str] | None = None,
            chunk_delay: float = 0.0) -> str:
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.routes[path] = Route(status=status, body=body, headers=headers or {}, chunk_delay=chunk_delay)
        return self.base + path

    def url(self, path: str) -> str:
        return self.base + path

    def remap(self, url: str) -> str:
        """https://host/ruta → http://127.0.0.1:<puerto>/host/ruta (para simular sitios remotos)."""
        scheme, _, rest = url.partition("://")
        assert scheme in ("http", "https"), url
        return f"{self.base}/{rest}"

    def add_remote(self, url: str, body: bytes | str = b"", status: int = 200) -> str:
        """Publica `body` como si estuviera en la URL remota `url`."""
        local = self.remap(url)
        return self.add(local[len(self.base):], body, status)

    def hits(self, path_fragment: str) -> int:
        return sum(1 for _, p in self.requests if path_fragment in p)


@pytest.fixture
def http_server() -> Iterator[LocalServer]:
    server = LocalServer().start()
    try:
        yield server
    finally:
        server.stop()
