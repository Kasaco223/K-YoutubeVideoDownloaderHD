"""Comprueba que el site-packages del runtime tenga todas las dependencias que declaran sus paquetes.

Uso (con el Python del build, no con el runtime):  python packaging/check_deps.py <site-packages>

build.ps1 instala con --no-deps (para exigir los hashes de requirements-runtime.txt), así que este
chequeo detecta si a la lista le falta alguna dependencia transitiva. Evalúa los marcadores como en
el runtime: CPython 3.13, Windows x64. Necesita el paquete "packaging"; si no está, avisa y sale con 0.
"""

from __future__ import annotations

import sys
from importlib import metadata
from pathlib import Path

TARGET_ENV = {
    "implementation_name": "cpython",
    "implementation_version": "3.13.16",
    "os_name": "nt",
    "platform_machine": "AMD64",
    "platform_python_implementation": "CPython",
    "platform_release": "10",
    "platform_system": "Windows",
    "platform_version": "10.0.26100",
    "python_full_version": "3.13.16",
    "python_version": "3.13",
    "sys_platform": "win32",
}


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    try:
        from packaging.requirements import Requirement
        from packaging.utils import canonicalize_name
    except ImportError:
        print("check_deps: falta el paquete 'packaging'; se omite el chequeo de dependencias.")
        return 0

    site = Path(argv[0])
    installed = {}
    for dist in metadata.distributions(path=[str(site)]):
        installed[canonicalize_name(dist.metadata["Name"])] = dist
    problems = []
    for name, dist in sorted(installed.items()):
        for raw in dist.requires or []:
            req = Requirement(raw)
            if req.marker is not None and not req.marker.evaluate({**TARGET_ENV, "extra": ""}):
                continue
            dep = installed.get(canonicalize_name(req.name))
            if dep is None:
                problems.append(f"{name} necesita {req} (no está instalado)")
            elif req.specifier and not req.specifier.contains(dep.version, prereleases=True):
                problems.append(f"{name} necesita {req} (hay {dep.version})")
    for line in problems:
        print("check_deps:", line)
    print(f"check_deps: {len(installed)} paquetes, {len(problems)} problema(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
