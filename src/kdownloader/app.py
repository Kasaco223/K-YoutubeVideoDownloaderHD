"""Punto de entrada: crea la ventana pywebview, conecta los servicios y gestiona el ciclo de vida."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from . import __version__, paths, winintegration
from .constants import APP_NAME
from .instance import InstanceGuard, url_from_argv
from .util import log, setup_logging


def _icon_path() -> str | None:
    root = paths.install_root()
    candidates = [root / "K-Downloader.ico"] if root else []
    candidates.append(paths.package_dir().parent.parent / "packaging" / "assets" / "K-Downloader.ico")
    for c in candidates:
        if c.exists():
            return str(c)
    return None


def _bring_to_front(window) -> None:
    try:
        window.restore()
        from System import Func, Object  # type: ignore[import-not-found]

        def activate():
            window.native.Activate()
            return None

        window.native.Invoke(Func[Object](activate))
    except Exception:  # noqa: BLE001
        pass


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    debug = "--debug" in argv or os.environ.get("KD_DEBUG") == "1"
    setup_logging(paths.logs_dir(), debug)
    log.info("K-Downloader %s (Python %s) desde %s", __version__, sys.version.split()[0], sys.executable)
    winintegration.set_app_id()

    guard = InstanceGuard(paths.data_dir())
    if not guard.acquire():
        if "--after-update" in argv:
            if not guard.wait_for_release():
                log.warning("La instancia anterior no se cerró a tiempo")
                return 1
        else:
            guard.forward(argv)
            return 0

    import webview  # import tardío: la segunda instancia no necesita cargar WebView2

    from .bridge import Api
    from .services import Services

    services = Services()
    api = Api(services)
    window = webview.create_window(
        APP_NAME, url=str(paths.ui_dir() / "index.html"), js_api=api, width=1000, height=680,
        min_size=(760, 540), background_color="#101218", text_select=False,
    )
    services.window = window
    services.pump.attach(window)

    def on_closing():
        active = services.downloads.active_count()
        if services.force_quit or active == 0:
            return True
        # No se llama a JS desde aquí (hilo de la UI): el aviso sale por el hilo del pump.
        services.pump.emit({"type": "confirm_close", "active": active}, "confirm_close")
        return False

    def on_shown():
        try:
            services.hwnd = int(window.native.Handle.ToInt64())
        except Exception:  # noqa: BLE001
            services.hwnd = 0

    def on_message(msg: dict) -> None:
        url = url_from_argv([str(a) for a in msg.get("argv") or []])
        if url:
            services.pump.emit({"type": "incoming_url", "url": url}, "incoming_url")
        _bring_to_front(window)

    window.events.closing += on_closing
    window.events.shown += on_shown
    guard.serve(on_message)

    incoming = url_from_argv(argv)
    if incoming:
        services.pump.emit({"type": "incoming_url", "url": incoming}, "incoming_url")

    webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True
    webview.settings["ALLOW_DOWNLOADS"] = False
    try:
        webview.start(services.start_background, gui="edgechromium", debug=debug, private_mode=True,
                      icon=_icon_path())
    finally:
        services.shutdown()
        guard.close()
        log.info("K-Downloader cerrado")
    return 0


def selftest() -> int:
    """Comprobación rápida para el instalador y la CI: dependencias, UI y motor importables."""
    problems: list[str] = []
    try:
        import webview  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        problems.append(f"pywebview: {exc!r}")
    if sys.platform == "win32":
        try:
            import clr_loader  # noqa: F401
        except Exception as exc:  # noqa: BLE001
            problems.append(f"pythonnet: {exc!r}")
    index = paths.ui_dir() / "index.html"
    if not index.exists():
        problems.append(f"Falta la interfaz: {index}")
    try:
        from .engine import errors, presets, ytdlp  # noqa: F401

        errors.catalog()
        presets.build_args(presets.Choice("recommended"), is_youtube=True)
    except Exception as exc:  # noqa: BLE001
        problems.append(f"motor: {exc!r}")
    out = sys.stdout
    if out is not None:
        if problems:
            out.write("SELFTEST FAIL\n" + "\n".join(problems) + "\n")
        else:
            out.write(f"SELFTEST OK K-Downloader {__version__} · Python {sys.version.split()[0]} · "
                      f"{Path(sys.executable).name}\n")
    return 1 if problems else 0
