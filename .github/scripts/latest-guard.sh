#!/usr/bin/env bash
# Mantiene "Latest" en la versión estable más alta de la app de Windows (vX.Y.Z).
# Lo corre .github/workflows/release-latest.yml (siempre la copia de master) y lo prueban
# .github/scripts/test-latest-guard.sh con un gh simulado.
#
# Orden (importa): 1) todo Release android-* publicado como normal pasa a pre-release; una pre-release
# nunca puede ser Latest, así que desde ese momento Latest ya es un Release de Windows. 2) Se marca la vX.Y.Z
# más alta. 3) Se comprueba. Cada llamada a gh se reintenta (5, 15 y 45 s) y un fallo no corta el resto de
# los arreglos: al final sale con 1 si algo no se pudo hacer, para que el run quede en rojo.
# Variables: GH_REPO (obligatoria), KD_SLEEP_SCALE (0 en las pruebas), GITHUB_STEP_SUMMARY (opcional).
set -uo pipefail

desktop_re='^v[0-9]+\.[0-9]+\.[0-9]+$'
failures=0

pause() { sleep "$(( $1 * ${KD_SLEEP_SCALE:-1} ))"; }

# retry_out <comando...>: hasta 4 intentos; imprime la salida del intento que funcionó.
retry_out() {
  local i out
  for i in 1 2 3 4; do
    if out=$("$@"); then
      [ -n "$out" ] && printf '%s\n' "$out"
      return 0
    fi
    [ "$i" -eq 4 ] && break
    echo "::warning::Falló «$*» (intento $i de 4); se reintenta." >&2
    pause $(( 5 * 3 ** (i - 1) ))
  done
  return 1
}

fail() { echo "::error::$1"; failures=$((failures + 1)); }

latest_tag() { gh api "repos/${GH_REPO}/releases/latest" --jq .tag_name 2>/dev/null || true; }

# 1) Android nunca es Latest: todo android-* publicado como versión normal vuelve a pre-release. PRIMERO.
if android_normal=$(retry_out gh release list --exclude-drafts --limit 1000 --json tagName,isPrerelease \
    --jq '.[] | select((.tagName | startswith("android-")) and (.isPrerelease | not)) | .tagName'); then
  for t in $android_normal; do
    echo "::warning::${t} estaba publicado como versión normal; se marca como pre-release para que nunca sea Latest."
    retry_out gh release edit "$t" --prerelease --latest=false > /dev/null \
      || fail "No se pudo marcar ${t} como pre-release. Hazlo a mano: gh release edit ${t} --prerelease --latest=false"
  done
else
  fail "No se pudo leer la lista de Releases (paso 1)."
fi

# 2) Latest = la vX.Y.Z publicada más alta. sort -V ordena versiones (2.10.0 > 2.9.0); el filtro deja fuera
#    android-* (sort -V los pondría después de cualquier número) y las -rc de Windows.
tag=""
if tags=$(retry_out gh release list --exclude-drafts --exclude-pre-releases --limit 1000 --json tagName --jq '.[].tagName'); then
  highest=$(printf '%s\n' "$tags" | { grep -E "$desktop_re" || true; } | sed 's/^v//' | sort -V | tail -n 1)
  if [ -z "$highest" ]; then
    echo "::notice::Todavía no hay un Release publicado de la app de Windows (vX.Y.Z): no se cambia Latest."
  else
    tag="v${highest}"
    current=$(latest_tag)
    if [ "$current" != "$tag" ]; then
      echo "::warning::Latest era «${current:-ninguno}»; se marca ${tag}, la versión de Windows más alta."
      retry_out gh release edit "$tag" --latest > /dev/null || fail "No se pudo marcar ${tag} como Latest."
    fi
  fi
else
  fail "No se pudo leer la lista de Releases publicados (paso 2)."
fi

# 3) Comprobar la API y la misma URL que usan /descargar y la autoactualización de Windows.
if [ -n "$tag" ]; then
  current=""
  for _ in 1 2 3 4 5 6; do
    current=$(latest_tag)
    [ "$current" = "$tag" ] && break
    pause 5
  done
  if [ "$current" != "$tag" ]; then
    fail "GitHub sigue marcando «${current:-ninguno}» como Latest en vez de ${tag}."
  elif ! curl -fsSL --retry 5 --retry-all-errors --retry-delay 5 -o /dev/null \
      "https://github.com/${GH_REPO}/releases/latest/download/latest.json"; then
    fail "releases/latest/download/latest.json no responde: revisa los archivos de ${tag}."
  elif [ -n "${GITHUB_STEP_SUMMARY:-}" ]; then
    echo "Latest: **${tag}** (app de Windows)." >> "$GITHUB_STEP_SUMMARY"
  fi
fi

[ "$failures" -eq 0 ] || { echo "::error::${failures} problema(s); el próximo run (cada hora) lo vuelve a intentar."; exit 1; }
