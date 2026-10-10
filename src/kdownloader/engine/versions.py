"""Comparación de versiones de yt-dlp (AAAA.MM.DD[.HHMMSS]) y semver simple (Deno, FFmpeg)."""

from __future__ import annotations

import re

_YTDLP_RE = re.compile(r"^(\d{4})\.(\d{1,2})\.(\d{1,2})(?:\.(\d+))?$")
_SEMVER_RE = re.compile(r"^v?(\d+)(?:\.(\d+))?(?:\.(\d+))?")


def parse_ytdlp(version: str | None) -> tuple[int, int, int, int] | None:
    if not version:
        return None
    m = _YTDLP_RE.match(version.strip())
    if not m:
        return None
    y, mo, d, extra = m.groups()
    return int(y), int(mo), int(d), int(extra or 0)


def ytdlp_at_least(version: str | None, minimum: str | None) -> bool:
    """True si `version` es >= `minimum`. Sin mínimo, cualquier versión válida sirve."""
    v = parse_ytdlp(version)
    if v is None:
        return False
    m = parse_ytdlp(minimum)
    return m is None or v >= m


def parse_semver(version: str | None) -> tuple[int, int, int] | None:
    if not version:
        return None
    m = _SEMVER_RE.match(version.strip())
    if not m:
        return None
    return tuple(int(x or 0) for x in m.groups())  # type: ignore[return-value]


def semver_at_least(version: str | None, minimum: str) -> bool:
    v, m = parse_semver(version), parse_semver(minimum)
    return v is not None and m is not None and v >= m
