"""engine.binaries: instalación, verificación, rollback y limpieza de yt-dlp / FFmpeg / Deno.

Todo corre contra un "GitHub" y un "gyan.dev" falsos servidos desde un servidor HTTP local, con la descarga
y la verificación SHA-256 reales. yt-dlp es un zipapp de verdad que se ejecuta con `--version`; los .exe
(FFmpeg, Deno) son bytes de relleno y solo su ejecución se simula (no se generan ni corren .exe nuevos).
"""

from __future__ import annotations

import hashlib
import io
import json
import subprocess
import sys
import threading
import zipapp
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from kdownloader.engine import binaries, fetch
from kdownloader.engine.binaries import DENO_ASSET, DENO_REPO, GYAN, YTDLP_REPOS, ComponentState, EngineManager

REAL_GET_TEXT = fetch.get_text
REAL_DOWNLOAD = fetch.download
REAL_RUN_CAPTURE = binaries.run_capture
BTBN = binaries.BTBN

NIGHTLY = "2026.09.27.232945"
EXE_PLACEHOLDER = b"MZ placeholder: no es un ejecutable real"
FFMPEG_OUT = ("ffmpeg version 9.0.2-essentials_build-www.gyan.dev Copyright (c) 2000-2026 the FFmpeg developers\n"
              "built with gcc 15.2.0 (Rev8, Built by MSYS2 project)")
DENO_OUT = "deno 2.9.7 (stable, release, x86_64-pc-windows-msvc)\nv8 14.2.231.9-rusty\ntypescript 5.9.2"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_zip(members: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in members.items():
            z.writestr(name, data)
    return buf.getvalue()


class FakeRemote:
    """GitHub + gyan.dev falsos. `publish_*` deja disponible un componente; `exe` decide qué "imprime" cada .exe."""

    def __init__(self, server, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        self.server = server
        self.tmp = tmp_path / "remote-src"
        self.tmp.mkdir()
        self.tags: dict[str, str] = {}
        self.published: dict[str, bytes] = {}
        self.latest_calls: list[str] = []
        self.downloads: list[str] = []
        self.exe_runs: list[list[str]] = []
        # nombre del .exe → salida de --version, o una excepción a lanzar
        self.exe: dict[str, str | BaseException | tuple[int, str, str]] = {
            "ffmpeg.exe": FFMPEG_OUT, "ffprobe.exe": FFMPEG_OUT.replace("ffmpeg version", "ffprobe version"),
            "deno.exe": DENO_OUT,
        }
        monkeypatch.setattr(fetch, "latest_tag", self.latest_tag)
        monkeypatch.setattr(fetch, "get_text", self.get_text)
        monkeypatch.setattr(fetch, "download", self.download)
        monkeypatch.setattr(binaries, "run_capture", self.run_capture)

    # --- reemplazos de fetch / process
    def latest_tag(self, repo: str, timeout: float = 30) -> str:
        self.latest_calls.append(repo)
        if repo not in self.tags:
            raise RuntimeError(f"No se pudo resolver la última versión de {repo} (404)")
        return self.tags[repo]

    def get_text(self, url: str, timeout: float = 30, limit: int = 2_000_000) -> str:
        return REAL_GET_TEXT(self.server.remap(url), timeout=timeout, limit=limit)

    def download(self, url: str, dest: Path, **kwargs: Any) -> str:
        self.downloads.append(url)
        return REAL_DOWNLOAD(self.server.remap(url), dest, **kwargs)

    def run_capture(self, args: list[str], timeout: float = 30, env=None):
        name = Path(args[0]).name.lower()
        if name in self.exe:
            self.exe_runs.append(list(args))
            exe = Path(args[0])
            assert exe.is_file(), f"se intentó correr {exe} sin extraerlo"
            behavior = self.exe[name]
            if isinstance(behavior, BaseException):
                raise behavior
            if isinstance(behavior, tuple):
                return behavior
            return 0, behavior, ""
        return REAL_RUN_CAPTURE(args, timeout=timeout, env=env)  # yt-dlp: el zipapp corre de verdad

    # --- publicaciones
    def ytdlp_pyz(self, printed: str, exit_code: int = 0) -> bytes:
        src = self.tmp / f"pyz-src-{len(list(self.tmp.iterdir()))}"
        src.mkdir()
        (src / "__main__.py").write_text(
            "import sys\n"
            "if '--version' in sys.argv:\n"
            f"    print({printed!r})\n"
            f"sys.exit({exit_code})\n",
            encoding="utf-8",
        )
        target = src.with_suffix(".pyz")
        zipapp.create_archive(src, target)
        return target.read_bytes()

    def publish_ytdlp(self, tag: str = NIGHTLY, channel: str = "nightly", *, printed: str | None = None,
                      exit_code: int = 0, sums_hash: str | None = None, listed: bool = True) -> bytes:
        repo = YTDLP_REPOS[channel]
        data = self.ytdlp_pyz(printed if printed is not None else tag, exit_code)
        base = f"https://github.com/{repo}/releases/download/{tag}"
        lines = [f"{sha(b'exe')}  yt-dlp.exe", f"{sha(b'zip')}  yt-dlp_win.zip"]
        if listed:
            lines.append(f"{sums_hash or sha(data)}  yt-dlp")
        self.server.add_remote(f"{base}/SHA2-256SUMS", "\n".join(lines) + "\n")
        self.server.add_remote(f"{base}/yt-dlp", data)
        self.tags[repo] = tag
        return data

    def ffmpeg_zip(self, version: str, members: dict[str, bytes] | None = None) -> bytes:
        root = f"ffmpeg-{version}-essentials_build"
        return make_zip(members if members is not None else {
            f"{root}/bin/ffmpeg.exe": EXE_PLACEHOLDER,
            f"{root}/bin/ffprobe.exe": EXE_PLACEHOLDER,
            f"{root}/bin/ffplay.exe": EXE_PLACEHOLDER,  # no se necesita: no se extrae
            f"{root}/bin/avcodec-62.dll": b"dll",
            f"{root}/doc/ffmpeg.html": b"<html>",
            f"{root}/LICENSE": b"GPL",
        })

    def publish_ffmpeg_gyan(self, version: str = "9.0.2", *, members: dict[str, bytes] | None = None,
                            sums_hash: str | None = None) -> bytes:
        data = self.ffmpeg_zip(version, members)
        url = f"{GYAN}/ffmpeg-release-essentials.zip"
        self.server.add_remote(f"{GYAN}/release-version", version)
        self.server.add_remote(url + ".sha256", f"{sums_hash or sha(data)}\n")
        self.server.add_remote(url, data)
        return data

    def publish_ffmpeg_btbn(self, versions: list[str]) -> dict[str, bytes]:
        files = {}
        lines = [f"{sha(b'master')}  ffmpeg-master-latest-win64-gpl.zip",
                 f"{sha(b'linux')}  ffmpeg-n99.0-latest-linux64-lgpl-99.0.tar.xz"]
        for v in versions:
            name = f"ffmpeg-n{v}-latest-win64-lgpl-shared-{v}.zip"
            data = self.ffmpeg_zip(v)
            files[name] = data
            lines.append(f"{sha(data)} *{name}")
            self.server.add_remote(f"{BTBN}/{name}", data)
        self.server.add_remote(f"{BTBN}/checksums.sha256", "\n".join(lines) + "\n")
        return files

    def publish_deno(self, tag: str = "v2.9.7", *, sums_hash: str | None = None) -> bytes:
        data = make_zip({"deno.exe": EXE_PLACEHOLDER})
        base = f"https://github.com/{DENO_REPO}/releases/download/{tag}"
        # Deno firma sus .sha256sum con Get-FileHash | Format-List (hash en mayúsculas)
        text = (f"\r\nAlgorithm : SHA256\r\nHash      : {(sums_hash or sha(data)).upper()}\r\n"
                f"Path      : D:\\a\\deno\\deno\\target\\release\\{DENO_ASSET}\r\n\r\n")
        self.server.add_remote(f"{base}/{DENO_ASSET}.sha256sum", text)
        self.server.add_remote(f"{base}/{DENO_ASSET}", data)
        self.tags[DENO_REPO] = tag
        return data

    def publish_all(self) -> None:
        self.published = {"ytdlp": self.publish_ytdlp(), "ffmpeg": self.publish_ffmpeg_gyan(),
                          "deno": self.publish_deno()}

    def downloads_of(self, fragment: str) -> int:
        return sum(1 for u in self.downloads if fragment in u)


@pytest.fixture
def remote(http_server, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FakeRemote:
    return FakeRemote(http_server, tmp_path, monkeypatch)


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return tmp_path / "engine"


@pytest.fixture
def events() -> list[dict[str, Any]]:
    return []


@pytest.fixture
def new_manager(root: Path, python_exe: Path, events) -> Callable[..., EngineManager]:
    def factory(**kwargs: Any) -> EngineManager:
        kwargs.setdefault("use_system_tools", False)
        return EngineManager(root, python_exe, on_change=events.append, **kwargs)
    return factory


def manifest(root: Path) -> dict[str, Any]:
    path = root / "manifest.json"
    if not path.exists():  # nada se confirmó todavía
        return {"components": {}, "checks": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def all_files(root: Path) -> list[str]:
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())


def install_ytdlp(mgr: EngineManager, remote: FakeRemote, tag: str, channel: str = "nightly", **kw: Any) -> bool:
    remote.publish_ytdlp(tag, channel, **kw)
    return mgr.check_updates(channel=channel, force=True)


# ----------------------------------------------------------------------------- estado inicial


def test_initial_state(new_manager, events):
    mgr = new_manager()
    st = mgr.status()
    assert set(st) == {"ytdlp", "ffmpeg", "deno", "ready", "busy"}
    for name in ("ytdlp", "ffmpeg", "deno"):
        assert st[name]["state"] == "missing"
        assert st[name]["version"] is None and st[name]["source"] is None
        assert st[name]["progress"] is None
        assert set(st[name]) >= {"name", "state", "version", "source", "done", "total", "error", "progress"}
    assert st["ready"] is False and st["busy"] is False
    assert mgr.ready() is False
    assert mgr.ytdlp_path() is None and mgr.ffmpeg_dir() is None and mgr.deno_path() is None
    assert events and events[-1] == st  # el constructor emite el estado inicial
    json.dumps(st)


def test_component_state_progress():
    assert ComponentState("ytdlp", done=50, total=200).to_dict()["progress"] == 0.25
    assert ComponentState("ytdlp", done=50, total=0).to_dict()["progress"] is None


# ----------------------------------------------------------------------------- instalación completa


def test_ensure_installs_everything(remote: FakeRemote, new_manager, root: Path, events):
    remote.publish_all()
    mgr = new_manager()
    assert mgr.ensure() is True
    st = mgr.status()
    assert st["ready"] is True and st["busy"] is False
    assert (st["ytdlp"]["state"], st["ytdlp"]["version"], st["ytdlp"]["source"]) == ("ready", NIGHTLY, "managed")
    assert (st["ffmpeg"]["state"], st["ffmpeg"]["version"]) == ("ready", "9.0.2")
    assert (st["deno"]["state"], st["deno"]["version"]) == ("ready", "2.9.7")

    assert mgr.ytdlp_path() == root / "ytdlp" / NIGHTLY / "yt-dlp.pyz"
    assert mgr.ytdlp_version() == NIGHTLY
    assert mgr.ffmpeg_dir() == root / "ffmpeg" / "gyan-9.0.2"
    assert mgr.deno_path() == root / "deno" / "v2.9.7" / "deno.exe"
    assert mgr.deno_path().read_bytes() == EXE_PLACEHOLDER

    files = all_files(root)
    assert files == sorted([
        "manifest.json",
        f"ytdlp/{NIGHTLY}/yt-dlp.pyz",
        "ffmpeg/gyan-9.0.2/ffmpeg.exe",
        "ffmpeg/gyan-9.0.2/ffprobe.exe",
        "ffmpeg/gyan-9.0.2/avcodec-62.dll",
        "deno/v2.9.7/deno.exe",
    ])  # sin ffplay, docs, .part ni zips de descarga

    m = manifest(root)["components"]
    assert m["ytdlp"]["current"] == f"ytdlp/{NIGHTLY}/yt-dlp.pyz"
    assert m["ytdlp"]["channel"] == "nightly"
    assert m["ytdlp"]["sha256"] == fetch.sha256_file(mgr.ytdlp_path())
    assert m["ffmpeg"]["origin"] == "gyan.dev"
    assert m["deno"]["sha256"] == sha(remote.published["deno"])
    assert m["ffmpeg"]["sha256"] == sha(remote.published["ffmpeg"])

    # Cada componente pasó por checking → downloading → installing → ready (y la UI se enteró).
    for name in ("ytdlp", "ffmpeg", "deno"):
        seen = []
        for ev in events:
            s = ev[name]["state"]
            if not seen or seen[-1] != s:
                seen.append(s)
        assert seen[-4:] == ["checking", "downloading", "installing", "ready"], (name, seen)
    assert any(ev["busy"] for ev in events)
    # La validación del exe se hizo sobre lo extraído (ffmpeg y ffprobe) y sobre deno.
    ran = sorted(Path(r[0]).name for r in remote.exe_runs)
    assert ran == ["deno.exe", "ffmpeg.exe", "ffprobe.exe"]


def test_ytdlp_version_check_really_runs_the_zipapp(remote: FakeRemote, new_manager, python_exe: Path):
    remote.publish_all()
    remote.publish_ytdlp("2026.10.01.000000", printed="Aviso: algo\n2026.10.01.000007")
    mgr = new_manager()
    mgr.ensure(include_deno=False)
    # La versión registrada es la que imprimió el zipapp al correr con el Python real (última línea).
    assert mgr.ytdlp_version() == "2026.10.01.000007"
    rc, out, _ = binaries.run_capture([str(python_exe), "-I", "-X", "utf8", str(mgr.ytdlp_path()), "--version"])
    assert rc == 0 and out.splitlines()[-1] == "2026.10.01.000007"


def test_ready_needs_only_ytdlp_and_ffmpeg(remote: FakeRemote, new_manager):
    remote.publish_ytdlp()
    remote.publish_ffmpeg_gyan()  # sin Deno publicado
    mgr = new_manager()
    assert mgr.ensure() is True
    st = mgr.status()
    assert st["ready"] is True
    assert st["deno"]["state"] == "error" and st["deno"]["error"]


def test_ensure_without_deno(remote: FakeRemote, new_manager):
    remote.publish_all()
    mgr = new_manager()
    assert mgr.ensure(include_deno=False) is True
    assert mgr.status()["deno"]["state"] == "missing"
    assert DENO_REPO not in remote.latest_calls


def test_ensure_skips_ready_components(remote: FakeRemote, new_manager):
    remote.publish_all()
    mgr = new_manager()
    mgr.ensure()
    n = len(remote.downloads)
    assert mgr.ensure() is True
    assert len(remote.downloads) == n  # nada que bajar


def test_state_survives_restart(remote: FakeRemote, new_manager):
    remote.publish_all()
    new_manager().ensure()
    again = new_manager()
    st = again.status()
    assert st["ready"] is True
    assert st["ytdlp"]["version"] == NIGHTLY and st["deno"]["version"] == "2.9.7"


def test_deleted_component_is_detected_on_restart(remote: FakeRemote, new_manager):
    remote.publish_all()
    mgr = new_manager()
    mgr.ensure()
    mgr.ytdlp_path().unlink()  # p. ej. el antivirus lo borró
    again = new_manager()
    assert again.status()["ytdlp"]["state"] == "missing"
    assert again.ready() is False
    assert again.ytdlp_path() is None


def test_on_change_errors_are_swallowed(remote: FakeRemote, root: Path, python_exe: Path):
    remote.publish_all()

    def boom(_status: dict) -> None:
        raise RuntimeError("UI caída")

    mgr = EngineManager(root, python_exe, on_change=boom, use_system_tools=False)
    assert mgr.ensure() is True


# ----------------------------------------------------------------------------- verificación


def test_ytdlp_hash_mismatch_commits_nothing(remote: FakeRemote, new_manager, root: Path):
    remote.publish_ytdlp(sums_hash="0" * 64)
    remote.publish_ffmpeg_gyan()
    mgr = new_manager()
    assert mgr.ensure(include_deno=False) is False
    st = mgr.status()["ytdlp"]
    assert st["state"] == "error"
    assert "Hash" in st["error"]
    assert mgr.ytdlp_path() is None
    assert "current" not in manifest(root)["components"].get("ytdlp", {})
    assert not any(f.startswith("ytdlp/") for f in all_files(root))  # ni el archivo ni el .part
    assert mgr.status()["ffmpeg"]["state"] == "ready"  # un fallo no frena a los demás


def test_ytdlp_not_listed_in_sums_is_refused(remote: FakeRemote, new_manager, root: Path):
    remote.publish_ytdlp(listed=False)
    mgr = new_manager()
    mgr.ensure(include_deno=False)
    assert mgr.status()["ytdlp"]["state"] == "error"
    assert "hash" in mgr.status()["ytdlp"]["error"].lower()
    assert not any(f.startswith("ytdlp/") for f in all_files(root))


def test_ytdlp_too_old_is_rejected(remote: FakeRemote, new_manager, root: Path):
    remote.publish_ytdlp("2026.03.03")  # la versión que daba 403
    mgr = new_manager()
    mgr.ensure(include_deno=False)
    st = mgr.status()["ytdlp"]
    assert st["state"] == "error" and "2026.03.03" in st["error"]
    assert "current" not in manifest(root)["components"].get("ytdlp", {})


def test_ytdlp_that_fails_to_run_is_rejected(remote: FakeRemote, new_manager, root: Path):
    remote.publish_ytdlp(exit_code=3)
    mgr = new_manager()
    mgr.ensure(include_deno=False)
    assert mgr.status()["ytdlp"]["state"] == "error"
    assert mgr.ytdlp_path() is None


def test_ffmpeg_hash_mismatch_falls_back_to_btbn(remote: FakeRemote, new_manager, root: Path):
    remote.publish_ytdlp()
    remote.publish_ffmpeg_gyan(sums_hash="f" * 64)
    remote.publish_ffmpeg_btbn(["8.1", "9.0", "10.0"])
    mgr = new_manager()
    assert mgr.ensure(include_deno=False) is True
    entry = manifest(root)["components"]["ffmpeg"]
    assert entry["origin"] == "BtbN" and entry["version"] == "10.0"  # la mayor rama publicada
    assert entry["current"].startswith("ffmpeg/btbn-10.0-")
    assert mgr.ffmpeg_dir() == root / entry["current"]
    assert not (root / "ffmpeg" / "gyan-9.0.2").exists()  # el zip de gyan con hash malo ni se extrajo


def test_ffmpeg_btbn_picks_numeric_max(remote: FakeRemote, new_manager, root: Path):
    remote.publish_ytdlp()
    remote.server.add_remote(f"{GYAN}/release-version", "", status=503)  # gyan.dev caído
    remote.publish_ffmpeg_btbn(["9.10", "9.9", "8.1"])
    mgr = new_manager()
    mgr.ensure(include_deno=False)
    assert manifest(root)["components"]["ffmpeg"]["version"] == "9.10"


def test_ffmpeg_everything_fails(remote: FakeRemote, new_manager, root: Path):
    remote.publish_ytdlp()
    mgr = new_manager()
    assert mgr.ensure(include_deno=False) is False
    st = mgr.status()["ffmpeg"]
    assert st["state"] == "error" and st["error"]
    assert "ffmpeg" not in manifest(root)["components"] or "current" not in manifest(root)["components"]["ffmpeg"]


def test_ffmpeg_zip_without_ffprobe_is_rejected(remote: FakeRemote, new_manager, root: Path):
    remote.publish_ytdlp()
    remote.publish_ffmpeg_gyan(members={"ffmpeg-9.0.2-essentials_build/bin/ffmpeg.exe": EXE_PLACEHOLDER})
    mgr = new_manager()
    mgr.ensure(include_deno=False)
    assert mgr.status()["ffmpeg"]["state"] == "error"
    assert mgr.ffmpeg_dir() is None
    assert not list((root / "downloads").glob("*.zip"))  # el zip descargado se borra igual


def test_ffmpeg_that_does_not_run_is_rejected(remote: FakeRemote, new_manager):
    remote.publish_ytdlp()
    remote.publish_ffmpeg_gyan()
    remote.exe["ffprobe.exe"] = (1, "", "error: falta una DLL")
    mgr = new_manager()
    mgr.ensure(include_deno=False)
    assert mgr.status()["ffmpeg"]["state"] == "error"
    assert mgr.ffmpeg_dir() is None


def test_deno_hash_mismatch(remote: FakeRemote, new_manager, root: Path):
    remote.publish_ytdlp()
    remote.publish_ffmpeg_gyan()
    remote.publish_deno(sums_hash="a" * 64)
    mgr = new_manager()
    assert mgr.ensure() is True
    assert mgr.status()["deno"]["state"] == "error"
    assert mgr.deno_path() is None
    assert not any(f.startswith("deno/") for f in all_files(root))


@pytest.mark.skipif(sys.platform != "win32", reason="WinError 4551 solo existe en Windows")
def test_blocked_by_smart_app_control(remote: FakeRemote, new_manager):
    remote.publish_all()
    remote.exe["deno.exe"] = OSError(None, "An Application Control policy has blocked this file", None, 4551)
    mgr = new_manager()
    assert mgr.ensure() is True
    st = mgr.status()["deno"]
    assert st["state"] == "blocked" and st["error"]
    assert mgr.deno_path() is None


def test_exe_timeout_is_an_error(remote: FakeRemote, new_manager):
    remote.publish_all()
    remote.exe["deno.exe"] = subprocess.TimeoutExpired(["deno.exe"], 60)
    mgr = new_manager()
    mgr.ensure()
    assert mgr.status()["deno"]["state"] == "error"


def test_cancel_during_download(remote: FakeRemote, new_manager):
    remote.publish_all()
    mgr = new_manager()
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(fetch.Cancelled):
        mgr.ensure(cancel=cancel)
    st = mgr.status()
    assert st["ytdlp"]["state"] == "missing" and st["busy"] is False
    assert mgr.ytdlp_path() is None


# ----------------------------------------------------------------------------- actualizaciones y rollback


def test_check_updates_not_due_makes_no_requests(remote: FakeRemote, new_manager):
    remote.publish_all()
    mgr = new_manager()
    mgr.ensure()
    assert mgr.check_updates(force=True) is False  # misma versión: no cambia
    calls = len(remote.latest_calls)
    assert mgr.check_updates() is False
    assert len(remote.latest_calls) == calls  # dentro de las 24 h no consulta nada


def test_update_and_rollback(remote: FakeRemote, new_manager, root: Path):
    remote.publish_all()
    mgr = new_manager()
    mgr.ensure()
    a = NIGHTLY
    b = "2026.10.02.101010"
    assert install_ytdlp(mgr, remote, b) is True
    assert mgr.ytdlp_version() == b
    entry = manifest(root)["components"]["ytdlp"]
    assert (entry["previous"], entry["previous_version"]) == (f"ytdlp/{a}/yt-dlp.pyz", a)

    assert mgr.rollback_ytdlp() is True
    assert mgr.ytdlp_version() == a
    assert mgr.ytdlp_path() == root / "ytdlp" / a / "yt-dlp.pyz"
    assert mgr.status()["ytdlp"]["version"] == a
    entry = manifest(root)["components"]["ytdlp"]
    assert (entry["previous"], entry["previous_version"]) == (f"ytdlp/{b}/yt-dlp.pyz", b)

    assert mgr.rollback_ytdlp() is True  # y de vuelta
    assert mgr.ytdlp_version() == b


def test_rollback_without_previous(remote: FakeRemote, new_manager, root: Path):
    remote.publish_all()
    mgr = new_manager()
    assert mgr.rollback_ytdlp() is False  # nada instalado
    mgr.ensure()
    assert mgr.rollback_ytdlp() is False  # una sola versión
    install_ytdlp(mgr, remote, "2026.10.02.101010")
    (root / "ytdlp" / NIGHTLY / "yt-dlp.pyz").unlink()
    assert mgr.rollback_ytdlp() is False  # la anterior ya no existe
    assert mgr.ytdlp_version() == "2026.10.02.101010"


def test_prune_keeps_current_and_previous(remote: FakeRemote, new_manager, root: Path):
    remote.publish_all()
    mgr = new_manager()
    mgr.ensure()
    for tag in ("2026.10.01.000001", "2026.10.02.000002", "2026.10.03.000003"):
        install_ytdlp(mgr, remote, tag)
    kept = sorted(p.name for p in (root / "ytdlp").iterdir())
    assert kept == ["2026.10.02.000002", "2026.10.03.000003"]


def test_in_use_versions_are_not_deleted(remote: FakeRemote, new_manager, root: Path):
    remote.publish_all()
    mgr = new_manager()
    mgr.ensure()
    mgr.acquire()  # una descarga en curso usa NIGHTLY
    for tag in ("2026.10.01.000001", "2026.10.02.000002", "2026.10.03.000003"):
        install_ytdlp(mgr, remote, tag)
    kept = sorted(p.name for p in (root / "ytdlp").iterdir())
    assert kept == [NIGHTLY, "2026.10.02.000002", "2026.10.03.000003"]
    assert (root / "ytdlp" / NIGHTLY / "yt-dlp.pyz").is_file()


def test_release_frees_what_acquire_took(remote: FakeRemote, new_manager, root: Path):
    remote.publish_all()
    mgr = new_manager()
    mgr.ensure()
    job1 = mgr.acquire()  # trabajo 1 → NIGHTLY
    b = "2026.10.01.000001"
    install_ytdlp(mgr, remote, b)
    mgr.acquire()  # trabajo 2 → b
    mgr.release(job1)  # termina el trabajo 1
    for tag in ("2026.10.02.000002", "2026.10.03.000003"):
        install_ytdlp(mgr, remote, tag)
    assert (root / "ytdlp" / b / "yt-dlp.pyz").is_file(), "se borró la versión que usa el trabajo 2"
    assert not (root / "ytdlp" / NIGHTLY).exists(), "la versión del trabajo 1 quedó retenida para siempre"


def test_prune_does_not_keep_prefix_lookalikes(remote: FakeRemote, new_manager, root: Path):
    remote.publish_all()
    mgr = new_manager()
    install_ytdlp(mgr, remote, "2026.09.27", channel="stable")
    install_ytdlp(mgr, remote, "2026.09.27.232945", channel="nightly")
    install_ytdlp(mgr, remote, "2026.09.28.000000", channel="nightly")
    kept = sorted(p.name for p in (root / "ytdlp").iterdir())
    assert kept == ["2026.09.27.232945", "2026.09.28.000000"]


def test_channel_switch_reinstalls(remote: FakeRemote, new_manager, root: Path):
    remote.publish_all()
    mgr = new_manager()
    mgr.ensure()
    mgr.check_updates(force=True)  # deja las revisiones al día
    remote.publish_ytdlp("2026.09.20", channel="stable")
    calls = len(remote.latest_calls)
    assert mgr.check_updates(channel="stable") is True  # no vencía, pero cambió el canal
    assert YTDLP_REPOS["stable"] in remote.latest_calls[calls:]
    entry = manifest(root)["components"]["ytdlp"]
    assert (entry["channel"], entry["version"]) == ("stable", "2026.09.20")
    assert entry["previous_version"] == NIGHTLY
    assert mgr.check_updates(channel="stable") is False  # ya en el canal: no vuelve a instalar


def test_minimum_hint_forces_update(remote: FakeRemote, new_manager):
    remote.publish_all()
    mgr = new_manager()
    mgr.ensure()
    mgr.check_updates(force=True)
    remote.publish_ytdlp("2026.10.05.010101")
    assert mgr.check_updates(minimum="2026.10.01") is True  # engine.json pidió un mínimo más nuevo
    assert mgr.ytdlp_version() == "2026.10.05.010101"


def test_deno_checked_monthly(remote: FakeRemote, new_manager):
    remote.publish_all()
    mgr = new_manager()
    mgr.ensure()
    mgr.check_updates(force=True)
    remote.publish_deno("v2.9.8")
    mgr.check_updates()
    assert mgr.status()["deno"]["version"] == "2.9.7"  # no venció el mes
    mgr.check_updates(force=True)
    assert remote.downloads_of("v2.9.8") == 1


def test_repair_one_component(remote: FakeRemote, new_manager):
    remote.publish_all()
    mgr = new_manager()
    mgr.ensure()
    before = {k: remote.downloads_of(k) for k in ("/yt-dlp", "ffmpeg-release", DENO_ASSET)}
    assert mgr.repair("ffmpeg") is True
    assert remote.downloads_of("ffmpeg-release") == before["ffmpeg-release"] + 1
    assert remote.downloads_of("/yt-dlp") == before["/yt-dlp"]
    assert mgr.status()["ffmpeg"]["state"] == "ready"


def test_repair_all(remote: FakeRemote, new_manager):
    remote.publish_all()
    mgr = new_manager()
    mgr.ensure()
    n = len(remote.downloads)
    assert mgr.repair(None) is True
    assert len(remote.downloads) == n + 3
    assert mgr.ready()


# ----------------------------------------------------------------------------- herramientas del sistema


@pytest.fixture
def system_tools(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    folder = tmp_path / "system bin"
    folder.mkdir()
    tools = {}
    for name in ("ffmpeg", "ffprobe", "deno"):
        exe = folder / f"{name}.exe"
        exe.write_bytes(EXE_PLACEHOLDER)
        tools[name] = exe
    monkeypatch.setattr(binaries.shutil, "which", lambda name: str(tools[name]) if name in tools else None)
    return tools


def test_system_ffmpeg_and_deno_are_used_when_allowed(remote: FakeRemote, new_manager, system_tools):
    remote.publish_all()
    mgr = new_manager(use_system_tools=True)
    assert mgr.ensure() is True
    st = mgr.status()
    assert (st["ffmpeg"]["source"], st["ffmpeg"]["version"]) == ("system", "9.0.2")
    assert (st["deno"]["source"], st["deno"]["version"]) == ("system", "2.9.7")
    assert mgr.ffmpeg_dir() == system_tools["ffmpeg"].parent
    assert mgr.deno_path() == system_tools["deno"]
    assert remote.downloads_of("ffmpeg") == 0 and remote.downloads_of("deno") == 0


def test_old_system_ffmpeg_is_ignored(remote: FakeRemote, new_manager, system_tools):
    remote.publish_all()
    remote.exe["ffmpeg.exe"] = "ffmpeg version 8.1-full_build Copyright (c) 2000-2026"  # 8.1 se cuelga
    remote.exe["deno.exe"] = "deno 2.2.0 (stable)"  # demasiado viejo
    mgr = new_manager(use_system_tools=True)
    mgr.ensure()
    st = mgr.status()
    assert st["ffmpeg"]["source"] == "managed"
    assert st["deno"]["source"] == "managed"


def test_system_tools_disabled(remote: FakeRemote, new_manager, system_tools):
    remote.publish_all()
    mgr = new_manager(use_system_tools=False)
    mgr.ensure()
    assert mgr.status()["ffmpeg"]["source"] == "managed"
    assert mgr.status()["deno"]["source"] == "managed"


@pytest.mark.parametrize("content", ["[1]", '{"components": []}', '{"components": {"ytdlp": "x"}}'])
def test_odd_manifest_is_treated_as_empty(root: Path, new_manager, content):
    root.mkdir(parents=True)
    (root / "manifest.json").write_text(content, encoding="utf-8")
    mgr = new_manager()
    assert mgr.status()["ytdlp"]["state"] == "missing"
