"""engine.versions: etiquetas de yt-dlp (AAAA.MM.DD[.HHMMSS]) y semver simple."""

from __future__ import annotations

import pytest

from kdownloader.engine import versions


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2026.09.27.232945", (2026, 9, 27, 232945)),  # nightly con HHMMSS
        ("2026.08.19", (2026, 8, 19, 0)),  # estable
        ("2026.8.9", (2026, 8, 9, 0)),
        (" 2026.08.19 \n", (2026, 8, 19, 0)),  # salida de --version con espacios
        ("2026.09.27.000001", (2026, 9, 27, 1)),
    ],
)
def test_parse_ytdlp_valid(text, expected):
    assert versions.parse_ytdlp(text) == expected


@pytest.mark.parametrize(
    "text",
    [None, "", "   ", "abc", "2026", "2026.09", "v2026.09.27", "2026.09.27.", "2026.09.27.23:59",
     "2026-09-27", "2026.09.27.232945.1", "26.09.27", "2026.123.01", "nightly@2026.09.27"],
)
def test_parse_ytdlp_invalid(text):
    assert versions.parse_ytdlp(text) is None


@pytest.mark.parametrize(
    ("version", "minimum", "expected"),
    [
        ("2026.09.27.232945", "2026.09.27.232945", True),  # igual
        ("2026.09.27.232946", "2026.09.27.232945", True),
        ("2026.09.27.232944", "2026.09.27.232945", False),
        ("2026.09.27", "2026.09.27.232945", False),  # estable del mismo día < nightly de ese día
        ("2026.09.27.232945", "2026.09.27", True),
        ("2026.10.01", "2026.09.27.232945", True),
        ("2026.08.19", "2026.08.19", True),
        ("2026.08.18.235959", "2026.08.19", False),
        ("2026.03.03", "2026.08.19", False),  # la versión de pip que daba 403
        ("2027.01.01", "2026.12.31.235959", True),
        ("2026.10.1", "2026.9.30", True),  # sin ceros a la izquierda: compara números, no texto
    ],
)
def test_ytdlp_at_least(version, minimum, expected):
    assert versions.ytdlp_at_least(version, minimum) is expected


def test_ytdlp_at_least_without_minimum_accepts_any_valid_version():
    assert versions.ytdlp_at_least("2020.01.01", None) is True
    assert versions.ytdlp_at_least("2020.01.01", "") is True


@pytest.mark.parametrize("bad", [None, "", "garbage", "1.2.3"])
def test_ytdlp_at_least_rejects_invalid_version(bad):
    assert versions.ytdlp_at_least(bad, "2026.08.19") is False
    assert versions.ytdlp_at_least(bad, None) is False


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2.9.7", (2, 9, 7)),
        ("v2.9.7", (2, 9, 7)),
        ("9.0", (9, 0, 0)),
        ("9", (9, 0, 0)),
        ("9.0.2-essentials_build-www.gyan.dev", (9, 0, 2)),
        ("2.10.0", (2, 10, 0)),
        (" 1.2.3 ", (1, 2, 3)),
    ],
)
def test_parse_semver_valid(text, expected):
    assert versions.parse_semver(text) == expected


@pytest.mark.parametrize("text", [None, "", "n9.0", "deno 2.9.7", "latest", "vx.1"])
def test_parse_semver_invalid(text):
    assert versions.parse_semver(text) is None


@pytest.mark.parametrize(
    ("version", "minimum", "expected"),
    [
        ("9.0.2", "9.0", True),
        ("9.0", "9.0", True),
        ("8.1", "9.0", False),  # la 8.1 se cuelga con --download-sections
        ("10.0", "9.0", True),
        ("2.10.0", "2.9.0", True),  # numérico, no lexicográfico
        ("2.3.0", "2.3.0", True),
        ("2.2.9", "2.3.0", False),
        (None, "2.3.0", False),
        ("basura", "2.3.0", False),
        ("2.3.0", "basura", False),
    ],
)
def test_semver_at_least(version, minimum, expected):
    assert versions.semver_at_least(version, minimum) is expected
