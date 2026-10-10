"""yt-dlp falso para las pruebas de engine.ytdlp (solo biblioteca estándar).

Se ejecuta igual que el real: `python -I -X utf8 fake_ytdlp.py <args…> -- <url>`. Su comportamiento depende
de la URL (último argumento) y de las opciones. Guarda los argumentos recibidos en `<script>.args.<pid>.json`
(un archivo por proceso: la simulación lanza varios en paralelo).
"""

import json
import os
import sys
import time

ARGS = sys.argv[1:]
URL = ARGS[-1] if ARGS else ""
HERE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(HERE, f"{os.path.basename(__file__)}.args.{os.getpid()}.json"), "w", encoding="utf-8") as f:
    json.dump(ARGS, f)


def opt(name, default=None):
    """Valor de la última aparición de `name`."""
    value = default
    for i, a in enumerate(ARGS[:-1]):
        if a == name:
            value = ARGS[i + 1]
    return value


def out(line):
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def err(line):
    sys.stderr.write(line + "\n")
    sys.stderr.flush()


def kdl_dl(status, done, total, fmt, vcodec, acodec, height=None):
    prog = {"status": status, "downloaded_bytes": done, "total_bytes": total, "speed": 1000.0, "eta": 1,
            "elapsed": 0.1}
    info = {"format_id": fmt, "vcodec": vcodec, "acodec": acodec}
    if height:
        info["height"] = height
    return "KDL|dl|" + json.dumps(prog) + "|" + json.dumps(info)


def kdl_pp(status, name):
    return "KDL|pp|" + json.dumps({"status": status, "postprocessor": name})


def simulate():
    path = opt("--load-info-json")
    try:
        with open(path, encoding="utf-8") as f:
            info = json.load(f)
        assert info.get("id")
    except Exception as exc:
        err(f"ERROR: bad --load-info-json: {exc!r}")
        sys.exit(2)
    if "sim-fail" in str(info.get("webpage_url")):
        err("ERROR: [youtube] abc123def45: Requested format is not available")
        sys.exit(1)
    out("[info] simulando")
    if "-x" in ARGS:
        res = {"format_id": "251", "height": None, "vcodec": "none", "acodec": "opus", "ext": "webm",
               "filesize": 10202210}
    elif opt("--merge-output-format") == "mp4":
        res = {"format_id": "299+140", "height": 1080, "vcodec": "avc1.64002A", "acodec": "mp4a.40.2", "ext": "mp4",
               "filesize": 267891149}
    else:
        res = {"format_id": "315+251", "height": 2160, "vcodec": "vp9", "acodec": "opus", "ext": "mkv",
               "filesize": 1372471691}
    res["info_id"] = info["id"]
    out(json.dumps(res))
    sys.exit(0)


def probe():
    if "private" in URL:
        err("WARNING: [youtube] abc123def45: algo raro")
        err("ERROR: [youtube] abc123def45: Private video. Sign in if you've been granted access to this video")
        sys.exit(1)
    if "badjson" in URL:
        out("esto no es JSON")
        sys.exit(0)
    if "empty" in URL:
        sys.exit(0)
    if "slow" in URL:
        time.sleep(60)
    err("WARNING: [youtube] abc123def45: Some formats may be missing")
    err("[youtube] abc123def45: Downloading webpage")
    if "--flat-playlist" in ARGS:
        info = {"_type": "playlist", "id": "PLx", "title": "Lista ñ", "entries": [
            {"id": "a", "title": "Uno", "url": "https://www.youtube.com/watch?v=a", "duration": 10}]}
    else:
        info = {"id": "abc123def45", "title": "Soy el Ñandú ｜ Zenón", "webpage_url": URL, "formats": []}
    out(json.dumps(info, ensure_ascii=False))
    sys.exit(0)


def download():
    home = "."
    for i, a in enumerate(ARGS[:-1]):
        if a == "-P" and ARGS[i + 1].startswith("home:"):
            home = ARGS[i + 1][len("home:"):]
    final = os.path.join(home, "Soy el Ñandú ｜ La Granja de Zenón 6 [IKLKB49EqS8].mp4")
    out(f"[youtube] Extracting URL: {URL}")
    if "already" in URL:
        out(f"[download] {final} has already been downloaded")
        out("KDL|file|" + json.dumps(final))
        sys.exit(0)
    out(kdl_dl("downloading", 1024, 4096, "134", "avc1.4D401E", "none", 360))
    if "hang" in URL:
        time.sleep(60)
    out(kdl_dl("finished", 4096, 4096, "134", "avc1.4D401E", "none", 360))
    out(kdl_dl("downloading", 512, 2048, "140", "none", "mp4a.40.2"))
    out(kdl_dl("finished", 2048, 2048, "140", "none", "mp4a.40.2"))
    if "fail" in URL:
        err("ERROR: unable to download video data: HTTP Error 403: Forbidden")
        sys.exit(1)
    err(kdl_pp("started", "Merger"))  # con --print, el posproceso puede llegar por stderr
    err("WARNING: algo sin importancia")
    out(f'[Merger] Merging formats into "{final}"')
    err(kdl_pp("finished", "Merger"))
    os.makedirs(home, exist_ok=True)
    with open(final, "wb") as f:
        f.write(b"fake")
    out("KDL|file|" + json.dumps(final))
    sys.exit(0)


if "--version" in ARGS:
    out("2026.09.27.232945")
elif "--simulate" in ARGS:
    simulate()
elif "-J" in ARGS:
    probe()
else:
    download()
