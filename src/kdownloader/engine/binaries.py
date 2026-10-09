"""Gestión de los componentes del motor: yt-dlp (zipapp), FFmpeg y Deno.

Diseño (validado en la Fase 0 con Smart App Control activo):
- yt-dlp se usa como zipapp de Python puro, ejecutado por el Python oficial firmado: no es un .exe,
  así que Windows nunca lo bloquea y cualquier canal (nightly/estable) sirve.
- FFmpeg viene de gyan.dev (release essentials, con reputación en Windows) y Deno es oficial y firmado.
- Cada versión se instala en su propia carpeta y `manifest.json` apunta a la actual y a la anterior
  (rollback). Una actualización nunca toca archivos que una descarga en curso está usando.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import threading
import time
import zipfile
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ..util import log, read_json, write_json_atomic
from . import fetch
from .process import run_capture
from .versions import parse_semver, semver_at_least, ytdlp_at_least

YTDLP_REPOS = {"nightly": "yt-dlp/yt-dlp-nightly-builds", "stable": "yt-dlp/yt-dlp"}
MIN_YTDLP = {"nightly": "2026.09.27.232945", "stable": "2026.08.19"}
MIN_DENO = "2.3.0"
MIN_SYSTEM_FFMPEG = "9.0"
GYAN = "https://www.gyan.dev/ffmpeg/builds"
BTBN = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest"
DENO_REPO = "denoland/deno"
DENO_ASSET = "deno-x86_64-pc-windows-msvc.zip"
YTDLP_CHECK_EVERY = 24 * 3600
DENO_CHECK_EVERY = 30 * 24 * 3600
BLOCKED_WINERROR = 4551  # "An Application Control policy has blocked this file"

COMPONENTS = ("ytdlp", "ffmpeg", "deno")
REQUIRED = ("ytdlp", "ffmpeg")


@dataclass
class ComponentState:
    name: str
    state: str = "missing"  # missing | checking | downloading | installing | ready | error | blocked
    version: str | None = None
    source: str | None = None  # managed | system
    done: int = 0
    total: int = 0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["progress"] = (self.done / self.total) if self.total else None
        return d


class ComponentBlocked(Exception):
    """Windows (Smart App Control / antivirus) no dejó ejecutar el componente."""


class EngineManager:
    def __init__(self, root: Path, python_exe: Path, on_change: Callable[[dict[str, Any]], None] | None = None,
                 use_system_tools: bool = True):
        self.root = root
        self.python_exe = python_exe
        self.on_change = on_change
        self.use_system_tools = use_system_tools
        self.manifest_path = root / "manifest.json"
        self._lock = threading.RLock()
        self._busy = threading.Lock()
        self._in_use: dict[str, int] = {}
        self._last_emit = 0.0
        self.manifest: dict[str, Any] = read_json(self.manifest_path, default=None) or {"components": {}, "checks": {}}
        self.states = {name: ComponentState(name) for name in COMPONENTS}
        self.refresh()

    # ------------------------------------------------------------------ estado
    def _entry(self, name: str) -> dict[str, Any]:
        return self.manifest.setdefault("components", {}).setdefault(name, {})

    def _save(self) -> None:
        write_json_atomic(self.manifest_path, self.manifest)

    def _current_path(self, name: str) -> Path | None:
        entry = self.manifest.get("components", {}).get(name) or {}
        rel = entry.get("current")
        if not rel:
            return None
        path = self.root / rel
        return path if path.exists() else None

    def refresh(self) -> None:
        """Recalcula el estado de cada componente a partir del manifiesto y del sistema."""
        with self._lock:
            for name in COMPONENTS:
                st = self.states[name]
                if st.state in ("downloading", "installing", "checking"):
                    continue
                path = self._current_path(name)
                entry = self.manifest.get("components", {}).get(name) or {}
                if path:
                    st.state, st.version, st.source, st.error = "ready", entry.get("version"), "managed", None
                elif entry.get("system") and self.use_system_tools and Path(entry["system"]).exists():
                    st.state, st.version, st.source, st.error = "ready", entry.get("system_version"), "system", None
                elif st.state not in ("error", "blocked"):
                    st.state, st.version, st.source = "missing", None, None
        self._emit(force=True)

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {name: st.to_dict() for name, st in self.states.items()} | {
                "ready": self.ready(), "busy": self._busy.locked()}

    def ready(self) -> bool:
        return all(self.states[n].state == "ready" for n in REQUIRED)

    def _emit(self, force: bool = False) -> None:
        now = time.monotonic()
        if not force and now - self._last_emit < 0.2:
            return
        self._last_emit = now
        if self.on_change:
            try:
                self.on_change(self.status())
            except Exception:  # noqa: BLE001
                log.exception("on_change falló")

    def _set(self, name: str, **changes: Any) -> None:
        with self._lock:
            for key, value in changes.items():
                setattr(self.states[name], key, value)
        self._emit(force="state" in changes)

    # ------------------------------------------------------------------ rutas para el motor
    def ytdlp_path(self) -> Path | None:
        return self._current_path("ytdlp")

    def ytdlp_version(self) -> str | None:
        return (self.manifest.get("components", {}).get("ytdlp") or {}).get("version")

    def ffmpeg_dir(self) -> Path | None:
        path = self._current_path("ffmpeg")
        if path:
            return path
        entry = self.manifest.get("components", {}).get("ffmpeg") or {}
        if entry.get("system") and self.use_system_tools:
            return Path(entry["system"]).parent
        return None

    def deno_path(self) -> Path | None:
        path = self._current_path("deno")
        if path:
            return path
        entry = self.manifest.get("components", {}).get("deno") or {}
        if entry.get("system") and self.use_system_tools and Path(entry["system"]).exists():
            return Path(entry["system"])
        return None

    def acquire(self) -> None:
        """Marca las versiones actuales como en uso (no se borran mientras corre una descarga)."""
        with self._lock:
            for name in COMPONENTS:
                rel = (self.manifest.get("components", {}).get(name) or {}).get("current")
                if rel:
                    self._in_use[rel] = self._in_use.get(rel, 0) + 1

    def release(self) -> None:
        with self._lock:
            for name in COMPONENTS:
                rel = (self.manifest.get("components", {}).get(name) or {}).get("current")
                if rel and self._in_use.get(rel):
                    self._in_use[rel] -= 1

    # ------------------------------------------------------------------ instalación
    def ensure(self, channel: str = "nightly", cancel: threading.Event | None = None,
               include_deno: bool = True) -> bool:
        """Instala lo que falte. Devuelve True si los componentes obligatorios quedaron listos."""
        with self._busy:
            if self.states["ytdlp"].state != "ready":
                self._guard("ytdlp", lambda: self._install_ytdlp(channel, cancel))
            if self.states["ffmpeg"].state != "ready":
                self._guard("ffmpeg", lambda: self._install_ffmpeg(cancel))
            if include_deno and self.states["deno"].state != "ready":
                self._guard("deno", lambda: self._install_deno(cancel))
        return self.ready()

    def check_updates(self, channel: str = "nightly", force: bool = False, minimum: str | None = None,
                      cancel: threading.Event | None = None) -> bool:
        """Actualiza yt-dlp (y Deno cada mes). Devuelve True si yt-dlp cambió de versión."""
        changed = False
        with self._busy:
            checks = self.manifest.setdefault("checks", {})
            now = time.time()
            current = self.ytdlp_version()
            entry = self._entry("ytdlp")
            need_min = minimum or MIN_YTDLP.get(channel)
            due = force or now - float(checks.get("ytdlp", 0)) > YTDLP_CHECK_EVERY
            wrong_channel = entry.get("channel") not in (None, channel)
            if due or wrong_channel or not ytdlp_at_least(current, need_min):
                before = current
                self._guard("ytdlp", lambda: self._install_ytdlp(channel, cancel))
                checks["ytdlp"] = now
                changed = self.ytdlp_version() != before
            if force or now - float(checks.get("deno", 0)) > DENO_CHECK_EVERY:
                self._guard("deno", lambda: self._install_deno(cancel))
                checks["deno"] = now
            self._save()
        return changed

    def repair(self, component: str | None = None, channel: str = "nightly",
               cancel: threading.Event | None = None) -> bool:
        names = [component] if component in COMPONENTS else list(COMPONENTS)
        with self._lock:
            for name in names:
                entry = self._entry(name)
                entry.pop("current", None)
                entry.pop("system", None)
                self.states[name] = ComponentState(name)
            self._save()
        return self.ensure(channel=channel, cancel=cancel)

    def rollback_ytdlp(self) -> bool:
        with self._lock:
            entry = self._entry("ytdlp")
            prev = entry.get("previous")
            if not prev or not (self.root / prev).exists():
                return False
            entry["current"], entry["previous"] = prev, entry.get("current")
            entry["version"], entry["previous_version"] = entry.get("previous_version"), entry.get("version")
            self._save()
        self.refresh()
        return True

    def _guard(self, name: str, action: Callable[[], None]) -> None:
        try:
            action()
        except fetch.Cancelled:
            self._set(name, state="missing" if not self._current_path(name) else "ready", done=0, total=0)
            raise
        except ComponentBlocked as exc:
            log.warning("Componente %s bloqueado por Windows: %s", name, exc)
            self._set(name, state="blocked", error=str(exc), done=0, total=0)
        except Exception as exc:  # noqa: BLE001 - se informa en la UI y se reintenta luego
            log.exception("No se pudo instalar %s", name)
            ok = self._current_path(name) is not None
            self._set(name, state="ready" if ok else "error", error=None if ok else str(exc), done=0, total=0)

    def _progress(self, name: str) -> Callable[[int, int], None]:
        def cb(done: int, total: int) -> None:
            with self._lock:
                st = self.states[name]
                st.done, st.total = done, total
            self._emit()
        return cb

    def _commit(self, name: str, rel: str, version: str, **extra: Any) -> None:
        with self._lock:
            entry = self._entry(name)
            if entry.get("current") and entry.get("current") != rel:
                entry["previous"], entry["previous_version"] = entry["current"], entry.get("version")
            entry.update({"current": rel, "version": version, "installed_at": time.time(), **extra})
            entry.pop("system", None)
            self._save()
            self.states[name] = ComponentState(name, state="ready", version=version, source="managed")
        self._emit(force=True)
        self._prune(name)

    def _prune(self, name: str) -> None:
        """Borra versiones viejas que no sean la actual, la anterior ni estén en uso."""
        entry = self._entry(name)
        keep = {entry.get("current"), entry.get("previous")}
        folder = self.root / name
        if not folder.is_dir():
            return
        for child in folder.iterdir():
            rel = f"{name}/{child.name}"
            if not any(k and k.startswith(rel) for k in keep) and not any(
                    k.startswith(rel) and n for k, n in self._in_use.items()):
                shutil.rmtree(child, ignore_errors=True)

    def _run_check(self, args: list[str]) -> str:
        try:
            rc, out, err = run_capture(args, timeout=60)
        except OSError as exc:
            if getattr(exc, "winerror", None) == BLOCKED_WINERROR:
                raise ComponentBlocked("Smart App Control bloqueó el archivo") from exc
            raise
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("El componente no respondió") from exc
        if rc != 0:
            raise RuntimeError((err or out).strip()[-300:] or f"código {rc}")
        return out.strip()

    # ------------------------------------------------------------------ yt-dlp
    def _install_ytdlp(self, channel: str, cancel: threading.Event | None) -> None:
        repo = YTDLP_REPOS.get(channel, YTDLP_REPOS["nightly"])
        self._set("ytdlp", state="checking", error=None)
        tag = fetch.latest_tag(repo)
        entry = self._entry("ytdlp")
        if entry.get("version") == tag and entry.get("channel") == channel and self._current_path("ytdlp"):
            self._set("ytdlp", state="ready")
            return
        base = f"https://github.com/{repo}/releases/download/{tag}"
        want = fetch.find_sha256(fetch.get_text(f"{base}/SHA2-256SUMS"), "yt-dlp")
        rel = f"ytdlp/{tag}/yt-dlp.pyz"
        dest = self.root / rel
        self._set("ytdlp", state="downloading", done=0, total=0)
        digest = fetch.download(f"{base}/yt-dlp", dest, expected_sha256=want, on_progress=self._progress("ytdlp"),
                                cancel=cancel)
        self._set("ytdlp", state="installing")
        version = self._run_check([str(self.python_exe), "-I", "-X", "utf8", str(dest), "--version"]).splitlines()[-1]
        if not ytdlp_at_least(version, "2026.08.19"):
            raise RuntimeError(f"Versión inesperada de yt-dlp: {version}")
        self._commit("ytdlp", rel, version, channel=channel, sha256=digest)
        log.info("yt-dlp %s (%s) instalado", version, channel)

    # ------------------------------------------------------------------ FFmpeg
    def _system_ffmpeg(self) -> tuple[Path, str] | None:
        ff, fp = shutil.which("ffmpeg"), shutil.which("ffprobe")
        if not (ff and fp):
            return None
        try:
            first = self._run_check([ff, "-hide_banner", "-version"]).splitlines()[0]
        except Exception:  # noqa: BLE001
            return None
        m = re.search(r"version\s+n?(\d+\.\d+(?:\.\d+)?)", first)
        if m and semver_at_least(m.group(1), MIN_SYSTEM_FFMPEG):
            return Path(ff), m.group(1)
        return None

    def _install_ffmpeg(self, cancel: threading.Event | None) -> None:
        self._set("ffmpeg", state="checking", error=None)
        if self.use_system_tools:
            found = self._system_ffmpeg()
            if found:
                with self._lock:
                    entry = self._entry("ffmpeg")
                    entry.update({"system": str(found[0]), "system_version": found[1]})
                    self._save()
                    self.states["ffmpeg"] = ComponentState("ffmpeg", state="ready", version=found[1], source="system")
                self._emit(force=True)
                return
        try:
            self._install_ffmpeg_gyan(cancel)
        except (ComponentBlocked, fetch.Cancelled):
            raise
        except Exception as exc:  # noqa: BLE001
            log.warning("gyan.dev falló (%s); se intenta BtbN", exc)
            self._install_ffmpeg_btbn(cancel)

    def _extract_ffmpeg(self, archive: Path, rel_dir: str) -> Path:
        target = self.root / rel_dir
        target.mkdir(parents=True, exist_ok=True)
        wanted = re.compile(r"(^|/)bin/(ffmpeg\.exe|ffprobe\.exe|[^/]+\.dll)$", re.IGNORECASE)
        found = set()
        with zipfile.ZipFile(archive) as z:
            for info in z.infolist():
                if info.is_dir() or not wanted.search(info.filename):
                    continue
                name = Path(info.filename).name
                with z.open(info) as src, open(target / name, "wb") as out:
                    shutil.copyfileobj(src, out, 1024 * 1024)
                found.add(name.lower())
        if not {"ffmpeg.exe", "ffprobe.exe"} <= found:
            raise RuntimeError("El paquete de FFmpeg no trae ffmpeg.exe y ffprobe.exe")
        return target

    def _finish_ffmpeg(self, archive: Path, rel_dir: str, version: str, source: str, digest: str) -> None:
        self._set("ffmpeg", state="installing")
        try:
            target = self._extract_ffmpeg(archive, rel_dir)
        finally:
            archive.unlink(missing_ok=True)
        self._run_check([str(target / "ffmpeg.exe"), "-hide_banner", "-version"])
        self._run_check([str(target / "ffprobe.exe"), "-hide_banner", "-version"])
        self._commit("ffmpeg", rel_dir, version, origin=source, sha256=digest)
        log.info("FFmpeg %s (%s) instalado", version, source)

    def _install_ffmpeg_gyan(self, cancel: threading.Event | None) -> None:
        version = fetch.get_text(f"{GYAN}/release-version", timeout=20).strip()
        if not parse_semver(version):
            raise RuntimeError(f"Versión de FFmpeg inesperada: {version!r}")
        url = f"{GYAN}/ffmpeg-release-essentials.zip"
        want = fetch.find_sha256(fetch.get_text(url + ".sha256", timeout=20))
        archive = self.root / "downloads" / f"ffmpeg-{version}.zip"
        self._set("ffmpeg", state="downloading", done=0, total=0)
        digest = fetch.download(url, archive, expected_sha256=want, on_progress=self._progress("ffmpeg"),
                                cancel=cancel, timeout=90)
        self._finish_ffmpeg(archive, f"ffmpeg/gyan-{version}", version, "gyan.dev", digest)

    def _install_ffmpeg_btbn(self, cancel: threading.Event | None) -> None:
        sums = fetch.get_text(f"{BTBN}/checksums.sha256")
        cands = []
        for line in sums.splitlines():
            m = re.match(r"([0-9a-f]{64})\s+\*?(ffmpeg-n(\d+)\.(\d+)-latest-win64-lgpl-shared-\3\.\4\.zip)$",
                         line.strip())
            if m:
                cands.append(((int(m.group(3)), int(m.group(4))), m.group(2), m.group(1)))
        if not cands:
            raise RuntimeError("BtbN no publicó builds de Windows")
        (major, minor), name, want = max(cands)
        archive = self.root / "downloads" / name
        self._set("ffmpeg", state="downloading", done=0, total=0)
        digest = fetch.download(f"{BTBN}/{name}", archive, expected_sha256=want,
                                on_progress=self._progress("ffmpeg"), cancel=cancel, timeout=90)
        self._finish_ffmpeg(archive, f"ffmpeg/btbn-{major}.{minor}-{digest[:8]}", f"{major}.{minor}", "BtbN", digest)

    # ------------------------------------------------------------------ Deno
    def _install_deno(self, cancel: threading.Event | None) -> None:
        self._set("deno", state="checking", error=None)
        if self.use_system_tools and not self._current_path("deno"):
            system = shutil.which("deno")
            if system:
                try:
                    out = self._run_check([system, "--version"])
                    m = re.search(r"deno\s+(\d+\.\d+\.\d+)", out)
                    if m and semver_at_least(m.group(1), MIN_DENO):
                        with self._lock:
                            self._entry("deno").update({"system": system, "system_version": m.group(1)})
                            self._save()
                            self.states["deno"] = ComponentState("deno", state="ready", version=m.group(1),
                                                                 source="system")
                        self._emit(force=True)
                        return
                except Exception:  # noqa: BLE001
                    pass
        tag = fetch.latest_tag(DENO_REPO)
        entry = self._entry("deno")
        if entry.get("version") == tag.lstrip("v") and self._current_path("deno"):
            self._set("deno", state="ready")
            return
        base = f"https://github.com/{DENO_REPO}/releases/download/{tag}"
        want = fetch.find_sha256(fetch.get_text(f"{base}/{DENO_ASSET}.sha256sum"))
        archive = self.root / "downloads" / f"deno-{tag}.zip"
        self._set("deno", state="downloading", done=0, total=0)
        digest = fetch.download(f"{base}/{DENO_ASSET}", archive, expected_sha256=want,
                                on_progress=self._progress("deno"), cancel=cancel, timeout=90)
        self._set("deno", state="installing")
        rel = f"deno/{tag}/deno.exe"
        dest = self.root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(archive) as z:
                member = next(n for n in z.namelist() if n.lower().endswith("deno.exe"))
                with z.open(member) as src, open(dest, "wb") as out:
                    shutil.copyfileobj(src, out, 1024 * 1024)
        finally:
            archive.unlink(missing_ok=True)
        out = self._run_check([str(dest), "--version"])
        m = re.search(r"deno\s+(\d+\.\d+\.\d+)", out)
        version = m.group(1) if m else tag.lstrip("v")
        self._commit("deno", rel, version, sha256=digest)
        log.info("Deno %s instalado", version)
