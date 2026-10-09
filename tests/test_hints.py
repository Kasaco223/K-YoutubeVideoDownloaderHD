"""engine.hints: engine.json es entrada hostil; solo pasan los campos de la lista blanca."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from kdownloader.engine import hints
from kdownloader.engine.hints import Hints, HintsStore, validate

GOOD = {
    "schema": 1,
    "min_ytdlp": {"nightly": "2026.09.27.232945", "stable": "2026.08.19"},
    "youtube_player_client": "default,-web",
    "notice": {"es": "Hay un problema con YouTube; ya lo estamos arreglando.", "en": "YouTube issue; fix coming."},
}


def test_validate_good_document():
    h = validate(GOOD)
    assert h.min_ytdlp == {"nightly": "2026.09.27.232945", "stable": "2026.08.19"}
    assert h.youtube_player_client == "default,-web"
    assert h.notice == GOOD["notice"]
    assert h.to_dict() == {"min_ytdlp": h.min_ytdlp, "youtube_player_client": "default,-web", "notice": h.notice}


def test_repo_engine_json_shape_from_architecture_is_valid():
    doc = {"schema": 1, "min_ytdlp": {"nightly": "2026.09.27.232945", "stable": "2026.08.19"},
           "youtube_player_client": None, "notice": {"es": None, "en": None}}
    h = validate(doc)
    assert h.youtube_player_client is None and h.notice == {}
    assert h.min_ytdlp["nightly"] == "2026.09.27.232945"


@pytest.mark.parametrize("raw", [None, [], "texto", 1, {}, {**GOOD, "schema": 2}, {**GOOD, "schema": "1"},
                                 {**GOOD, "schema": 1.5}, {**GOOD, "schema": None},
                                 {k: v for k, v in GOOD.items() if k != "schema"}])
def test_wrong_schema_or_type_gives_empty_hints(raw):
    h = validate(raw)
    assert h == Hints()
    assert h.to_dict() == {"min_ytdlp": {}, "youtube_player_client": None, "notice": {}}


@pytest.mark.parametrize(
    "client",
    ["visionos", "default,-web", "web_safari,tv", "-android_vr", "mweb,-ios,tv_simply"],
)
def test_player_client_accepted(client):
    assert validate({"schema": 1, "youtube_player_client": client}).youtube_player_client == client


@pytest.mark.parametrize(
    "client",
    [
        "",
        "WEB",  # mayúsculas
        "web,",  # coma colgante
        ",web",
        "web,,tv",
        "web tv",
        "web;rm -rf",
        "web --exec calc",
        "default,-web --cookies-from-browser chrome",
        "web\ntv",
        "web&tv",
        "--",
        "web2",  # dígitos: fuera de la lista blanca
        "a" * 121,  # demasiado largo
        123,
        ["web"],
        {"client": "web"},
        True,
    ],
)
def test_player_client_rejected(client):
    assert validate({"schema": 1, "youtube_player_client": client}).youtube_player_client is None


def test_player_client_max_length_boundary():
    ok = ",".join(["web"] * 30)  # 119 caracteres
    assert len(ok) <= 120
    assert validate({"schema": 1, "youtube_player_client": ok}).youtube_player_client == ok


def test_min_ytdlp_filters_bad_values_and_channels():
    h = validate({"schema": 1, "min_ytdlp": {"nightly": "latest", "stable": 20260819, "master": "2026.09.01",
                                             "extra": "2026.09.01"}})
    assert h.min_ytdlp == {}
    h = validate({"schema": 1, "min_ytdlp": {"nightly": "2026.10.01.000000", "stable": "v2026.08.19"}})
    assert h.min_ytdlp == {"nightly": "2026.10.01.000000"}
    assert validate({"schema": 1, "min_ytdlp": ["2026.09.27"]}).min_ytdlp == {}


def test_notice_truncated_and_trimmed():
    long = "á" * 500
    h = validate({"schema": 1, "notice": {"es": f"  {long}  ", "en": "  hello  "}})
    assert h.notice["es"] == "á" * 280
    assert h.notice["en"] == "hello"


@pytest.mark.parametrize("notice", [{"es": 5, "en": None}, {"es": "   ", "en": ["x"]}, "aviso", ["es"], None,
                                    {"fr": "bonjour"}])
def test_notice_non_strings_ignored(notice):
    assert validate({"schema": 1, "notice": notice}).notice == {}


def test_notice_is_kept_as_plain_text():
    # El HTML no se interpreta aquí: la UI lo pinta con textContent. Solo se valida tipo y largo.
    h = validate({"schema": 1, "notice": {"es": "<img src=x onerror=alert(1)>"}})
    assert h.notice == {"es": "<img src=x onerror=alert(1)>"}


def test_unknown_fields_are_dropped():
    raw = {**GOOD, "url": "https://evil.example/yt-dlp.exe", "args": ["--exec", "calc"], "ytdlp_repo": "evil/evil"}
    h = validate(raw)
    assert set(h.to_dict()) == {"min_ytdlp", "youtube_player_client", "notice"}
    assert "evil" not in json.dumps(h.to_dict())


# ----------------------------------------------------------------------------- HintsStore


class FakeGetText:
    def __init__(self, payload: object = GOOD, exc: BaseException | None = None):
        self.payload = payload
        self.exc = exc
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, url: str, **kwargs):
        self.calls.append((url, kwargs))
        if self.exc is not None:
            raise self.exc
        return self.payload if isinstance(self.payload, str) else json.dumps(self.payload)


@pytest.fixture
def cache(tmp_path: Path) -> Path:
    return tmp_path / "hints.json"


URL = "https://raw.githubusercontent.invalid/engine.json"


def test_store_fetches_once_then_uses_cache(cache: Path, monkeypatch: pytest.MonkeyPatch):
    fake = FakeGetText()
    monkeypatch.setattr(hints, "get_text", fake)
    store = HintsStore(cache, URL)
    assert store.hints == Hints() and store.fetched_at == 0
    h = store.refresh()
    assert h.youtube_player_client == "default,-web"
    assert len(fake.calls) == 1
    url, kwargs = fake.calls[0]
    assert url == URL and kwargs.get("limit", 0) <= 64_000  # el documento remoto está acotado
    assert store.refresh() is h  # dentro de las 24 h no se vuelve a pedir
    assert len(fake.calls) == 1
    store.refresh(force=True)
    assert len(fake.calls) == 2


def test_store_persists_cache_and_reloads(cache: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(hints, "get_text", FakeGetText())
    store = HintsStore(cache, URL)
    store.refresh()
    saved = json.loads(cache.read_text(encoding="utf-8"))
    assert saved["fetched_at"] == pytest.approx(time.time(), abs=60)
    assert saved["data"]["schema"] == 1
    fake = FakeGetText(exc=AssertionError("no debería pedir de nuevo"))
    monkeypatch.setattr(hints, "get_text", fake)
    again = HintsStore(cache, URL)
    assert again.hints == store.hints
    assert again.refresh() == store.hints
    assert fake.calls == []


def test_cache_is_revalidated_on_load(cache: Path):
    cache.write_text(json.dumps({"fetched_at": time.time(), "data": {
        "schema": 1, "youtube_player_client": "web --exec calc", "notice": {"es": "x" * 999}}}), encoding="utf-8")
    store = HintsStore(cache, URL)
    assert store.hints.youtube_player_client is None
    assert len(store.hints.notice["es"]) == 280


def test_stale_cache_triggers_refresh(cache: Path, monkeypatch: pytest.MonkeyPatch):
    cache.write_text(json.dumps({"fetched_at": time.time() - hints.CHECK_EVERY - 10, "data": GOOD}), encoding="utf-8")
    fake = FakeGetText({**GOOD, "youtube_player_client": "tv"})
    monkeypatch.setattr(hints, "get_text", fake)
    store = HintsStore(cache, URL)
    assert store.hints.youtube_player_client == "default,-web"
    assert store.refresh().youtube_player_client == "tv"
    assert len(fake.calls) == 1


@pytest.mark.parametrize("exc", [OSError("sin red"), TimeoutError("lento"), ValueError("raro")])
def test_network_errors_keep_previous_hints(cache: Path, monkeypatch: pytest.MonkeyPatch, exc):
    monkeypatch.setattr(hints, "get_text", FakeGetText())
    store = HintsStore(cache, URL)
    good = store.refresh()
    stamp = store.fetched_at
    monkeypatch.setattr(hints, "get_text", FakeGetText(exc=exc))
    assert store.refresh(force=True) == good
    assert store.fetched_at == stamp  # no cuenta como revisado: se reintenta luego


def test_invalid_json_keeps_previous_hints(cache: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(hints, "get_text", FakeGetText("<html>rate limited</html>"))
    store = HintsStore(cache, URL)
    assert store.refresh() == Hints()
    assert store.fetched_at == 0
    assert not cache.exists()


def test_hostile_remote_document_yields_empty_hints(cache: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(hints, "get_text", FakeGetText({"schema": 1, "youtube_player_client": "web; calc"}))
    store = HintsStore(cache, URL)
    assert store.refresh().youtube_player_client is None


def test_corrupt_cache_file_is_ignored(cache: Path):
    cache.write_text("{corrupt", encoding="utf-8")
    store = HintsStore(cache, URL)
    assert store.hints == Hints() and store.fetched_at == 0


@pytest.mark.parametrize("content", ["[1]", '"x"', '{"fetched_at": "abc", "data": {}}', '{"fetched_at": [1]}'])
def test_odd_cache_file_is_ignored(cache: Path, content):
    cache.write_text(content, encoding="utf-8")
    store = HintsStore(cache, URL)
    assert store.hints == Hints() and store.fetched_at == 0
