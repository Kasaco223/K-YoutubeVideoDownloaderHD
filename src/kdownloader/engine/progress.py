"""Lectura del protocolo `KDL|…` que imprime yt-dlp gracias a --progress-template y --print.

Formatos (todo el JSON lo genera yt-dlp con el conversor `j`, siempre ASCII):
  KDL|dl|<progreso>|<info>      progreso de descarga de un formato
  KDL|pp|<posproceso>           inicio/fin de un posprocesador (Merger, ExtractAudio, …)
  KDL|file|"<ruta final>"       archivo terminado (after_move)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

_decoder = json.JSONDecoder()

PROGRESS_TEMPLATE_DL = (
    "download:KDL|dl|%(progress.{status,downloaded_bytes,total_bytes,total_bytes_estimate,speed,eta,elapsed,"
    "fragment_index,fragment_count})j|%(info.{format_id,vcodec,acodec,height,ext})j"
)
PROGRESS_TEMPLATE_PP = "postprocess:KDL|pp|%(progress.{status,postprocessor})j"
PRINT_FILE = "after_move:KDL|file|%(filepath)j"


@dataclass
class KdlEvent:
    kind: str  # "dl" | "pp" | "file"
    data: dict[str, Any] = field(default_factory=dict)
    info: dict[str, Any] = field(default_factory=dict)
    path: str | None = None


def _decode(text: str) -> tuple[Any, str]:
    value, end = _decoder.raw_decode(text)
    return value, text[end:]


def parse_line(line: str) -> KdlEvent | None:
    """Devuelve el evento de una línea, o None si la línea no es del protocolo o está dañada.

    Solo se acepta `KDL|` al inicio de la línea (tras el último `\\r` de las barras de progreso):
    yt-dlp repite la URL del usuario en su salida, y una URL con "KDL|file|…" no debe inyectar eventos.
    """
    line = line.rstrip("\r\n").rsplit("\r", 1)[-1].lstrip()
    if not line.startswith("KDL|"):
        return None
    rest = line[4:]
    kind, sep, payload = rest.partition("|")
    if not sep:
        return None
    try:
        if kind == "dl":
            data, tail = _decode(payload)
            info: dict[str, Any] = {}
            if tail.startswith("|"):
                info, _ = _decode(tail[1:])
            if isinstance(data, dict):
                return KdlEvent("dl", data, info if isinstance(info, dict) else {})
        elif kind == "pp":
            data, _ = _decode(payload)
            if isinstance(data, dict):
                return KdlEvent("pp", data)
        elif kind == "file":
            path, _ = _decode(payload)
            if isinstance(path, str) and path:
                return KdlEvent("file", path=path)
    except ValueError:
        return None
    return None


def stream_kind(info: dict[str, Any]) -> str:
    """'video', 'audio' o 'av' según los códecs del formato que se está bajando."""
    vcodec = str(info.get("vcodec") or "none")
    acodec = str(info.get("acodec") or "none")
    if vcodec != "none" and acodec != "none":
        return "av"
    if vcodec != "none":
        return "video"
    return "audio"
