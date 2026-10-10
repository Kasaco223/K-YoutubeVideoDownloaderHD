"""engine.ytdlp: argumentos comunes, resumen de la info, detección de probe degradado y ejecuciones (con un
yt-dlp falso que imprime el protocolo KDL)."""

from __future__ import annotations

import json
import shutil
import threading
import time
from pathlib import Path

import pytest

from kdownloader.engine import ytdlp
from kdownloader.engine.presets import Choice, build_args, output_template
from kdownloader.engine.progress import PRINT_FILE, PROGRESS_TEMPLATE_DL, PROGRESS_TEMPLATE_PP, KdlEvent
from kdownloader.engine.ytdlp import (
    DownloadRun,
    EngineConfig,
    EngineFailure,
    base_args,
    is_degraded,
    is_youtube,
    summarize,
)

FAKE_SOURCE = Path(__file__).parent / "fixtures" / "fake_ytdlp.py"
YT = "https://www.youtube.com/watch?v=aqz-KE-bpKQ"
VIMEO = "https://vimeo.com/76979871"


@pytest.fixture
def cfg(tmp_path: Path, python_exe: Path) -> EngineConfig:
    return EngineConfig(
        python=python_exe,
        ytdlp=tmp_path / "engine" / "ytdlp" / "2026.09.27.232945" / "yt-dlp.pyz",
        ffmpeg_dir=tmp_path / "engine" / "ffmpeg" / "gyan-9.0.2",
        deno=tmp_path / "engine" / "deno" / "v2.9.7" / "deno.exe",
        cache_dir=tmp_path / "cache",
    )


@pytest.fixture
def fake_cfg(tmp_path: Path, python_exe: Path) -> EngineConfig:
    """Config cuyo "yt-dlp" es el script falso, copiado a una carpeta con espacios y ñ."""
    folder = tmp_path / "motor ñ"
    folder.mkdir()
    script = folder / "fake_ytdlp.py"
    shutil.copyfile(FAKE_SOURCE, script)
    return EngineConfig(python=python_exe, ytdlp=script, ffmpeg_dir=None, deno=None, cache_dir=tmp_path / "cache")


def recorded_runs(cfg: EngineConfig) -> list[list[str]]:
    """Argumentos de cada ejecución del yt-dlp falso, de la más vieja a la más nueva."""
    files = sorted(cfg.ytdlp.parent.glob(cfg.ytdlp.name + ".args.*.json"), key=lambda p: p.stat().st_mtime_ns)
    return [json.loads(p.read_text(encoding="utf-8")) for p in files]


def recorded_args(cfg: EngineConfig) -> list[str]:
    runs = recorded_runs(cfg)
    assert runs, "el yt-dlp falso no se ejecutó"
    return runs[-1]


# ----------------------------------------------------------------------------- is_youtube


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=aqz-KE-bpKQ",
        "https://youtube.com/shorts/abc",
        "https://m.youtube.com/watch?v=x",
        "https://music.youtube.com/watch?v=x",
        "https://youtu.be/aqz-KE-bpKQ?t=10",
        "https://www.youtube-nocookie.com/embed/x",
        "https://WWW.YOUTUBE.COM/watch?v=x",
        "http://www.youtube.com:443/watch?v=x",
    ],
)
def test_is_youtube_true(url):
    assert is_youtube(url)


@pytest.mark.parametrize(
    "url",
    [
        "",
        "not a url",
        "https://vimeo.com/123",
        "https://notyoutube.com/watch?v=x",
        "https://youtube.com.evil.example/watch?v=x",
        "https://evil.example/?u=https://youtube.com",
        "https://evil.example/youtube.com",
        "https://fakeyoutu.be/x",
        "youtube.com/watch?v=x",  # sin esquema no hay host
    ],
)
def test_is_youtube_false(url):
    assert not is_youtube(url)


# ----------------------------------------------------------------------------- base_args


def test_base_args_prefix(cfg: EngineConfig):
    args = base_args(cfg, YT)
    assert args[:5] == [str(cfg.python), "-I", "-X", "utf8", str(cfg.ytdlp)]
    for flag in ("--ignore-config", "--no-update", "--no-plugin-dirs"):
        assert flag in args
    assert args[args.index("--color") + 1] == "never"
    assert args[args.index("--cache-dir") + 1] == str(cfg.cache_dir)
    assert "--" not in args and YT not in args  # la URL la agrega el que llama, después de "--"


def test_base_args_deno_and_ffmpeg(cfg: EngineConfig):
    args = base_args(cfg, YT)
    assert args[args.index("--js-runtimes") + 1] == f"deno:{cfg.deno}"
    assert args[args.index("--ffmpeg-location") + 1] == str(cfg.ffmpeg_dir)
    cfg.deno = None
    cfg.ffmpeg_dir = None
    args = base_args(cfg, YT)
    assert "--js-runtimes" not in args and "--ffmpeg-location" not in args


@pytest.mark.parametrize(
    ("url", "use_cookies", "expected"),
    [
        (YT, None, False),  # YouTube: nunca por defecto (desactivan el cliente visionos)
        (YT, True, True),  # salvo que el usuario lo pida (flujo guiado de un error)
        (YT, False, False),
        ("https://youtu.be/x", None, False),
        (VIMEO, None, True),  # otros sitios: sí por defecto
        (VIMEO, False, False),
        (VIMEO, True, True),
    ],
)
def test_base_args_cookies(cfg: EngineConfig, url, use_cookies, expected):
    cfg.cookies_file = "C:\\Users\\Ana\\cookies ñ.txt"
    args = base_args(cfg, url, use_cookies)
    assert ("--cookies" in args) is expected
    if expected:
        assert args[args.index("--cookies") + 1] == cfg.cookies_file
    assert "--cookies-from-browser" not in args


def test_base_args_without_cookies_file(cfg: EngineConfig):
    cfg.cookies_file = None
    assert "--cookies" not in base_args(cfg, VIMEO, True)
    cfg.cookies_file = ""
    assert "--cookies" not in base_args(cfg, YT, True)


def test_base_args_player_client_only_for_youtube(cfg: EngineConfig):
    cfg.youtube_player_client = "default,-web"
    args = base_args(cfg, YT)
    i = args.index("--extractor-args")
    assert args[i + 1] == "youtube:player_client=default,-web"
    assert "--extractor-args" not in base_args(cfg, VIMEO)
    cfg.youtube_player_client = None
    assert "--extractor-args" not in base_args(cfg, YT)


# ----------------------------------------------------------------------------- summarize


def test_summarize_bbb_fixture(bbb_info):
    s = summarize(bbb_info)
    assert s["id"] == "aqz-KE-bpKQ"
    assert s["title"] == "Big Buck Bunny 60fps 4K - Official Blender Foundation Short Film"
    assert s["uploader"] == "Blender"
    assert s["duration"] == 634
    assert s["thumbnail"] == "https://i.ytimg.com/vi_webp/aqz-KE-bpKQ/maxresdefault.webp"
    assert s["url"] == YT
    assert s["extractor"] == "Youtube"
    assert (s["is_live"], s["age_limit"], s["is_playlist"]) == (False, 0, False)
    assert s["max_height"] == 2160 and s["has_video"] is True
    assert [h["height"] for h in s["heights"]] == [2160, 1440, 1080, 720, 360]
    by_h = {h["height"]: h for h in s["heights"]}
    assert by_h[2160]["fps"] == 60 and by_h[720]["fps"] == 60 and by_h[360]["fps"] == 30
    assert not any(h["hdr"] for h in s["heights"])
    # El vertical 1080x1920 cuenta como 1080 (como `res` de yt-dlp), no como 1920.
    assert 1920 not in by_h
    assert "formats" not in s and "url" not in json.dumps(s["heights"])  # sin URLs de medios
    json.dumps(s)  # serializable para el puente


def test_summarize_vertical_short(make_info, make_format):
    info = make_info([
        make_format("140", acodec="mp4a.40.2", ext="m4a"),
        make_format("137v", height=1920, width=1080, vcodec="avc1.640028", fps=30),
        make_format("136v", height=1280, width=720, vcodec="avc1.4d401f", fps=30),
    ], url="https://www.youtube.com/shorts/abcdefghijk")
    s = summarize(info)
    assert [h["height"] for h in s["heights"]] == [1080, 720]
    assert s["max_height"] == 1080


def test_summarize_hdr_and_missing_fields(make_info, make_format):
    info = make_info([
        make_format("701", height=2160, vcodec="av01.0.13M.10", fps=60, dynamic_range="HDR10"),
        make_format("315", height=2160, vcodec="vp9", fps=60),
        make_format("x", height=480, vcodec="avc1", fps=None),
        make_format("noh", vcodec="avc1"),  # sin altura: se ignora
    ])
    info.pop("channel")
    s = summarize(info)
    assert s["uploader"] == "Uploader de prueba"  # sin canal → uploader
    assert s["heights"][0] == {"height": 2160, "fps": 60, "hdr": True}
    assert {"height": 480, "fps": 0, "hdr": False} in s["heights"]


def test_summarize_audio_only_and_title_fallback(make_info, make_format):
    info = make_info([make_format("251", acodec="opus", ext="webm")], url=VIMEO, title="")
    s = summarize(info)
    assert s["title"] == info["id"]
    assert s["has_video"] is False and s["max_height"] == 0 and s["heights"] == []


def test_summarize_thumbnail_only_https(make_info):
    info = make_info(thumbnail="http://insecure.example/t.jpg", thumbnails=[
        {"url": "http://i.ytimg.com/a.jpg", "preference": 100, "width": 4000},
        {"url": "https://i.ytimg.com/b.jpg", "preference": -5, "width": 1280},
        {"url": "https://i.ytimg.com/c.jpg", "preference": -5, "width": 1920},
        {"url": "https://i.ytimg.com/d.jpg", "preference": -10, "width": 9999},
        {"url": "data:image/png;base64,xxxx", "preference": 50},
    ])
    assert summarize(info)["thumbnail"] == "https://i.ytimg.com/c.jpg"
    info = make_info(thumbnail=None, thumbnails=[{"url": "javascript:alert(1)"}])
    assert summarize(info)["thumbnail"] is None


def test_summarize_playlist(make_playlist):
    info = make_playlist([
        {"id": "a1", "title": "Uno", "url": "https://www.youtube.com/watch?v=a1", "duration": 60},
        None,  # yt-dlp deja None para entradas no disponibles
        {"id": "b2", "title": None, "url": "https://www.youtube.com/watch?v=b2", "duration": None},
        {"id": "c3", "title": "Tres ñ", "webpage_url": "https://www.youtube.com/watch?v=c3", "duration": 30.5},
        "basura",
    ])
    s = summarize(info)
    assert s["is_playlist"] is True
    assert s["count"] == 3
    assert s["total_duration"] == 90.5
    assert s["title"] == "Lista de prueba" and s["uploader"] == "Canal de la lista"
    assert s["entries"] == [
        {"id": "a1", "title": "Uno", "url": "https://www.youtube.com/watch?v=a1", "duration": 60},
        {"id": "b2", "title": "b2", "url": "https://www.youtube.com/watch?v=b2", "duration": None},
        {"id": "c3", "title": "Tres ñ", "url": "https://www.youtube.com/watch?v=c3", "duration": 30.5},
    ]
    assert "heights" not in s


def test_summarize_empty_playlist(make_playlist):
    s = summarize(make_playlist(None))
    assert s["count"] == 0 and s["entries"] == [] and s["total_duration"] == 0


# ----------------------------------------------------------------------------- is_degraded


def test_bbb_visionos_ladder_is_not_degraded(bbb_info):
    assert is_degraded(bbb_info) is False


def test_only_format_18_is_degraded(make_info, make_format):
    info = make_info([
        make_format("18", height=360, vcodec="avc1.42001E", acodec="mp4a.40.2", fps=30),
        make_format("140", acodec="mp4a.40.2", ext="m4a"),
        {"format_id": "sb0", "vcodec": "none", "acodec": "none", "ext": "mhtml"},
    ])
    assert is_degraded(info) is True


def test_low_ladder_with_18_is_degraded(make_info, make_format):
    info = make_info([
        make_format("18", height=360, vcodec="avc1.42001E", acodec="mp4a.40.2"),
        make_format("134", height=360, vcodec="avc1.4D401E"),
        make_format("160", height=144, vcodec="avc1.4d400c"),
    ])
    assert is_degraded(info) is True


def test_low_quality_original_is_not_degraded(make_info, make_format):
    # Un video subido en 360p sin el formato 18 es simplemente así: no es un bloqueo.
    info = make_info([make_format("134", height=360, vcodec="avc1.4D401E"),
                      make_format("140", acodec="mp4a.40.2", ext="m4a")])
    assert is_degraded(info) is False


def test_vertical_short_with_high_res_is_not_degraded(make_info, make_format):
    info = make_info([make_format("18", height=640, width=360, vcodec="avc1", acodec="mp4a"),
                      make_format("137", height=1920, width=1080, vcodec="avc1")],
                     url="https://www.youtube.com/shorts/abcdefghijk")
    assert is_degraded(info) is False


def test_degraded_only_applies_to_youtube_vod(make_info, make_format):
    only18 = [make_format("18", height=360, vcodec="avc1", acodec="mp4a")]
    assert is_degraded(make_info(only18, url=VIMEO)) is False
    assert is_degraded(make_info(only18, is_live=True)) is False
    assert is_degraded(make_info([make_format("140", acodec="mp4a", ext="m4a")])) is False
    assert is_degraded(make_info([])) is False


# ----------------------------------------------------------------------------- DownloadRun


def _run(cfg: EngineConfig, url: str, home: Path, temp: Path, **kwargs) -> tuple[DownloadRun, list[KdlEvent]]:
    events: list[KdlEvent] = []
    lock = threading.Lock()

    def on_event(ev: KdlEvent) -> None:
        with lock:
            events.append(ev)

    run = DownloadRun(cfg, url, build_args(Choice("recommended"), is_youtube=is_youtube(url)),
                      output_template("title_id"), home, temp, on_event, **kwargs)
    return run, events


def test_download_run_args(cfg: EngineConfig, tmp_path: Path):
    home, temp = tmp_path / "Descargas ñ", tmp_path / "t" / "abcd1234"
    run, _ = _run(cfg, YT, home, temp, extra=["--download-sections", "*10-14"])
    a = run.args
    assert a[-2:] == ["--", YT]  # la URL siempre al final, después de "--"
    assert a[:5] == [str(cfg.python), "-I", "-X", "utf8", str(cfg.ytdlp)]
    for flag in ("--no-quiet", "--newline", "--progress", "--embed-metadata", "--embed-thumbnail",
                 "--embed-chapters", "--no-playlist"):
        assert flag in a
    templates = [a[i + 1] for i, x in enumerate(a) if x == "--progress-template"]
    assert templates == [PROGRESS_TEMPLATE_DL, PROGRESS_TEMPLATE_PP]
    assert a[a.index("--print") + 1] == PRINT_FILE
    paths_ = [a[i + 1] for i, x in enumerate(a) if x == "-P"]
    assert paths_ == [f"home:{home}", f"temp:{temp}"]
    assert a[a.index("-o") + 1] == "%(title).120B [%(id)s].%(ext)s"
    assert a[a.index("-f") + 1] == "bv+ba"
    assert a.index("--download-sections") > a.index("-S")  # los extras van al final, antes de la URL
    assert a.index("-f") < a.index("--")


def test_download_run_cookies_flag(cfg: EngineConfig, tmp_path: Path):
    cfg.cookies_file = "C:\\c.txt"
    run, _ = _run(cfg, YT, tmp_path, tmp_path)
    assert "--cookies" not in run.args
    run, _ = _run(cfg, YT, tmp_path, tmp_path, use_cookies=True)
    assert "--cookies" in run.args
    assert run.args.index("--cookies") < run.args.index("--")


def test_download_run_success(fake_cfg: EngineConfig, tmp_path: Path):
    home, temp = tmp_path / "Descargas ñ", tmp_path / "t" / "abcd1234"
    run, events = _run(fake_cfg, YT, home, temp)
    run.start()
    result = run.wait()
    assert result.returncode == 0 and result.canceled is False
    expected = str(home / "Soy el Ñandú ｜ La Granja de Zenón 6 [IKLKB49EqS8].mp4")
    assert result.files == [expected]
    assert Path(expected).read_bytes() == b"fake"
    assert result.already_downloaded is False
    kinds = [e.kind for e in events]
    assert kinds.count("dl") == 4 and kinds.count("pp") == 2 and kinds.count("file") == 1
    dl = [e for e in events if e.kind == "dl"]
    assert [e.info["format_id"] for e in dl] == ["134", "134", "140", "140"]  # stdout conserva el orden
    pp = [e.data["postprocessor"] for e in events if e.kind == "pp"]
    assert pp == ["Merger", "Merger"]  # las líneas KDL de stderr también cuentan
    # Las líneas que no son KDL quedan en la cola (para clasificar errores y "Ver detalles").
    assert any(ln.startswith("[youtube] Extracting URL") for ln in result.lines)
    assert any(ln.startswith("WARNING: algo") for ln in result.lines)
    assert not any("KDL|" in ln for ln in result.lines)
    assert recorded_args(fake_cfg)[-2:] == ["--", YT]


def test_download_run_failure(fake_cfg: EngineConfig, tmp_path: Path):
    url = "https://www.youtube.com/watch?v=fail0000000"
    run, events = _run(fake_cfg, url, tmp_path / "home", tmp_path / "t")
    run.start()
    result = run.wait()
    assert result.returncode == 1 and not result.canceled
    assert result.files == []
    assert [e.kind for e in events] == ["dl"] * 4
    assert "ERROR: unable to download video data: HTTP Error 403: Forbidden" in result.lines
    from kdownloader.engine import errors

    assert errors.classify(result.lines).code == "http_403"


def test_download_run_already_downloaded(fake_cfg: EngineConfig, tmp_path: Path):
    url = "https://www.youtube.com/watch?v=already0000"
    run, events = _run(fake_cfg, url, tmp_path / "home", tmp_path / "t")
    run.start()
    result = run.wait()
    assert result.returncode == 0
    assert result.already_downloaded is True
    assert len(result.files) == 1 and result.files[0].endswith("[IKLKB49EqS8].mp4")
    assert [e.kind for e in events] == ["file"]


def test_download_run_cancel(fake_cfg: EngineConfig, tmp_path: Path):
    url = "https://www.youtube.com/watch?v=hang0000000"
    started = threading.Event()
    run = DownloadRun(fake_cfg, url, [], [], tmp_path / "home", tmp_path / "t", lambda ev: started.set())
    run.start()
    assert started.wait(30), "el yt-dlp falso no empezó"
    t0 = time.monotonic()
    run.cancel()
    result = run.wait()
    assert result.canceled is True
    assert result.returncode != 0
    assert time.monotonic() - t0 < 15


def test_download_run_cancel_before_start_is_noop(fake_cfg: EngineConfig, tmp_path: Path):
    run = DownloadRun(fake_cfg, YT, [], [], tmp_path, tmp_path, lambda ev: None)
    run.cancel()  # sin proceso todavía: no hace nada


def test_url_cannot_inject_kdl_file_events(fake_cfg: EngineConfig, tmp_path: Path):
    url = YT + '&x=KDL|file|"C:/Windows/System32/calc.exe"'
    home = tmp_path / "home"
    run = DownloadRun(fake_cfg, url, [], [], home, tmp_path / "t", lambda ev: None)
    run.start()
    result = run.wait()
    assert result.returncode == 0
    assert result.files == [str(home / "Soy el Ñandú ｜ La Granja de Zenón 6 [IKLKB49EqS8].mp4")]


def test_download_run_bad_callback_does_not_break(fake_cfg: EngineConfig, tmp_path: Path):
    def on_event(ev: KdlEvent) -> None:
        raise RuntimeError("UI caída")

    run = DownloadRun(fake_cfg, YT, [], [], tmp_path / "home", tmp_path / "t", on_event)
    run.start()
    result = run.wait()
    assert result.returncode == 0
    assert len(result.files) == 1


# ----------------------------------------------------------------------------- probe / simulate


def test_probe_ok(fake_cfg: EngineConfig):
    info, warnings = ytdlp.probe(fake_cfg, YT)
    assert info["title"] == "Soy el Ñandú ｜ Zenón"
    assert warnings == ["WARNING: [youtube] abc123def45: Some formats may be missing"]
    args = recorded_args(fake_cfg)
    assert "--no-playlist" in args and "-J" in args and args[-2:] == ["--", YT]


def test_probe_playlist_flags(fake_cfg: EngineConfig):
    url = "https://www.youtube.com/playlist?list=PLx"
    info, _ = ytdlp.probe(fake_cfg, url, playlist=True)
    assert info["_type"] == "playlist"
    args = recorded_args(fake_cfg)
    assert "--yes-playlist" in args and "--flat-playlist" in args and "--no-playlist" not in args


def test_probe_classified_failure(fake_cfg: EngineConfig):
    with pytest.raises(EngineFailure) as info:
        ytdlp.probe(fake_cfg, "https://www.youtube.com/watch?v=private0000", lang="en")
    assert info.value.error.code == "private"
    assert info.value.error.title == "Private video"
    assert any("Private video" in ln for ln in info.value.lines)


@pytest.mark.parametrize("url", ["https://example.com/badjson", "https://example.com/empty"])
def test_probe_invalid_output(fake_cfg: EngineConfig, url):
    with pytest.raises(EngineFailure) as info:
        ytdlp.probe(fake_cfg, url)
    assert info.value.error.code == "unknown"


def test_probe_timeout(fake_cfg: EngineConfig):
    t0 = time.monotonic()
    with pytest.raises(TimeoutError):
        ytdlp.probe(fake_cfg, "https://example.com/slow", timeout=1)
    assert time.monotonic() - t0 < 20


def test_probe_cancel(fake_cfg: EngineConfig):
    cancel = threading.Event()
    threading.Timer(0.5, cancel.set).start()
    t0 = time.monotonic()
    with pytest.raises(InterruptedError):
        ytdlp.probe(fake_cfg, "https://example.com/slow", cancel=cancel, timeout=60)
    assert time.monotonic() - t0 < 20


def test_simulate_choices(fake_cfg: EngineConfig, bbb_info):
    choices = {
        "recommended": build_args(Choice("recommended"), is_youtube=True),
        "max": build_args(Choice("max"), is_youtube=True),
        "mp3": build_args(Choice("mp3"), is_youtube=True),
        "h720": build_args(Choice("height", 720), is_youtube=True),
    }
    res = ytdlp.simulate(fake_cfg, bbb_info, choices)
    assert set(res) == set(choices)
    assert res["recommended"]["format_id"] == "299+140"
    assert res["max"]["format_id"] == "315+251"
    assert res["mp3"]["format_id"] == "251"
    assert res["h720"]["format_id"] == "299+140"  # el falso solo mira el contenedor
    assert all(r["info_id"] == "aqz-KE-bpKQ" for r in res.values())  # leyó el info.json temporal
    runs = recorded_runs(fake_cfg)
    assert len(runs) == 4
    for args in runs:
        assert "--simulate" in args and "--load-info-json" in args and "--no-warnings" in args
        assert args[args.index("--print") + 1] == ytdlp.SIM_PRINT
        assert "--" not in args  # simula sobre el JSON local: sin URL ni red
        assert not Path(args[args.index("--load-info-json") + 1]).exists()  # el temporal se borró


def test_simulate_failure_gives_none(fake_cfg: EngineConfig, make_info):
    info = make_info(url="https://www.youtube.com/watch?v=sim-fail000")
    res = ytdlp.simulate(fake_cfg, info, {"recommended": ["-f", "bv+ba"]})
    assert res == {"recommended": None}


def test_simulate_without_choices(fake_cfg: EngineConfig, bbb_info):
    assert ytdlp.simulate(fake_cfg, bbb_info, {}) == {}
