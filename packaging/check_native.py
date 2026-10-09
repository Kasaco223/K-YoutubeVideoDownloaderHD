"""Carga cada .pyd/.dll del runtime con los diálogos de error de Windows suprimidos y falla si alguno
está bloqueado por Smart App Control / App Control (WinError 4551).

En una PC con Smart App Control activo, un módulo nativo sin firma y sin reputación hace que Windows
muestre el diálogo "Bad Image" cada vez que se carga (así se detectó pycryptodomex). Uso:

    runtime\\python.exe packaging\\check_native.py <carpeta del runtime>

Los errores 193 (DLL de otra arquitectura, p. ej. x86/arm64) y 126 (dependencias que solo se resuelven
al importar el paquete) se informan pero no hacen fallar la comprobación.
"""

from __future__ import annotations

import ctypes
import sys
from pathlib import Path

SEM_FAILCRITICALERRORS = 0x0001
SEM_NOGPFAULTERRORBOX = 0x0002
SEM_NOOPENFILEERRORBOX = 0x8000
LOAD_WITH_ALTERED_SEARCH_PATH = 0x8
BLOCKED = 4551  # ERROR_SYSTEM_INTEGRITY_POLICY_VIOLATION


def main(root: Path) -> int:
    if sys.platform != "win32":
        print("check_native: solo aplica en Windows")
        return 0
    ctypes.windll.kernel32.SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX | SEM_NOOPENFILEERRORBOX)
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.LoadLibraryExW.restype = ctypes.c_void_p
    k32.LoadLibraryExW.argtypes = [ctypes.c_wchar_p, ctypes.c_void_p, ctypes.c_uint]
    k32.FreeLibrary.argtypes = [ctypes.c_void_p]
    blocked: list[str] = []
    other: list[str] = []
    ok = 0
    for path in sorted([*root.rglob("*.pyd"), *root.rglob("*.dll")]):
        handle = k32.LoadLibraryExW(str(path), None, LOAD_WITH_ALTERED_SEARCH_PATH)
        if handle:
            ok += 1
            k32.FreeLibrary(handle)
            continue
        err = ctypes.get_last_error()
        rel = str(path.relative_to(root))
        (blocked if err == BLOCKED else other).append(f"WinError {err}: {rel}")
    print(f"check_native: {ok} módulos cargan bien")
    for line in other:
        print("  aviso (no bloquea):", line)
    for line in blocked:
        print("  BLOQUEADO por Windows:", line)
    return 1 if blocked else 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1] if len(sys.argv) > 1 else sys.prefix)))
