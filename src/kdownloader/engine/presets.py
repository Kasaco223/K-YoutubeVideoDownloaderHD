"""Opciones de descarga → argumentos de yt-dlp.

Validado en la Fase 0 contra la escalera real del cliente `visionos` (oct-2026):
- recomendado → 299+140 (H.264 1080p60 + AAC) en MP4, que se reproduce en todo;
- máxima → 315+251 (VP9 4K + Opus) en MKV; con AV1 → 401+251.
`acodec:aac` va antes de `quality`: H.264 HLS + Opus no se puede unir en MP4 (yt-dlp #17326).
Nunca se usa `[height<=N]`: rompe los Shorts verticales (`res` usa la dimensión menor).
"""

from __future__ import annotations

from dataclasses import dataclass

MAIN_PRESETS = ("recommended", "max", "mp3")
ALL_PRESETS = ("recommended", "max", "mp3", "m4a")


@dataclass(frozen=True)
class Choice:
    preset: str  # recommended | max | mp3 | m4a | height
    height: int | None = None

    @property
    def is_audio(self) -> bool:
        return self.preset in ("mp3", "m4a")


def _video_format(is_youtube: bool) -> list[str]:
    # En YouTube, "bv+ba" estricto: visionos no tiene formatos combinados y así nunca se cuela el 360p (formato 18).
    return ["-f", "bv+ba" if is_youtube else "bv*+ba/b"]


def build_args(choice: Choice, *, is_youtube: bool, max_codec: str = "vp9") -> list[str]:
    p = choice.preset
    if p == "recommended":
        return [*_video_format(is_youtube),
                "-S", "lang,vcodec:h264,res:1080,acodec:aac,quality,fps,hdr:12",
                "--merge-output-format", "mp4", "--remux-video", "mp4"]
    if p == "max":
        codec = ",vcodec:vp9" if max_codec == "vp9" else ""
        return [*_video_format(is_youtube),
                "-S", f"lang,res,fps,hdr:sdr{codec},acodec:opus",
                "--merge-output-format", "mkv"]
    if p == "height":
        n = int(choice.height or 1080)
        if n <= 1080:
            return [*_video_format(is_youtube),
                    "-S", f"lang,res:{n},vcodec:h264,acodec:aac,fps,hdr:sdr",
                    "--merge-output-format", "mp4", "--remux-video", "mp4"]
        codec = ",vcodec:vp9" if max_codec == "vp9" else ""
        return [*_video_format(is_youtube),
                "-S", f"lang,res:{n},fps,hdr:sdr{codec},acodec:opus",
                "--merge-output-format", "mkv"]
    if p == "mp3":
        return ["-f", "ba/b", "-x", "--audio-format", "mp3", "--audio-quality", "0"]
    if p == "m4a":
        return ["-f", "ba[ext=m4a]/ba[acodec^=mp4a]/ba/b", "-x", "--audio-format", "m4a"]
    raise ValueError(f"Opción desconocida: {p}")


def fallback_args(choice: Choice) -> list[str]:
    """Para el error 'Requested format is not available': la mejor calidad que haya, avisando al usuario."""
    if choice.is_audio:
        return build_args(choice, is_youtube=False)
    return ["-f", "bv*+ba/b", "--merge-output-format", "mp4/mkv"]


def output_template(style: str, legacy_stamp: str | None = None) -> list[str]:
    """Plantilla de nombre de archivo. Corta a 120 bytes para no superar 260 caracteres en Windows."""
    if style == "legacy_k" and legacy_stamp:
        return ["-o", f"K-{legacy_stamp}.%(ext)s"]
    args = ["-o", "%(title).120B [%(id)s].%(ext)s"]
    if style == "simple":
        args.append("--restrict-filenames")
    return args
