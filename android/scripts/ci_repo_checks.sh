#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Kasaco223 y colaboradores de K-Downloader
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Revisiones del repositorio que no necesitan Gradle ni el SDK. Se corre desde la RAÍZ del repo (CI y local):
#   bash android/scripts/ci_repo_checks.sh
# Cada revisión trabaja solo con archivos que ya existen. Las que lleguen con otros PR (avisos de terceros,
# pins de youtubedl-android, espejo de fuentes, huellas del certificado de release) se agregan como
# secciones nuevas al final, con su propio número.
set -uo pipefail
fail=0
err() {
  echo "::error file=$1::$2"
  fail=1
}

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1 || [ ! -d android ]; then
  echo "Corre este script desde la raíz del repositorio." >&2
  exit 2
fi

# 1) Scripts ejecutables en git y con LF: Windows no guarda el bit +x por sí solo, y un CRLF rompe bash.
while IFS= read -r f; do
  [ -n "$f" ] || continue
  mode=$(git ls-files -s -- "$f" | cut -d' ' -f1)
  [ "$mode" = "100755" ] || err "$f" "No es ejecutable en git (modo ${mode:-?}). Corre: git update-index --chmod=+x $f"
  if grep -q $'\r' "$f"; then err "$f" "Tiene finales de línea CRLF (revisa .gitattributes)"; fi
done < <(git ls-files -- android/gradlew 'android/*.sh')

# 2) Encabezado SPDX en los archivos propios de android/ (GPL-3.0-or-later; GPL-3.0-only si se copió de un
#    proyecto con esa licencia). No llevan encabezado: el texto de la licencia, los binarios y el wrapper
#    de Gradle (archivos de Gradle, Apache-2.0).
while IFS= read -r f; do
  [ -n "$f" ] || continue
  case "$f" in
    android/LICENSE | android/gradlew | android/gradlew.bat | android/gradle/wrapper/*) continue ;;
  esac
  case "$f" in
    *.kt | *.kts | *.java | *.sh | *.py | *.xml | *.properties | *.toml | *.yaml | *.yml | *.pro | *.md | */Dockerfile) ;;
    *) continue ;;
  esac
  if ! head -n 12 "$f" | grep -qE 'SPDX-License-Identifier: GPL-3\.0-(or-later|only)'; then
    err "$f" "Falta el encabezado SPDX-License-Identifier: GPL-3.0-or-later (android/README.md › Licencia)"
  fi
done < <(git ls-files -- android)

# 3) Ninguna llave de firma en git, salvo la de debug (pública a propósito).
while IFS= read -r f; do
  [ -n "$f" ] || continue
  [ "$f" = "android/app/debug.keystore" ] && continue
  err "$f" "Hay una llave de firma en el repositorio: sácala de git y reemplázala por una nueva"
done < <(git ls-files -- '*.jks' '*.p12' '*.pfx' '*.keystore')

# 4) android/LICENSE es el texto de la GPL-3.0 sin cambios (https://www.gnu.org/licenses/gpl-3.0.txt).
gpl_sha=3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986
if [ ! -f android/LICENSE ]; then
  err android/LICENSE "Falta el texto de la GPL-3.0"
elif [ "$(sha256sum android/LICENSE | cut -d' ' -f1)" != "$gpl_sha" ]; then
  err android/LICENSE "No es el texto oficial de la GPL-3.0: restáuralo desde https://www.gnu.org/licenses/gpl-3.0.txt"
fi

# 5) El wrapper de Gradle fija el SHA-256 de su distribución (setup-gradle valida además gradle-wrapper.jar).
props=android/gradle/wrapper/gradle-wrapper.properties
if ! grep -qE '^distributionSha256Sum=[0-9a-f]{64}$' "$props"; then
  err "$props" "Falta distributionSha256Sum (SHA-256 de la distribución de Gradle)"
fi
if ! grep -qE '^distributionUrl=https\\://services\.gradle\.org/distributions/gradle-[0-9.]+-bin\.zip$' "$props"; then
  err "$props" "distributionUrl debe ser una distribución -bin.zip de services.gradle.org"
fi

if [ "$fail" -eq 0 ]; then echo "Revisiones del repositorio: OK"; fi
exit "$fail"
