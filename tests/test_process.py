"""engine.process: procesos con lectura por líneas en UTF-8 y cancelación del árbol completo (Job Object)."""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
import threading
import time
from pathlib import Path

import pytest

from kdownloader.engine import process
from kdownloader.engine.process import ManagedProcess, clean_child_env, run_capture

IS_WINDOWS = sys.platform == "win32"


def pid_alive(pid: int) -> bool:
    """¿Sigue vivo el proceso? Sin psutil; en Windows NO se usa os.kill(pid, 0) (eso manda Ctrl+C)."""
    if IS_WINDOWS:
        import ctypes
        from ctypes import wintypes

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k32.OpenProcess.restype = wintypes.HANDLE
        k32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        k32.GetExitCodeProcess.restype = wintypes.BOOL
        k32.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False  # ya no existe
        try:
            code = wintypes.DWORD()
            if not k32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return code.value == 259  # STILL_ACTIVE
        finally:
            k32.CloseHandle(handle)
    import os

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def wait_until(predicate, timeout: float = 15.0, interval: float = 0.05) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()


@pytest.fixture
def tree_script(tmp_path: Path) -> Path:
    """Hijo que lanza un nieto (como yt-dlp → FFmpeg) y espera; imprime los PIDs reales."""
    script = tmp_path / "padre ñandú.py"  # ruta con espacio y ñ, como la carpeta de un usuario real
    script.write_text(textwrap.dedent("""
        import os, subprocess, sys, time
        grandchild = subprocess.Popen(
            [sys.executable, "-c", "import os, time; print(os.getpid(), flush=True); time.sleep(60)"],
            stdout=subprocess.PIPE)
        real_pid = grandchild.stdout.readline().decode().strip()
        print("CHILD", os.getpid(), flush=True)
        print("GRANDCHILD", grandchild.pid, real_pid, flush=True)
        print("ñandú ｜ 日本語", flush=True)
        sys.stderr.write("err: Zenón\\n"); sys.stderr.flush()
        time.sleep(60)
    """), encoding="utf-8")
    return script


def test_kill_terminates_child_and_grandchild(tree_script: Path, python_exe: Path):
    out: list[str] = []
    err: list[str] = []
    ready = threading.Event()

    def on_out(line: str) -> None:
        out.append(line)
        if line.startswith("ñandú"):
            ready.set()

    p = ManagedProcess([str(python_exe), str(tree_script)], on_stdout=on_out, on_stderr=err.append)
    assert ready.wait(30), f"el hijo no arrancó: {out} {err}"
    child_pid = int(next(ln for ln in out if ln.startswith("CHILD")).split()[1])
    _, launcher_pid, grandchild_pid = next(ln for ln in out if ln.startswith("GRANDCHILD")).split()
    pids = {p.pid, child_pid, int(launcher_pid), int(grandchild_pid)}
    assert all(pid_alive(pid) for pid in pids)
    if IS_WINDOWS:
        assert p._job is not None, "el proceso debe quedar dentro de un Job Object"

    t0 = time.monotonic()
    p.kill()
    rc = p.wait(timeout=20)
    assert rc != 0
    assert p.killed
    assert wait_until(lambda: not any(pid_alive(pid) for pid in pids)), \
        [pid for pid in pids if pid_alive(pid)]
    assert time.monotonic() - t0 < 15
    assert "ñandú ｜ 日本語" in out  # el callback recibe texto UTF-8 ya decodificado
    assert "err: Zenón" in err
    assert all(not ln.endswith(("\r", "\n")) for ln in out)


def test_kill_after_exit_is_harmless(python_exe: Path):
    p = ManagedProcess([str(python_exe), "-c", "print('hola')"])
    assert p.wait(timeout=30) == 0
    p.kill()  # no lanza aunque ya terminó
    assert p.killed


def test_job_close_on_wait(python_exe: Path):
    p = ManagedProcess([str(python_exe), "-c", "pass"])
    p.wait(timeout=30)
    assert p._job is None  # el handle del Job se cierra al terminar


def test_line_callbacks_utf8_and_separate_streams(python_exe: Path, tmp_path: Path):
    target = "C:\\Videos\\Ñandú ｜ Zenón.mp4"
    script = tmp_path / "salida.py"
    script.write_text(
        "import json, sys\n"
        "print('línea 1: ñandú')\n"
        f"print('KDL|file|' + json.dumps({target!r}))\n"
        "sys.stderr.write('ERROR: algo ’ curvo\\r\\n')\n"
        "print('sin salto final', end='')\n",
        encoding="utf-8",
    )
    out: list[str] = []
    err: list[str] = []
    p = ManagedProcess([str(python_exe), str(script)], on_stdout=out.append, on_stderr=err.append)
    assert p.wait(timeout=30) == 0, err
    assert out == ["línea 1: ñandú", "KDL|file|" + json.dumps(target), "sin salto final"]
    assert err == ["ERROR: algo ’ curvo"]  # sin el salto de línea final


def test_utf8_with_isolated_mode_like_ytdlp(python_exe: Path):
    # yt-dlp corre con `-I -X utf8`: -I ignora PYTHONIOENCODING, así que -X utf8 es lo que garantiza UTF-8.
    rc, out, _ = run_capture([str(python_exe), "-I", "-X", "utf8", "-c", "print('Soy el Ñandú ｜ Zenón')"])
    assert rc == 0 and out == "Soy el Ñandú ｜ Zenón"


def test_invalid_utf8_is_replaced_not_fatal(python_exe: Path):
    code = "import sys; sys.stdout.buffer.write(b'caf\\xe9 ok\\n'); sys.stdout.flush()"
    rc, out, _ = run_capture([str(python_exe), "-c", code])
    assert rc == 0 and out == "caf\ufffd ok"


def test_faulty_callback_does_not_stop_reading(python_exe: Path):
    seen: list[str] = []

    def cb(line: str) -> None:
        seen.append(line)
        if line == "boom":
            raise RuntimeError("callback defectuoso")

    p = ManagedProcess([str(python_exe), "-c", "print('a'); print('boom'); print('b')"], on_stdout=cb)
    assert p.wait(timeout=30) == 0
    assert seen == ["a", "boom", "b"]


def test_run_capture_returns_output(python_exe: Path):
    rc, out, err = run_capture([str(python_exe), "-c",
                                "import sys; print('2026.09.27.232945'); print('x', file=sys.stderr); sys.exit(3)"])
    assert (rc, out, err) == (3, "2026.09.27.232945", "x")


def test_run_capture_multiline(python_exe: Path):
    rc, out, _ = run_capture([str(python_exe), "-c", "print('a'); print('b')"])
    assert rc == 0 and out == "a\nb"


def test_run_capture_timeout_kills(python_exe: Path):
    t0 = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        run_capture([str(python_exe), "-c", "import time; time.sleep(60)"], timeout=1)
    assert time.monotonic() - t0 < 20


def test_nonexistent_executable_raises_oserror(tmp_path: Path):
    with pytest.raises(OSError):
        ManagedProcess([str(tmp_path / "no-existe.exe"), "--version"])
    with pytest.raises(OSError):
        run_capture([str(tmp_path / "tampoco.exe")])


def test_stdin_is_closed(python_exe: Path):
    # Sin consola: un input() inesperado no debe colgar la descarga.
    rc, _, err = run_capture([str(python_exe), "-c", "input()"], timeout=30)
    assert rc != 0 and "EOFError" in err


def test_env_and_cwd(python_exe: Path, tmp_path: Path):
    env = clean_child_env({"KD_TEST_VALUE": "ñ-ok"})
    out: list[str] = []
    p = ManagedProcess([str(python_exe), "-c", "import os; print(os.environ['KD_TEST_VALUE']); print(os.getcwd())"],
                       on_stdout=out.append, env=env, cwd=str(tmp_path))
    assert p.wait(timeout=30) == 0
    assert out[0] == "ñ-ok"
    assert Path(out[1]).resolve() == tmp_path.resolve()


def test_clean_child_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PYTHONHOME", "C:\\bad")
    monkeypatch.setenv("PYTHONPATH", "C:\\bad")
    monkeypatch.setenv("PATH", "C:\\a;C:\\Temp\\_MEI12345;C:\\b")
    monkeypatch.setattr(process.sys, "_MEIPASS", "C:\\Temp\\_MEI12345", raising=False)
    env = clean_child_env({"EXTRA": "1"})
    assert env["PYTHONIOENCODING"] == "utf-8" and env["PYTHONUTF8"] == "1"
    assert "PYTHONHOME" not in env and "PYTHONPATH" not in env
    assert "_MEI12345" not in env["PATH"]
    assert env["EXTRA"] == "1"


@pytest.mark.skipif(not IS_WINDOWS, reason="taskkill solo existe en Windows")
def test_kill_without_job_falls_back_to_taskkill(tree_script: Path, python_exe: Path,
                                                 monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(process, "_create_job", lambda: None)  # como si el Job no se pudiera crear
    out: list[str] = []
    ready = threading.Event()

    def on_out(line: str) -> None:
        out.append(line)
        if line.startswith("ñandú"):
            ready.set()

    p = ManagedProcess([str(python_exe), str(tree_script)], on_stdout=on_out)
    assert ready.wait(30)
    assert p._job is None
    grandchild = int(next(ln for ln in out if ln.startswith("GRANDCHILD")).split()[2])
    p.kill()
    p.wait(timeout=20)
    assert wait_until(lambda: not pid_alive(grandchild))
