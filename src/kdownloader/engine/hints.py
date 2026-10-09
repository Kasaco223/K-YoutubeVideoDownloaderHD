"""Pistas remotas del motor (engine.json en el repo): permiten empujar arreglos sin publicar una versión.

Lista blanca estricta: nunca se aceptan URLs ni argumentos arbitrarios.
"""

from __future__ import annotations

import http.client
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..util import log, read_json, write_json_atomic
from .fetch import get_text
from .versions import parse_ytdlp

_CLIENT_RE = re.compile(r"^-?[a-z_]+(,-?[a-z_]+)*$")
CHECK_EVERY = 24 * 3600


@dataclass
class Hints:
    min_ytdlp: dict[str, str] = field(default_factory=dict)
    youtube_player_client: str | None = None
    notice: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"min_ytdlp": self.min_ytdlp, "youtube_player_client": self.youtube_player_client,
                "notice": self.notice}


def validate(raw: Any) -> Hints:
    """Convierte el JSON remoto en Hints, descartando todo lo que no pase la validación."""
    hints = Hints()
    if not isinstance(raw, dict) or raw.get("schema") != 1:
        return hints
    mins = raw.get("min_ytdlp")
    if isinstance(mins, dict):
        for channel in ("nightly", "stable"):
            value = mins.get(channel)
            if isinstance(value, str) and parse_ytdlp(value):
                hints.min_ytdlp[channel] = value
    client = raw.get("youtube_player_client")
    if isinstance(client, str) and len(client) <= 120 and _CLIENT_RE.fullmatch(client):
        hints.youtube_player_client = client
    notice = raw.get("notice")
    if isinstance(notice, dict):
        for lang in ("es", "en"):
            text = notice.get(lang)
            if isinstance(text, str) and text.strip():
                hints.notice[lang] = text.strip()[:280]
    return hints


class HintsStore:
    def __init__(self, cache_path: Path, url: str):
        self.cache_path = cache_path
        self.url = url
        cached = read_json(cache_path, default={})
        if not isinstance(cached, dict):
            cached = {}
        try:
            self.fetched_at = float(cached.get("fetched_at") or 0)
        except (TypeError, ValueError):
            self.fetched_at = 0.0
        self.hints = validate(cached.get("data"))

    def refresh(self, force: bool = False) -> Hints:
        if not force and time.time() - self.fetched_at < CHECK_EVERY:
            return self.hints
        try:
            data = json.loads(get_text(self.url, timeout=15, limit=64_000))
        except (OSError, ValueError, http.client.HTTPException) as exc:
            log.info("No se pudieron leer las pistas del motor: %s", exc)
            return self.hints
        self.hints = validate(data)
        self.fetched_at = time.time()
        write_json_atomic(self.cache_path, {"fetched_at": self.fetched_at, "data": data})
        return self.hints
