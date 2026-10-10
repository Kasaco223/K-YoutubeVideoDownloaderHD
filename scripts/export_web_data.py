"""Genera web/data/errors.json a partir del catálogo de errores de la app.

La app y la web comparten una sola fuente (src/kdownloader/engine/errors_catalog.json):
la página /ayuda muestra exactamente los mismos códigos y textos que ve el usuario en la app.

Uso:
    python scripts/export_web_data.py            # escribe web/data/errors.json
    python scripts/export_web_data.py --check    # falla (código 1) si el archivo está desactualizado
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = ROOT / "web" / "data" / "errors.json"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from kdownloader.engine.errors import export_for_web  # noqa: E402

REQUIRED_LANGS = ("es", "en")


def build() -> list[dict]:
    items = export_for_web()
    codes: set[str] = set()
    for item in items:
        code = item.get("code")
        if not code or not isinstance(code, str):
            raise ValueError(f"Entrada sin código: {item!r}")
        if code in codes:
            raise ValueError(f"Código repetido en el catálogo: {code}")
        codes.add(code)
        for lang in REQUIRED_LANGS:
            texts = item.get(lang) or {}
            if not texts.get("title") or not texts.get("message"):
                raise ValueError(f"Faltan textos '{lang}' para el código {code}")
    return items


def render(data: list[dict]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="solo comprueba que el archivo esté al día")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")

    items = build()
    text = render(items)
    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != text:
            print(f"{OUT.relative_to(ROOT)} está desactualizado; ejecuta scripts/export_web_data.py", file=sys.stderr)
            return 1
        print(f"{OUT.relative_to(ROOT)} está al día")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"Escrito {OUT.relative_to(ROOT)} ({len(items)} códigos)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
