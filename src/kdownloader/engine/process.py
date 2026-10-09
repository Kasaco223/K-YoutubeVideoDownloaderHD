"""Procesos del motor con limpieza garantizada.

En Windows cada proceso arranca suspendido, se mete en un Job Object con KILL_ON_JOB_CLOSE y recién
entonces se reanuda: así sus hijos (FFmpeg, Deno) heredan el Job y cancelar —o que la app se cierre de
golpe— termina el árbol completo. En otros sistemas se usa un grupo de procesos.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
from collections.abc import Callable, Sequence

from ..util import log

IS_WINDOWS = sys.platform == "win32"
CREATE_NO_WINDOW = 0x08000000
CREATE_SUSPENDED = 0x00000004

if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes

    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _ntdll = ctypes.WinDLL("ntdll")

    class _IO_COUNTERS(ctypes.Structure):
        _fields_ = [(n, ctypes.c_ulonglong) for n in (
            "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
            "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

    class _BASIC_LIMIT(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class _EXTENDED_LIMIT(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", _BASIC_LIMIT),
            ("IoInfo", _IO_COUNTERS),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    _k32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    _k32.CreateJobObjectW.restype = wintypes.HANDLE
    _k32.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    _k32.SetInformationJobObject.restype = wintypes.BOOL
    _k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    _k32.AssignProcessToJobObject.restype = wintypes.BOOL
    _k32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    _k32.TerminateJobObject.restype = wintypes.BOOL
    _k32.CloseHandle.argtypes = [wintypes.HANDLE]
    _k32.CloseHandle.restype = wintypes.BOOL
    _ntdll.NtResumeProcess.argtypes = [wintypes.HANDLE]
    _ntdll.NtResumeProcess.restype = ctypes.c_long

    _JOB_EXTENDED_LIMIT_INFORMATION = 9
    _KILL_ON_JOB_CLOSE = 0x2000

    def _create_job() -> int | None:
        job = _k32.CreateJobObjectW(None, None)
        if not job:
            return None
        info = _EXTENDED_LIMIT()
        info.BasicLimitInformation.LimitFlags = _KILL_ON_JOB_CLOSE
        if not _k32.SetInformationJobObject(job, _JOB_EXTENDED_LIMIT_INFORMATION, ctypes.byref(info),
                                            ctypes.sizeof(info)):
            _k32.CloseHandle(job)
            return None
        return job


def clean_child_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    """Entorno para hijos: UTF-8 y sin rutas temporales de empaquetadores en el PATH."""
    env = dict(os.environ)
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        env["PATH"] = os.pathsep.join(p for p in env.get("PATH", "").split(os.pathsep) if meipass not in p)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)
    if extra:
        env.update(extra)
    return env


class ManagedProcess:
    """Proceso con stdout/stderr leídos línea a línea en hilos propios."""

    def __init__(
        self,
        args: Sequence[str],
        *,
        on_stdout: Callable[[str], None] | None = None,
        on_stderr: Callable[[str], None] | None = None,
        env: dict[str, str] | None = None,
        cwd: str | None = None,
    ):
        self.args = list(args)
        self._job = None
        self._killed = threading.Event()
        flags = (CREATE_NO_WINDOW | CREATE_SUSPENDED) if IS_WINDOWS else 0
        self.proc = subprocess.Popen(
            self.args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env if env is not None else clean_child_env(),
            cwd=cwd,
            creationflags=flags,
            start_new_session=not IS_WINDOWS,
        )
        if IS_WINDOWS:
            self._attach_job_and_resume()
        self._readers = [
            threading.Thread(target=self._pump, args=(self.proc.stdout, on_stdout), daemon=True, name="kd-out"),
            threading.Thread(target=self._pump, args=(self.proc.stderr, on_stderr), daemon=True, name="kd-err"),
        ]
        for t in self._readers:
            t.start()

    def _attach_job_and_resume(self) -> None:
        handle = int(self.proc._handle)  # type: ignore[attr-defined]
        try:
            job = _create_job()
            if job and _k32.AssignProcessToJobObject(job, handle):
                self._job = job
            elif job:
                _k32.CloseHandle(job)
                log.warning("No se pudo asignar el proceso al Job (%s); se usará taskkill", ctypes.get_last_error())
        finally:
            status = _ntdll.NtResumeProcess(handle)  # siempre se reanuda, aunque el Job falle
            if status != 0:
                log.error("NtResumeProcess devolvió %#x", status & 0xFFFFFFFF)

    @staticmethod
    def _pump(stream, callback: Callable[[str], None] | None) -> None:
        try:
            for raw in iter(stream.readline, b""):
                if callback is not None:
                    try:
                        callback(raw.decode("utf-8", "replace").rstrip("\r\n"))
                    except Exception:  # noqa: BLE001 - un callback defectuoso no debe matar la lectura
                        log.exception("Error procesando salida del motor")
        finally:
            stream.close()

    @property
    def pid(self) -> int:
        return self.proc.pid

    @property
    def killed(self) -> bool:
        return self._killed.is_set()

    def wait(self, timeout: float | None = None) -> int:
        rc = self.proc.wait(timeout=timeout)
        for t in self._readers:
            t.join(timeout=5)
        self._close_job()
        return rc

    def kill(self) -> None:
        """Termina el proceso y todos sus hijos."""
        self._killed.set()
        if self.proc.poll() is not None:
            return
        if IS_WINDOWS:
            if self._job:
                _k32.TerminateJobObject(self._job, 1)
            else:
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(self.proc.pid)],
                               capture_output=True, creationflags=CREATE_NO_WINDOW, check=False)
        else:
            try:
                os.killpg(self.proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    def _close_job(self) -> None:
        if IS_WINDOWS and self._job:
            _k32.CloseHandle(self._job)
            self._job = None

    def __del__(self):  # pragma: no cover - limpieza de último recurso
        try:
            self._close_job()
        except Exception:  # noqa: BLE001
            pass


def run_capture(args: Sequence[str], timeout: float = 30, env: dict[str, str] | None = None) -> tuple[int, str, str]:
    """Ejecuta un comando corto (p. ej. `--version`) y devuelve (código, stdout, stderr)."""
    out: list[str] = []
    err: list[str] = []
    p = ManagedProcess(args, on_stdout=out.append, on_stderr=err.append, env=env)
    try:
        rc = p.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        p.wait(timeout=10)
        raise
    return rc, "\n".join(out), "\n".join(err)
