"""engine.errors: clasificación de la salida real de yt-dlp en errores comprensibles (es/en)."""

from __future__ import annotations

import pytest

from kdownloader.engine import errors
from kdownloader.engine.errors import catalog, classify, clean_message, export_for_web, is_already_downloaded

FAQ = "See  https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp  for how to manually pass cookies"

# (código esperado, salida de yt-dlp). Textos con la forma real de yt-dlp / Python / FFmpeg.
SAMPLES: list[tuple[str, list[str]]] = [
    ("drm", ["ERROR: [generic] film: This video is DRM protected"]),
    ("drm", ["ERROR: [youtube] abc123def45: This video is drm protected and only images are available for download. "
             "use --list-formats to see them"]),
    ("members_only", ["ERROR: [youtube] abc123def45: Join this channel to get access to members-only content like "
                      "this video, and other exclusive perks."]),
    ("members_only", ["ERROR: [youtube] abc123def45: This video is available to this channel's members on level: "
                      "Fan (or any higher level). Join this channel to get access to members-only content and other "
                      "exclusive perks."]),
    ("payment", ["ERROR: [youtube] abc123def45: This video requires payment to watch."]),
    ("payment", ["ERROR: [youtube] abc123def45: This video is only available to Music Premium members"]),
    ("age_restricted", [f"ERROR: [youtube] abc123def45: Sign in to confirm your age. This video may be inappropriate "
                        f"for some users. Use --cookies-from-browser or --cookies for the authentication. {FAQ}"]),
    ("private", [f"ERROR: [youtube] abc123def45: Private video. Sign in if you've been granted access to this "
                 f"video. Use --cookies-from-browser or --cookies for the authentication. {FAQ}"]),
    ("private", ["ERROR: [vimeo] 12345678: This video is private"]),
    ("bot_check", [f"ERROR: [youtube] abc123def45: Sign in to confirm you’re not a bot. Use --cookies-from-browser "
                   f"or --cookies for the authentication. {FAQ}"]),  # apóstrofo tipográfico, como lo manda YouTube
    ("bot_check", ["ERROR: [youtube] abc123def45: Sign in to confirm you're not a bot. This helps protect our "
                   "community. Learn more"]),
    ("rate_limited", ["ERROR: [youtube] abc123def45: Video unavailable. This content isn’t available, try again "
                      "later."]),
    ("rate_limited", ["ERROR: [youtube] abc123def45: Video unavailable. This content isn't available, try again "
                      "later."]),
    ("rate_limited", ["ERROR: unable to download video data: HTTP Error 429: Too Many Requests"]),
    ("rate_limited", ["ERROR: [tiktok] 7300000000000000000: You are being rate-limited, try again later"]),
    ("login_required", ["ERROR: [instagram] C0abcdefgh: Requested content is not available, rate-limit reached or "
                        "login required. Use --cookies, --cookies-from-browser, --username and --password, "
                        "--netrc-cmd, or --netrc (instagram) to provide account credentials"]),
    ("login_required", ["ERROR: [twitter] 1700000000000000000: NSFW tweet requires authentication. Use --cookies, "
                        "--cookies-from-browser, --username and --password, --netrc-cmd, or --netrc (twitter) to "
                        "provide account credentials"]),
    ("login_required", ["ERROR: [facebook] 123456789: Login details are needed to download this content"]),
    ("geo_blocked", ["ERROR: [youtube] abc123def45: Video unavailable. The uploader has not made this video "
                     "available in your country"]),
    ("geo_blocked", ["ERROR: [BBCiPlayer] p0abcdef: This video is not available from your location due to geo "
                     "restriction. You might want to use a VPN or a proxy server (with --proxy) to workaround."]),
    ("upcoming", ["ERROR: [youtube] abc123def45: Premieres in 2 hours"]),
    ("upcoming", ["ERROR: [youtube] abc123def45: This live event will begin in a few moments."]),
    ("not_live", ["ERROR: [youtube:tab] @SomeChannel: The channel is not currently live"]),
    ("removed", ["ERROR: [youtube] abc123def45: Video unavailable. This video has been removed by the uploader"]),
    ("removed", ["ERROR: [youtube] abc123def45: Video unavailable. This video is no longer available because the "
                 "YouTube account associated with this video has been terminated."]),
    ("copyright", ["ERROR: [youtube] abc123def45: Video unavailable. This video is no longer available due to a "
                   "copyright claim by Some Label"]),
    ("copyright", ["ERROR: [youtube] abc123def45: Video unavailable. This video contains content from Some Label, "
                   "who has blocked it on copyright grounds"]),
    ("format_unavailable", ["ERROR: [youtube] abc123def45: Requested format is not available. Use --list-formats "
                            "for a list of available formats"]),
    ("http_403", ["ERROR: unable to download video data: HTTP Error 403: Forbidden"]),
    ("http_403", ["[download] Got error: HTTP Error 403: Forbidden. Retrying fragment 1 (1/10)...",
                  "ERROR: fragment 1 not found, unable to continue; HTTP Error 403: Forbidden"]),
    ("engine_outdated", ["ERROR: [youtube] abc123def45: Unable to extract initial player response; please report "
                         "this issue on  https://github.com/yt-dlp/yt-dlp/issues?q= , filling out the appropriate "
                         "issue template. Confirm you are on the latest version using  yt-dlp -U"]),
    ("engine_outdated", ["ERROR: [youtube] abc123def45: n challenge solving failed: Some formats may be missing. "
                         "Ensure you have a supported JavaScript runtime and challenge solver script distribution "
                         "installed."]),
    ("unavailable", ["ERROR: [youtube] BaW_jenozKc: This video is unavailable"]),
    ("unavailable", ["ERROR: [youtube] abc123def45: Video unavailable"]),
    ("ffmpeg_missing", ["ERROR: Postprocessing: ffprobe and ffmpeg not found. Please install or provide the path "
                        "using --ffmpeg-location"]),
    ("ffmpeg_missing", ["ERROR: You have requested merging of multiple formats but ffmpeg is not installed. "
                        "Aborting due to --abort-on-error"]),
    ("blocked_by_windows", ["Traceback (most recent call last):",
                            "OSError: [WinError 4551] An Application Control policy has blocked this file: "
                            "'C:\\Users\\Ana\\AppData\\Local\\K-Downloader\\engine\\deno\\v2.9.7\\deno.exe'"]),
    ("blocked_by_windows", ["[WinError 4551] An Application Control policy has blocked this file"]),
    ("antivirus", ["OSError: [WinError 225] Operation did not complete successfully because the file contains a "
                   "virus or potentially unwanted software"]),
    ("merge_failed", ["ERROR: Postprocessing: Conversion failed!"]),
    ("merge_failed", ["ERROR: Unable to merge formats: Error merging streams"]),
    ("disk_full", ["ERROR: unable to write data: [Errno 28] No space left on device"]),
    ("disk_full", ["ERROR: unable to write data: [WinError 112] There is not enough space on the disk"]),
    ("permission", ["ERROR: unable to open for writing: [Errno 13] Permission denied: "
                    "'C:\\Users\\Ana\\Videos\\a.mp4.part'"]),
    ("permission", ["ERROR: Unable to rename file: [WinError 32] The process cannot access the file because it is "
                    "being used by another process: 'a.temp.mp4' -> 'a.mp4'"]),
    ("permission", ["ERROR: unable to create directory [WinError 5] Access is denied: 'C:\\Program Files\\x'"]),
    ("ssl", ["ERROR: [youtube] abc123def45: Unable to download API page: [SSL: CERTIFICATE_VERIFY_FAILED] "
             "certificate verify failed: unable to get local issuer certificate (_ssl.c:1006) (caused by "
             "CertificateVerifyFailed(\"[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed\"))"]),
    ("ssl", ["ERROR: [youtube] abc123def45: Unable to download webpage: <urlopen error [SSL: "
             "CERTIFICATE_VERIFY_FAILED] certificate verify failed (_ssl.c:1006)>"]),
    ("network", ["ERROR: [youtube] abc123def45: Unable to download webpage: <urlopen error [Errno 11001] "
                 "getaddrinfo failed> (caused by TransportError('<urlopen error [Errno 11001] getaddrinfo "
                 "failed>'))"]),
    ("network", ["ERROR: [download] Got error: The read operation timed out"]),
    ("network", ["ERROR: unable to download video data: [WinError 10054] An existing connection was forcibly closed "
                 "by the remote host (Connection reset)"]),
    ("unsupported_url", ["ERROR: Unsupported URL: https://example.com/some/page"]),
    ("unsupported_url", ["ERROR: 'notaurl' is not a valid URL. Set --default-search \"ytsearch\" (or run  yt-dlp "
                         "\"ytsearch:notaurl\" ) to search YouTube"]),
]


@pytest.mark.parametrize(("code", "lines"), SAMPLES, ids=[f"{c}-{i}" for i, (c, _) in enumerate(SAMPLES)])
def test_classify_realistic_lines(code, lines):
    err = classify(lines)
    assert err.code == code, (err.code, lines)
    rule = next(r for r in catalog()["rules"] if r["code"] == code)
    assert err.action == rule["action"]
    assert err.auto == rule.get("auto")


def test_every_rule_has_a_realistic_sample():
    covered = {code for code, _ in SAMPLES}
    rules = {r["code"] for r in catalog()["rules"]}
    assert rules - covered == set(), "agrega un ejemplo real para cada regla nueva del catálogo"


def test_private_is_not_login_required():
    err = classify([f"ERROR: [youtube] x1y2z3a4b5c: Private video. Sign in if you've been granted access to this "
                    f"video. Use --cookies-from-browser or --cookies for the authentication. {FAQ}"])
    assert err.code == "private"


def test_age_is_not_bot_check_nor_login():
    assert classify(["ERROR: [youtube] x1y2z3a4b5c: Sign in to confirm your age"]).code == "age_restricted"


def test_try_again_later_is_rate_limited_not_unavailable():
    err = classify(["ERROR: [youtube] x1y2z3a4b5c: Video unavailable. This content isn't available, try again later."])
    assert err.code == "rate_limited"
    assert err.action == "retry_later" and err.auto == "quiet_mode"


def test_bot_check_with_curly_apostrophe():
    err = classify(["ERROR: [youtube] abc: Sign in to confirm you’re not a bot. Use --cookies-from-browser…"])
    assert err.code == "bot_check"
    assert "’" not in err.details  # el detalle queda normalizado


def test_http_403_triggers_update_retry():
    err = classify(["ERROR: unable to download video data: HTTP Error 403: Forbidden"])
    assert (err.code, err.action, err.auto) == ("http_403", "update_retry", "update_retry")


def test_blocked_by_windows_without_error_prefix():
    err = classify(["[WinError 4551] An Application Control policy has blocked this file"])
    assert err.code == "blocked_by_windows" and err.action == "repair_engine"


def test_fixture_unavailable(fixture_lines):
    lines = fixture_lines("rec_full_unicode.stderr.txt") + fixture_lines("rec_full_unicode.stdout.txt")
    err = classify(lines)
    assert err.code == "unavailable" and err.action == "open_browser"
    assert err.details == "ERROR: [youtube] BaW_jenozKc: This video is unavailable"


def test_error_lines_win_over_warnings_and_noise():
    lines = [
        "[youtube] abc123def45: Downloading webpage",
        "WARNING: [youtube] abc123def45: n challenge solving failed: Some formats may be missing.",
        "ERROR: [youtube] abc123def45: Requested format is not available. Use --list-formats for a list of "
        "available formats",
    ]
    err = classify(lines)
    assert err.code == "format_unavailable"  # solo cuentan las líneas ERROR
    assert err.details == lines[-1]


def test_without_error_lines_uses_tail():
    lines = [f"[download] línea {i}" for i in range(100)] + ["Conversion failed!"]
    err = classify(lines)
    assert err.code == "merge_failed"
    assert err.details.splitlines()[0] == "[download] línea 71"  # últimas 30 líneas
    assert len(err.details.splitlines()) == 30


def test_ansi_is_stripped():
    err = classify(["\x1b[0;31mERROR:\x1b[0m [youtube] abc123def45: \x1b[1mPrivate video\x1b[0m. Sign in if you've "
                    "been granted access to this video"])
    assert err.code == "private"
    assert "\x1b" not in err.details
    assert err.details.startswith("ERROR: [youtube] abc123def45: Private video.")


def test_fallback_unknown_includes_cleaned_last_line():
    err = classify(["ERROR: [generic] abc123def45: Something completely new happened. See https://example.com/x"])
    assert err.code == "unknown" and err.action == "retry" and err.auto is None
    fb = catalog()["fallback"]
    assert err.title == fb["es"]["title"]
    assert err.message.startswith(fb["es"]["message"])
    assert "(Something completely new happened)" in err.message
    assert "https://" not in err.message and "ERROR" not in err.message
    assert err.texts == {"es": fb["es"], "en": fb["en"]}


def test_fallback_with_no_output():
    err = classify([])
    assert err.code == "unknown"
    assert err.message == catalog()["fallback"]["es"]["message"]
    assert err.details == ""
    assert classify(["", "   "]).code == "unknown"


def test_fallback_message_is_capped():
    err = classify(["ERROR: " + "x" * 1000])
    assert len(err.message) < len(catalog()["fallback"]["es"]["message"]) + 210


def test_details_are_capped():
    lines = ["ERROR: " + "y" * 300 + f" {i}" for i in range(50)]
    assert len(classify(lines).details) <= 4000


def test_language_selection():
    line = ["ERROR: [youtube] abc123def45: Private video. Sign in if you've been granted access to this video"]
    rule = next(r for r in catalog()["rules"] if r["code"] == "private")
    es, en = classify(line, "es"), classify(line, "en")
    assert (es.title, es.message) == (rule["es"]["title"], rule["es"]["message"])
    assert (en.title, en.message) == (rule["en"]["title"], rule["en"]["message"])
    assert classify(line, "fr").title == rule["es"]["title"]  # idioma desconocido → español
    assert es.texts == {"es": rule["es"], "en": rule["en"]}


def test_to_dict_has_errorview_shape():
    d = classify(["ERROR: unable to download video data: HTTP Error 403: Forbidden"], "en").to_dict()
    assert set(d) == {"code", "action", "auto", "title", "message", "details", "texts"}
    assert set(d["texts"]) == {"es", "en"}
    assert set(d["texts"]["en"]) >= {"title", "message"}


@pytest.mark.parametrize(
    ("line", "clean"),
    [
        ("ERROR: [youtube] dQw4w9WgXcQ: Video unavailable", "Video unavailable"),
        ("ERROR: [youtube] dQw4w9WgXcQ: Sign in to confirm your age. See https://x.y/faq",
         "Sign in to confirm your age"),
        ("ERROR: [youtube:tab] UCSMOQeBJ2RAnuFungnQOxLg: The channel is not currently live",
         "The channel is not currently live"),
        ("WARNING: [youtube] dQw4w9WgXcQ: Some formats may be missing.", "Some formats may be missing"),
        ("ERROR: Postprocessing: Conversion failed!", "Conversion failed!"),
        ("ERROR: unable to download video data: HTTP Error 403: Forbidden",
         "unable to download video data: HTTP Error 403: Forbidden"),
        ("\x1b[0;31mERROR:\x1b[0m [generic] abcdefgh: Visit https://example.com/help for details",
         "for details"),
        ("Sign in to confirm you’re not a bot", "Sign in to confirm you're not a bot"),
        ("error: [vimeo] 12345678: Private", "Private"),
    ],
)
def test_clean_message(line, clean):
    assert clean_message(line) == clean


def test_is_already_downloaded():
    assert is_already_downloaded(["[download] C:\\KD\\out\\Big Buck Bunny [aqz-KE-bpKQ].mp4 has already been "
                                  "downloaded"])
    assert is_already_downloaded(["\x1b[0;32m[download]\x1b[0m a.mp3 has already been downloaded"])
    assert not is_already_downloaded(["[download] 100% of 10.00MiB", "KDL|file|\"a.mp4\""])
    assert not is_already_downloaded([])


def test_export_for_web_shape():
    items = export_for_web()
    rules = catalog()["rules"]
    assert len(items) == len(rules) + 1
    assert items[-1]["code"] == "unknown"
    codes = [i["code"] for i in items]
    assert len(codes) == len(set(codes))
    for item in items:
        assert set(item) == {"code", "es", "en"}
        for lang in ("es", "en"):
            assert item[lang]["title"] and item[lang]["message"] and item[lang]["help"]


VALID_ACTIONS = {"update_retry", "retry", "retry_later", "choose_quality", "cookies", "choose_folder",
                 "repair_engine", "open_browser", "none"}


def test_catalog_rules_are_complete():
    data = catalog()
    assert data["version"] == 1
    codes = [r["code"] for r in data["rules"]]
    assert len(codes) == len(set(codes))
    for rule in [*data["rules"], data["fallback"]]:
        assert rule["action"] in VALID_ACTIONS, rule["code"]
        for lang in ("es", "en"):
            texts = rule[lang]
            for key in ("title", "message", "help"):
                assert isinstance(texts.get(key), str) and texts[key].strip(), (rule["code"], lang, key)
            assert len(texts["title"]) <= 80 and len(texts["message"]) <= 200
        assert rule.get("auto") is None or isinstance(rule["auto"], str)
    ad = data["already_downloaded"]
    for lang in ("es", "en"):
        assert ad[lang]["title"] and ad[lang]["message"]


def test_catalog_match_tokens_are_normalized():
    """El texto se compara en minúsculas y con ’ → ': un token con mayúsculas o comillas curvas nunca coincidiría."""
    data = catalog()
    for rule in [*data["rules"], data["already_downloaded"]]:
        assert rule["match"], rule["code"]
        for token in rule["match"]:
            assert token == token.lower(), (rule["code"], token)
            assert "’" not in token and "‘" not in token, (rule["code"], token)
            assert token.strip(), rule["code"]


def test_spanish_copy_uses_tu_and_video():
    """Español neutro con tú: nada de "vídeo" (con tilde de España) ni "usted"/"vosotros"."""
    data = catalog()
    for rule in [*data["rules"], data["fallback"], data["already_downloaded"]]:
        text = " ".join(rule["es"].values()).lower()
        assert "vídeo" not in text and "usted" not in text and "vosotros" not in text, rule["code"]


def test_relevant_lines_normalizes():
    assert errors.relevant_lines(["  \x1b[31mERROR:\x1b[0m algo’s mal  ", "", "otra"]) == ["ERROR: algo's mal"]
    assert errors.relevant_lines(["a", " ", "b"]) == ["a", "b"]
