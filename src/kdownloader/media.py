"""Análisis de enlaces para la UI: probe con autorreparación, simulación de opciones y tokens."""

from __future__ import annotations

import threading
from collections import OrderedDict
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

from . import paths
from .engine import presets, ytdlp
from .engine.binaries import EngineManager
from .engine.hints import HintsStore
from .settings import SettingsStore
from .util import log, short_id

MAX_TOKENS = 30
MP3_V0_BPS = 245_000  # bitrate medio de LAME V0, para estimar el tamaño del MP3


def validate_url(url: str) -> str | None:
    """Devuelve la URL limpia si es http(s) razonable; None si no."""
    if not isinstance(url, str):
        return None
    url = url.strip().split()[0] if url.strip() else ""
    if not url or len(url) > 4096:
        return None
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return None
    return url


def site_name(info: dict[str, Any], url: str) -> str:
    key = str(info.get("extractor_key") or "")
    if key.lower().startswith("youtube"):
        return "YouTube"
    if key and key.lower() != "generic":
        return key
    return (urlparse(url).hostname or "").removeprefix("www.")


def _vfam(codec: str | None) -> str | None:
    c = (codec or "none").lower()
    if c == "none":
        return None
    if c.startswith(("avc", "h264")):
        return "h264"
    if c.startswith(("vp9", "vp09")):
        return "vp9"
    if c.startswith(("av01", "av1")):
        return "av1"
    return "other"


def _afam(codec: str | None) -> str | None:
    c = (codec or "none").lower()
    if c == "none":
        return None
    if c.startswith(("mp4a", "aac")):
        return "aac"
    if c.startswith("opus"):
        return "opus"
    if c.startswith("mp3"):
        return "mp3"
    return "other"


def _size(fmt: dict[str, Any], duration: float | None = None) -> tuple[int | None, bool]:
    """Tamaño de un formato; si yt-dlp no lo trae (HLS), se estima con bitrate × duración."""
    if fmt.get("filesize"):
        return int(fmt["filesize"]), False
    if fmt.get("filesize_approx"):
        return int(fmt["filesize_approx"]), True
    tbr = fmt.get("tbr") or fmt.get("vbr") or fmt.get("abr")
    if tbr and duration:
        return int(float(tbr) * 1000 / 8 * float(duration)), True
    return None, True


def _has_size(fmt: dict[str, Any]) -> int:
    return 1 if (fmt.get("filesize") or fmt.get("filesize_approx")) else 0


def option_from_sim(key: str, sim: dict[str, Any] | None, kind: str, container: str,
                    duration: float | None) -> dict[str, Any]:
    opt: dict[str, Any] = {"key": key, "kind": kind, "container": container, "height": None, "fps": None,
                           "vcodec": None, "acodec": None, "hdr": False, "size": None, "size_approx": True,
                           "available": sim is not None}
    if not sim:
        return opt
    size, approx = _size(sim)
    if kind == "video":
        opt["height"] = min(int(sim.get("height") or 0), int(sim.get("width") or 10**6)) or None
        opt["fps"] = int(sim.get("fps") or 0) or None
        opt["vcodec"] = _vfam(sim.get("vcodec"))
        opt["hdr"] = sim.get("dynamic_range") not in (None, "SDR")
    opt["acodec"] = _afam(sim.get("acodec"))
    if container == "mp3":
        opt["acodec"] = "mp3"
        if duration:
            size, approx = int(duration * MP3_V0_BPS / 8), True
    opt["size"], opt["size_approx"] = size, approx
    return opt


def estimate_heights(info: dict[str, Any], summary: dict[str, Any], max_codec: str) -> list[dict[str, Any]]:
    """Opciones de "Más opciones": cada altura disponible con tamaño aproximado (sin lanzar yt-dlp)."""
    formats = info.get("formats") or []
    duration = summary.get("duration")
    audio = [f for f in formats if (f.get("vcodec") or "none") == "none" and (f.get("acodec") or "none") != "none"]

    def best_audio(prefer: str) -> dict[str, Any] | None:
        pool = [f for f in audio if _afam(f.get("acodec")) == prefer] or audio
        return max(pool, key=lambda f: (_has_size(f), f.get("tbr") or f.get("abr") or 0), default=None)

    out = []
    for h in summary.get("heights") or []:
        height = h["height"]
        container = "mp4" if height <= 1080 else "mkv"
        prefer = "h264" if height <= 1080 else ("vp9" if max_codec == "vp9" else "av1")
        cands = [f for f in formats if (f.get("vcodec") or "none") != "none"
                 and min(int(f.get("height") or 0), int(f.get("width") or 10**6)) == height]
        pool = [f for f in cands if _vfam(f.get("vcodec")) == prefer] or cands
        # Igual que yt-dlp: a igual fps se prefieren los formatos HTTPS (tamaño conocido) sobre HLS.
        video = max(pool, key=lambda f: (f.get("fps") or 0, _has_size(f), f.get("tbr") or 0), default=None)
        if not video:
            continue
        aud = best_audio("aac" if container == "mp4" else "opus") if (video.get("acodec") or "none") == "none" else None
        vs, _ = _size(video, duration)
        a_size, _ = _size(aud, duration) if aud else (0, True)
        total = (vs or 0) + (a_size or 0) or None
        out.append({"key": f"h{height}", "kind": "video", "container": container, "height": height,
                    "fps": int(video.get("fps") or 0) or None, "vcodec": _vfam(video.get("vcodec")),
                    "acodec": _afam((aud or video).get("acodec")), "hdr": bool(h.get("hdr")),
                    "size": total, "size_approx": True, "available": True})
    m4a = best_audio("aac")
    if m4a and _afam(m4a.get("acodec")) == "aac":
        size, approx = _size(m4a, duration)
        out.append({"key": "m4a", "kind": "audio", "container": "m4a", "height": None, "fps": None,
                    "vcodec": None, "acodec": "aac", "hdr": False, "size": size, "size_approx": approx,
                    "available": True})
    return out


class MediaService:
    def __init__(self, engine: EngineManager, settings: SettingsStore, hints: HintsStore,
                 config: Callable[[], ytdlp.EngineConfig], lang: Callable[[], str]):
        self.engine = engine
        self.settings = settings
        self.hints = hints
        self._config = config
        self._lang = lang
        self._lock = threading.Lock()
        self._cancel = threading.Event()
        self._tokens: OrderedDict[str, dict[str, Any]] = OrderedDict()

    def cancel(self) -> None:
        self._cancel.set()

    def get(self, token: str) -> dict[str, Any] | None:
        with self._lock:
            return self._tokens.get(token)

    def probe(self, url: str, playlist: bool = False) -> dict[str, Any]:
        """MediaView para la UI. Lanza ytdlp.EngineFailure (error clasificado) o ValueError."""
        clean = validate_url(url)
        if not clean:
            raise ValueError("invalid_url")
        self._cancel.clear()
        lang = self._lang()
        info, warnings = ytdlp.probe(self._config(), clean, playlist=playlist, cancel=self._cancel, lang=lang)
        degraded = ytdlp.is_degraded(info)
        if degraded and self.settings.get().auto_update_engine:
            log.info("Probe degradado: se actualiza el motor y se reintenta")
            channel = self.settings.get().engine_channel
            try:
                self.engine.check_updates(channel=channel, force=True,
                                          minimum=self.hints.hints.min_ytdlp.get(channel))
            except Exception:  # noqa: BLE001
                log.exception("No se pudo actualizar el motor")
            info, warnings = ytdlp.probe(self._config(), clean, playlist=playlist, cancel=self._cancel, lang=lang)
            degraded = ytdlp.is_degraded(info)
        summary = ytdlp.summarize(info)
        is_yt = ytdlp.is_youtube(str(summary.get("url") or clean))
        media: dict[str, Any] = {
            "token": short_id(), "id": summary.get("id"), "title": summary["title"], "uploader": summary["uploader"],
            "duration": summary.get("duration"), "thumbnail": summary.get("thumbnail"),
            "url": summary.get("url") or clean, "site": site_name(info, clean), "is_youtube": is_yt,
            "is_live": summary.get("is_live", False), "age_limit": summary.get("age_limit", 0),
            "is_playlist": summary["is_playlist"], "degraded": degraded,
            "warnings": [w.removeprefix("WARNING: ")[:300] for w in warnings[:5]],
        }
        if summary["is_playlist"]:
            entries = summary.get("entries") or []
            media.update(count=len(entries), total_duration=summary.get("total_duration"),
                         entries=[{"id": e.get("id"), "title": e.get("title"), "duration": e.get("duration"),
                                   "url": e.get("url")} for e in entries])
            media["options"] = [option_from_sim(k, {}, kind, cont, None) | {"available": True}
                                for k, kind, cont in (("recommended", "video", "mp4"), ("max", "video", "mkv"),
                                                      ("mp3", "audio", "mp3"))]
            media["more"] = []
        else:
            max_codec = self.settings.get().max_codec
            choices = {k: presets.build_args(presets.Choice(k), is_youtube=is_yt, max_codec=max_codec)
                       for k in presets.MAIN_PRESETS}
            sims = ytdlp.simulate(self._config(), info, choices)
            duration = summary.get("duration")
            has_video = summary.get("has_video", False)
            rec = sims.get("recommended") if has_video else None
            best = sims.get("max") if has_video else None
            media["options"] = [
                option_from_sim("recommended", rec, "video", "mp4", duration),
                option_from_sim("max", best, "video", "mkv", duration),
                option_from_sim("mp3", sims.get("mp3"), "audio", "mp3", duration),
            ]
            media["more"] = estimate_heights(info, summary, max_codec)
        with self._lock:
            self._tokens[media["token"]] = media
            while len(self._tokens) > MAX_TOKENS:
                self._tokens.popitem(last=False)
        return {k: v for k, v in media.items() if k != "entries"} | (
            {"entries": [{k: e[k] for k in ("id", "title", "duration")} for e in media.get("entries", [])[:200]]}
            if media["is_playlist"] else {})


def engine_config_factory(engine: EngineManager, settings: SettingsStore,
                          hints: HintsStore) -> Callable[[], ytdlp.EngineConfig]:
    def make() -> ytdlp.EngineConfig:
        path = engine.ytdlp_path()
        if path is None:
            raise RuntimeError("engine_not_ready")
        s = settings.get()
        return ytdlp.EngineConfig(python=paths.console_python(), ytdlp=path, ffmpeg_dir=engine.ffmpeg_dir(),
                                  deno=engine.deno_path(), cache_dir=paths.cache_dir(),
                                  cookies_file=s.cookies_file or None,
                                  youtube_player_client=hints.hints.youtube_player_client)
    return make
