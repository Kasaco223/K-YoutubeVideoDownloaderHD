"""engine.presets: cada opción de descarga → argumentos exactos de yt-dlp."""

from __future__ import annotations

import pytest

from kdownloader.engine import presets
from kdownloader.engine.presets import Choice, build_args, fallback_args, output_template

ALL_CHOICES = [
    Choice("recommended"),
    Choice("max"),
    Choice("mp3"),
    Choice("m4a"),
    Choice("height", 144),
    Choice("height", 360),
    Choice("height", 720),
    Choice("height", 1080),
    Choice("height", 1440),
    Choice("height", 2160),
    Choice("height", 4320),
]


def _id(c: Choice) -> str:
    return f"{c.preset}{c.height or ''}"


def _opt(args: list[str], flag: str) -> str:
    """Valor de la primera aparición de `flag`."""
    return args[args.index(flag) + 1]


def _sort(args: list[str]) -> list[str]:
    return _opt(args, "-S").split(",")


@pytest.mark.parametrize("choice", ALL_CHOICES, ids=_id)
@pytest.mark.parametrize("is_youtube", [True, False])
@pytest.mark.parametrize("max_codec", ["vp9", "av1"])
def test_never_uses_height_filters(choice, is_youtube, max_codec):
    args = build_args(choice, is_youtube=is_youtube, max_codec=max_codec)
    joined = " ".join(args)
    # [height<=N] rompe los Shorts verticales y cae en silencio a 360p (el bug original de la 1.x)
    assert "height<=" not in joined and "height<" not in joined and "[height" not in joined
    assert all(isinstance(a, str) for a in args)
    assert "--" not in args  # la URL siempre la agrega el que llama, después de "--"


@pytest.mark.parametrize("choice", [c for c in ALL_CHOICES if not c.is_audio], ids=_id)
def test_video_selector_strict_on_youtube(choice):
    yt = build_args(choice, is_youtube=True)
    other = build_args(choice, is_youtube=False)
    # YouTube: "bv+ba" sin asterisco ni respaldo: así nunca se cuela el formato 18 (360p combinado)
    assert yt[:2] == ["-f", "bv+ba"]
    assert other[:2] == ["-f", "bv*+ba/b"]
    assert yt[2:] == other[2:]  # el resto (orden y contenedor) no depende del sitio


def test_recommended():
    args = build_args(Choice("recommended"), is_youtube=True)
    assert args == ["-f", "bv+ba", "-S", "lang,vcodec:h264,res:1080,acodec:aac,quality,fps,hdr:12",
                    "--merge-output-format", "mp4", "--remux-video", "mp4"]
    order = _sort(args)
    # AAC antes de `quality`: H.264 + Opus no se puede unir en MP4 (yt-dlp #17326)
    assert order.index("acodec:aac") < order.index("quality")
    assert order.index("vcodec:h264") < order.index("quality")
    assert "res:1080" in order


def test_recommended_ignores_max_codec():
    assert build_args(Choice("recommended"), is_youtube=True, max_codec="av1") == build_args(
        Choice("recommended"), is_youtube=True, max_codec="vp9")


def test_max_vp9():
    args = build_args(Choice("max"), is_youtube=True, max_codec="vp9")
    assert args == ["-f", "bv+ba", "-S", "lang,res,fps,hdr:sdr,vcodec:vp9,acodec:opus", "--merge-output-format", "mkv"]
    assert "--remux-video" not in args


def test_max_av1():
    args = build_args(Choice("max"), is_youtube=True, max_codec="av1")
    order = _sort(args)
    assert order == ["lang", "res", "fps", "hdr:sdr", "acodec:opus"]
    assert not any(o.startswith("vcodec") for o in order)  # sin preferencia: yt-dlp prefiere AV1 (401)
    assert _opt(args, "--merge-output-format") == "mkv"


def test_max_default_codec_is_vp9():
    assert build_args(Choice("max"), is_youtube=False) == build_args(Choice("max"), is_youtube=False, max_codec="vp9")


@pytest.mark.parametrize("height", [144, 360, 480, 720, 1080])
def test_height_up_to_1080_is_mp4_h264(height):
    args = build_args(Choice("height", height), is_youtube=True)
    order = _sort(args)
    assert order[:2] == ["lang", f"res:{height}"]
    assert "vcodec:h264" in order and "acodec:aac" in order
    assert _opt(args, "--merge-output-format") == "mp4"
    assert _opt(args, "--remux-video") == "mp4"


def test_height_720_exact():
    assert build_args(Choice("height", 720), is_youtube=True) == [
        "-f", "bv+ba", "-S", "lang,res:720,vcodec:h264,acodec:aac,fps,hdr:sdr",
        "--merge-output-format", "mp4", "--remux-video", "mp4"]


@pytest.mark.parametrize("max_codec", ["vp9", "av1"])
def test_height_2160_is_mkv(max_codec):
    args = build_args(Choice("height", 2160), is_youtube=True, max_codec=max_codec)
    order = _sort(args)
    assert order[:2] == ["lang", "res:2160"]
    assert "vcodec:h264" not in order
    assert ("vcodec:vp9" in order) is (max_codec == "vp9")
    assert order[-1] == "acodec:opus"
    assert _opt(args, "--merge-output-format") == "mkv"
    assert "--remux-video" not in args


def test_height_without_value_defaults_to_1080():
    assert build_args(Choice("height"), is_youtube=True) == build_args(Choice("height", 1080), is_youtube=True)


def test_mp3():
    args = build_args(Choice("mp3"), is_youtube=True)
    assert args == ["-f", "ba/b", "-x", "--audio-format", "mp3", "--audio-quality", "0"]
    assert build_args(Choice("mp3"), is_youtube=False) == args  # el audio no depende del sitio


def test_m4a():
    args = build_args(Choice("m4a"), is_youtube=True)
    assert args == ["-f", "ba[ext=m4a]/ba[acodec^=mp4a]/ba/b", "-x", "--audio-format", "m4a"]


def test_unknown_preset_raises():
    with pytest.raises(ValueError):
        build_args(Choice("ultra"), is_youtube=True)


def test_choice_is_audio():
    assert Choice("mp3").is_audio and Choice("m4a").is_audio
    assert not Choice("recommended").is_audio and not Choice("max").is_audio and not Choice("height", 720).is_audio


def test_preset_lists():
    assert presets.MAIN_PRESETS == ("recommended", "max", "mp3")
    assert set(presets.MAIN_PRESETS) <= set(presets.ALL_PRESETS)
    assert "m4a" in presets.ALL_PRESETS
    for p in presets.ALL_PRESETS:
        build_args(Choice(p), is_youtube=True)  # todas las opciones nombradas funcionan


@pytest.mark.parametrize("choice", [Choice("recommended"), Choice("max"), Choice("height", 720),
                                    Choice("height", 2160)], ids=_id)
def test_fallback_video_is_best_anything(choice):
    assert fallback_args(choice) == ["-f", "bv*+ba/b", "--merge-output-format", "mp4/mkv"]


@pytest.mark.parametrize("preset", ["mp3", "m4a"])
def test_fallback_audio_keeps_format(preset):
    assert fallback_args(Choice(preset)) == build_args(Choice(preset), is_youtube=False)


def test_output_template_title_id():
    assert output_template("title_id") == ["-o", "%(title).120B [%(id)s].%(ext)s"]
    assert "--restrict-filenames" not in output_template("title_id")


def test_output_template_simple_restricts_filenames():
    args = output_template("simple")
    assert args[:2] == ["-o", "%(title).120B [%(id)s].%(ext)s"]
    assert "--restrict-filenames" in args


def test_output_template_legacy_k():
    assert output_template("legacy_k", "20261009_153000") == ["-o", "K-20261009_153000.%(ext)s"]


def test_output_template_legacy_without_stamp_falls_back():
    assert output_template("legacy_k") == output_template("title_id")
    assert output_template("legacy_k", "") == output_template("title_id")


def test_output_template_unknown_style_is_title_id():
    assert output_template("whatever") == output_template("title_id")


def test_title_is_cut_to_120_bytes():
    # Presupuesto de rutas de Windows (260): el título se recorta en bytes, no en caracteres.
    assert ".120B" in output_template("title_id")[1]
