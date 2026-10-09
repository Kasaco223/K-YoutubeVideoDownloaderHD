"""Ejecución de yt-dlp: análisis de enlaces, simulación de opciones y descargas con progreso.

yt-dlp corre como zipapp con el Python oficial (`python -I -X utf8 yt-dlp.pyz …`), dentro de un Job
Object (ver process.py). Toda la salida estructurada usa el protocolo KDL (ver progress.py).
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import threading
from collections import deque
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ..util import log
from . import errors
from .process import ManagedProcess
from .progress import PRINT_FILE, PROGRESS_TEMPLATE_DL, PROGRESS_TEMPLATE_PP, KdlEvent, parse_line

YOUTUBE_HOSTS = ("youtube.com", "youtu.be", "youtube-nocookie.com")


@dataclass
class EngineConfig:
    python: Path
    ytdlp: Path
    ffmpeg_dir: Path | None
    deno: Path | None
    cache_dir: Path
    cookies_file: str | None = None
    youtube_player_client: str | None = None


class EngineFailure(Exception):
    def __init__(self, error: errors.EngineError, lines: list[str]):
        super().__init__(error.message)
        self.error = error
        self.lines = lines


def is_youtube(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == h or host.endswith("." + h) for h in YOUTUBE_HOSTS)


def base_args(cfg: EngineConfig, url: str = "", use_cookies: bool | None = None) -> list[str]:
    args = [str(cfg.python), "-I", "-X", "utf8", str(cfg.ytdlp),
            "--ignore-config", "--no-update", "--no-plugin-dirs", "--color", "never",
            "--cache-dir", str(cfg.cache_dir)]
    if cfg.deno:
        args += ["--js-runtimes", f"deno:{cfg.deno}"]
    if cfg.ffmpeg_dir:
        args += ["--ffmpeg-location", str(cfg.ffmpeg_dir)]
    youtube = is_youtube(url)
    # Las cookies desactivan el cliente `visionos` de YouTube: solo se usan ahí si el usuario lo pide.
    if cfg.cookies_file and (use_cookies if use_cookies is not None else not youtube):
        args += ["--cookies", cfg.cookies_file]
    if youtube and cfg.youtube_player_client:
        args += ["--extractor-args", f"youtube:player_client={cfg.youtube_player_client}"]
    return args


def _run_collect(args: list[str], timeout: float, cancel: threading.Event | None) -> tuple[int, list[str], list[str]]:
    out: list[str] = []
    err: list[str] = []
    proc = ManagedProcess(args, on_stdout=out.append, on_stderr=err.append)
    done = threading.Event()

    def watchdog() -> None:
        while not done.wait(0.2):
            if cancel is not None and cancel.is_set():
                proc.kill()
                return

    threading.Thread(target=watchdog, daemon=True, name="kd-watch").start()
    try:
        rc = proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)
        raise TimeoutError("El análisis tardó demasiado") from None
    finally:
        done.set()
    if proc.killed:
        raise InterruptedError("Cancelado")
    return rc, out, err


def probe(cfg: EngineConfig, url: str, *, playlist: bool = False, timeout: float = 120,
          cancel: threading.Event | None = None, lang: str = "es") -> tuple[dict[str, Any], list[str]]:
    """Devuelve (info de yt-dlp, avisos). Lanza EngineFailure con el error ya clasificado."""
    args = base_args(cfg, url) + (["--yes-playlist", "--flat-playlist"] if playlist else ["--no-playlist"])
    args += ["-J", "--", url]
    rc, out, err = _run_collect(args, timeout, cancel)
    if rc != 0 or not out:
        raise EngineFailure(errors.classify(err + out, lang), err)
    text = "".join(out).strip()
    try:
        info = json.loads(text)
    except ValueError as exc:
        raise EngineFailure(errors.classify(err + ["ERROR: respuesta inválida del motor"], lang), err) from exc
    warnings = [ln for ln in err if ln.startswith("WARNING")]
    return info, warnings


SIM_PRINT = "%(.{format_id,height,width,fps,vcodec,acodec,ext,filesize,filesize_approx,dynamic_range})j"


def simulate(cfg: EngineConfig, info: dict[str, Any], choices: dict[str, list[str]],
             timeout: float = 60) -> dict[str, dict[str, Any] | None]:
    """Pregunta a yt-dlp qué formato elegiría cada opción, sin red ni descarga (--load-info-json)."""
    url = str(info.get("webpage_url") or info.get("original_url") or "")
    results: dict[str, dict[str, Any] | None] = {}
    with tempfile.TemporaryDirectory(prefix="kd-sim-") as tmp:
        path = Path(tmp) / "info.json"
        path.write_text(json.dumps(info), encoding="utf-8")

        def one(key: str, preset_args: list[str]) -> tuple[str, dict[str, Any] | None]:
            args = base_args(cfg, url) + ["--load-info-json", str(path), "--simulate", "--no-warnings",
                                          "--print", SIM_PRINT, *preset_args]
            try:
                rc, out, err = _run_collect(args, timeout, None)
            except (TimeoutError, InterruptedError):
                return key, None
            for line in reversed(out):
                line = line.strip()
                if line.startswith("{"):
                    try:
                        return key, json.loads(line)
                    except ValueError:
                        break
            log.info("Simulación %s sin resultado (rc=%s): %s", key, rc, err[-2:])
            return key, None

        with ThreadPoolExecutor(max_workers=min(4, len(choices) or 1)) as pool:
            for key, value in pool.map(lambda kv: one(*kv), choices.items()):
                results[key] = value
    return results


def summarize(info: dict[str, Any]) -> dict[str, Any]:
    """Resumen de la info de yt-dlp para la UI (sin URLs de medios)."""
    is_list = info.get("_type") == "playlist"
    thumbs = [t for t in info.get("thumbnails") or [] if str(t.get("url", "")).startswith("https://")]
    thumb = info.get("thumbnail") if str(info.get("thumbnail", "")).startswith("https://") else None
    if not thumb and thumbs:
        thumb = max(thumbs, key=lambda t: (t.get("preference") or 0, t.get("width") or 0)).get("url")
    out: dict[str, Any] = {
        "id": info.get("id"),
        "title": info.get("title") or info.get("id") or "",
        "uploader": info.get("channel") or info.get("uploader") or "",
        "duration": info.get("duration"),
        "thumbnail": thumb,
        "url": info.get("webpage_url") or info.get("original_url"),
        "extractor": info.get("extractor_key") or info.get("extractor"),
        "is_live": bool(info.get("is_live")),
        "age_limit": info.get("age_limit") or 0,
        "is_playlist": is_list,
    }
    if is_list:
        entries = []
        for e in info.get("entries") or []:
            if not isinstance(e, dict):
                continue
            entries.append({"id": e.get("id"), "title": e.get("title") or e.get("id"),
                            "url": e.get("url") or e.get("webpage_url"), "duration": e.get("duration")})
        out["entries"] = entries
        out["count"] = len(entries)
        out["total_duration"] = sum(e["duration"] or 0 for e in entries)
        return out
    heights: dict[int, dict[str, Any]] = {}
    for f in info.get("formats") or []:
        if (f.get("vcodec") or "none") == "none" or not f.get("height"):
            continue
        h = min(int(f.get("height") or 0), int(f.get("width") or 10**6))  # como `res` de yt-dlp: soporta verticales
        cur = heights.setdefault(h, {"height": h, "fps": 0, "hdr": False})
        cur["fps"] = max(cur["fps"], int(f.get("fps") or 0))
        cur["hdr"] = cur["hdr"] or (f.get("dynamic_range") not in (None, "SDR"))
    out["heights"] = sorted(heights.values(), key=lambda x: x["height"], reverse=True)
    out["max_height"] = out["heights"][0]["height"] if out["heights"] else 0
    out["has_video"] = bool(out["heights"])
    return out


def is_degraded(info: dict[str, Any]) -> bool:
    """YouTube entregó solo el formato 18 o ≤360p: señal de motor viejo o bloqueo (lo del 403 original)."""
    if not is_youtube(str(info.get("webpage_url") or "")) or info.get("is_live"):
        return False
    video = [f for f in info.get("formats") or [] if (f.get("vcodec") or "none") != "none"]
    if not video:
        return False
    ids = {str(f.get("format_id")) for f in video}
    max_h = max(min(int(f.get("height") or 0), int(f.get("width") or 10**6)) for f in video)
    return ids <= {"18"} or max_h <= 360 and (info.get("duration") or 0) > 0 and "18" in ids


@dataclass
class RunResult:
    returncode: int
    canceled: bool
    files: list[str] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)
    already_downloaded: bool = False


class DownloadRun:
    """Una ejecución de yt-dlp para un trabajo. `on_event(KdlEvent)` recibe el progreso."""

    def __init__(self, cfg: EngineConfig, url: str, choice_args: list[str], out_args: list[str], home: Path,
                 temp: Path, on_event: Callable[[KdlEvent], None], use_cookies: bool | None = None,
                 extra: list[str] | None = None):
        self.args = [
            *base_args(cfg, url, use_cookies),
            "--no-quiet", "--newline", "--progress", "--progress-delta", "0.5",
            "--progress-template", PROGRESS_TEMPLATE_DL, "--progress-template", PROGRESS_TEMPLATE_PP,
            "--print", PRINT_FILE,
            "-P", f"home:{home}", "-P", f"temp:{temp}", *out_args,
            "-N", "2", "--retries", "10", "--fragment-retries", "10",
            "--retry-sleep", "exp=1:20", "--retry-sleep", "fragment:exp=1:20",
            "--embed-metadata", "--embed-thumbnail", "--embed-chapters", "--no-playlist",
            *choice_args, *(extra or []), "--", url,
        ]
        self.on_event = on_event
        self.files: list[str] = []
        self.tail: deque[str] = deque(maxlen=400)
        self._proc: ManagedProcess | None = None
        self._lock = threading.Lock()

    def _line(self, line: str) -> None:
        ev = parse_line(line)
        if ev is None:
            self.tail.append(line)
            return
        if ev.kind == "file" and ev.path:
            self.files.append(ev.path)
        self.on_event(ev)

    def start(self) -> None:
        with self._lock:
            self._proc = ManagedProcess(self.args, on_stdout=self._line, on_stderr=self._line)

    def cancel(self) -> None:
        with self._lock:
            if self._proc:
                self._proc.kill()

    def wait(self) -> RunResult:
        assert self._proc is not None
        rc = self._proc.wait()
        lines = list(self.tail)
        return RunResult(returncode=rc, canceled=self._proc.killed, files=self.files, lines=lines,
                         already_downloaded=errors.is_already_downloaded(lines))
