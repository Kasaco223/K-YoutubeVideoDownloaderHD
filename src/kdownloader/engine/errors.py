"""Traduce la salida de yt-dlp a errores comprensibles (es/en) con una acción sugerida."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..util import strip_ansi

CATALOG_PATH = Path(__file__).with_name("errors_catalog.json")
_PREFIX_RE = re.compile(r"^(ERROR|WARNING):\s*(\[[^\]]+\]\s*)?([A-Za-z0-9_-]{6,}:\s*)?", re.IGNORECASE)
_URL_RE = re.compile(r"\s*(See|Visit)?\s*https?://\S+", re.IGNORECASE)


@dataclass
class EngineError:
    code: str
    action: str
    auto: str | None
    title: str
    message: str
    details: str = ""
    texts: dict[str, dict[str, str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@lru_cache(maxsize=1)
def catalog() -> dict[str, Any]:
    with open(CATALOG_PATH, encoding="utf-8") as f:
        return json.load(f)


def _normalize(text: str) -> str:
    return strip_ansi(text).replace("’", "'").replace("‘", "'")


def relevant_lines(lines: list[str]) -> list[str]:
    """Las líneas ERROR: si existen; si no, la cola de la salida."""
    clean = [_normalize(ln).strip() for ln in lines if ln and ln.strip()]
    errors = [ln for ln in clean if ln.upper().startswith("ERROR")]
    return errors or clean[-30:]


def clean_message(line: str) -> str:
    """Quita el prefijo `ERROR: [youtube] id:` y las URLs de la FAQ para mostrarlo al usuario."""
    text = _PREFIX_RE.sub("", _normalize(line)).strip()
    return _URL_RE.sub("", text).strip(" .;")


def classify(lines: list[str], lang: str = "es") -> EngineError:
    rel = relevant_lines(lines)
    haystack = "\n".join(rel).lower()
    data = catalog()
    lang = lang if lang in ("es", "en") else "es"
    details = "\n".join(rel)[-4000:]
    for rule in data["rules"]:
        if any(token in haystack for token in rule["match"]):
            return EngineError(
                code=rule["code"], action=rule["action"], auto=rule.get("auto"),
                title=rule[lang]["title"], message=rule[lang]["message"], details=details,
                texts={"es": rule["es"], "en": rule["en"]},
            )
    fb = data["fallback"]
    last = clean_message(rel[-1]) if rel else ""
    message = fb[lang]["message"] + (f" ({last[:200]})" if last else "")
    return EngineError(code=fb["code"], action=fb["action"], auto=None, title=fb[lang]["title"],
                       message=message, details=details, texts={"es": fb["es"], "en": fb["en"]})


def is_already_downloaded(lines: list[str]) -> bool:
    tokens = catalog()["already_downloaded"]["match"]
    return any(t in _normalize(ln).lower() for ln in lines for t in tokens)


def export_for_web() -> list[dict[str, Any]]:
    """Datos para la página /ayuda de la web (mismo catálogo que usa la app)."""
    data = catalog()
    items = [{"code": r["code"], "es": r["es"], "en": r["en"]} for r in data["rules"]]
    items.append({"code": data["fallback"]["code"], "es": data["fallback"]["es"], "en": data["fallback"]["en"]})
    return items
