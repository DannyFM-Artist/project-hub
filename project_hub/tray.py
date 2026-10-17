"""Windows tray app: runs the dashboard (uvicorn in a thread of this process) behind a notification-area icon."""

import errno
import logging
import logging.handlers
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

from .hub import data_dir

HOST, PORT = "127.0.0.1", 8765
ICON = Path(__file__).parent / "static" / "icons" / "app.ico"
LABELS = ("Abrir dashboard", "Reiniciar servidor", "Abrir carpeta de datos", "Salir")
QUIT_TITLE = "¿Cerrar el dashboard de project-hub?"
QUIT_TEXT = ("Los chats y las sesiones de Claude Code seguirán funcionando, "
             "pero el dashboard dejará de estar disponible.")
POLL_WAIT = 6  # pages poll every 5 s: one poll plus margin so every open page reads the flag before the server goes


def url(port=PORT) -> str:
    return f"http://{HOST}:{port}"


def tooltip(port=PORT) -> str:
    return f"project-hub · {HOST}:{port}"


def is_running(port=PORT) -> bool:
    """A refused connection means nothing listens. A timeout does not: on this laptop a loopback handshake is
    sometimes delayed or dropped under load, so try again before deciding (a miss starts a second tray app)."""
    for _ in range(3):
        with socket.socket() as s:
            s.settimeout(3)  # Windows takes about 2 s to report a refused loopback connection
            rc = s.connect_ex((HOST, port))
        if rc == 0:
            return True
        if rc in (errno.ECONNREFUSED, getattr(errno, "WSAECONNREFUSED", errno.ECONNREFUSED)):
            return False
    return False


def setup_logging(folder=None) -> Path:
    """Rotating dashboard.log (1 MB x 3) on the root logger; uncaught exceptions go there too."""
    path = (folder or data_dir()) / "logs" / "dashboard.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    sys.excepthook = lambda *e: root.critical("uncaught exception", exc_info=e)
    threading.excepthook = lambda a: root.critical(
        "uncaught exception in thread", exc_info=(a.exc_type, a.exc_value, a.exc_traceback))
    return path


class Server:
    """uvicorn in a background thread; start/stop can repeat (restart)."""

    def __init__(self, port=PORT):
        self.port, self.server, self.thread = port, None, None

    def start(self):
        import uvicorn

        from . import web
        from .web import app
        web.STATUS["state"] = "running"
        # log_config=None: no console handlers (a windowless exe has no stdout); records reach the file handler
        self.server = uvicorn.Server(uvicorn.Config(app, host=HOST, port=self.port, log_config=None))
        self.thread = threading.Thread(target=self.server.run, daemon=True, name="uvicorn")
        self.thread.start()

    def stop(self):
        if self.server:
            self.server.should_exit = True
            self.thread.join(timeout=10)
            self.server = self.thread = None


def open_dashboard(port=PORT):
    webbrowser.open(url(port))


def open_data_folder():
    os.startfile(data_dir())


def announce(state, wait=POLL_WAIT):
    """Tell open dashboard pages what is coming; wait for their next poll only if a page polled lately."""
    from . import web
    web.STATUS["state"] = state
    if time.monotonic() - web.STATUS["polled"] < wait:
        time.sleep(wait)


def confirm_quit() -> bool:
    """Native Windows task dialog with Cerrar / Cancelar; Esc, the X and Cancelar all keep the dashboard."""
    import ctypes
    from ctypes import wintypes as w

    class Button(ctypes.Structure):
        _pack_ = 1
        _fields_ = [("id", ctypes.c_int), ("text", w.LPCWSTR)]

    class Config(ctypes.Structure):  # TASKDIALOGCONFIG, packed like commctrl.h
        _pack_ = 1
        _fields_ = [("cbSize", w.UINT), ("hwndParent", w.HWND), ("hInstance", w.HINSTANCE), ("dwFlags", ctypes.c_int),
                    ("dwCommonButtons", ctypes.c_int), ("pszWindowTitle", w.LPCWSTR), ("pszMainIcon", ctypes.c_void_p),
                    ("pszMainInstruction", w.LPCWSTR), ("pszContent", w.LPCWSTR), ("cButtons", w.UINT),
                    ("pButtons", ctypes.POINTER(Button)), ("nDefaultButton", ctypes.c_int), ("cRadioButtons", w.UINT),
                    ("pRadioButtons", ctypes.c_void_p), ("nDefaultRadioButton", ctypes.c_int),
                    ("pszVerificationText", w.LPCWSTR), ("pszExpandedInformation", w.LPCWSTR),
                    ("pszExpandedControlText", w.LPCWSTR), ("pszCollapsedControlText", w.LPCWSTR),
                    ("pszFooterIcon", ctypes.c_void_p), ("pszFooter", w.LPCWSTR), ("pfCallback", ctypes.c_void_p),
                    ("lpCallbackData", ctypes.c_void_p), ("cxWidth", w.UINT)]

    CLOSE, CANCEL = 100, 2  # 2 = IDCANCEL, also returned for Esc and the X
    buttons = (Button * 2)(Button(CLOSE, "Cerrar"), Button(CANCEL, "Cancelar"))
    cfg = Config(cbSize=ctypes.sizeof(Config), dwFlags=0x0008, pszWindowTitle="project-hub",  # TDF_ALLOW_DIALOG_CANCELLATION
                 pszMainIcon=0xFFFF, pszMainInstruction=QUIT_TITLE, pszContent=QUIT_TEXT,  # 0xFFFF = TD_WARNING_ICON
                 cButtons=2, pButtons=buttons, nDefaultButton=CANCEL)
    pressed = ctypes.c_int(0)
    if ctypes.windll.comctl32.TaskDialogIndirect(ctypes.byref(cfg), ctypes.byref(pressed), None, None) == 0:
        return pressed.value == CLOSE
    logging.warning("task dialog unavailable, using a message box")  # e.g. no common controls v6
    MB_OKCANCEL, MB_ICONWARNING, MB_DEFBUTTON2, IDOK = 0x1, 0x30, 0x100, 1
    return ctypes.windll.user32.MessageBoxW(None, QUIT_TITLE + "\n\n" + QUIT_TEXT, "project-hub",
                                            MB_OKCANCEL | MB_ICONWARNING | MB_DEFBUTTON2) == IDOK


def restart_server(server):
    announce("restarting")
    server.stop()
    server.start()


def quit_app(server, icon, confirm=None):
    if not (confirm or confirm_quit)():  # looked up at call time so tests can guard it
        return
    icon.visible = False  # immediate feedback while open pages get their last poll
    announce("stopping")
    server.stop()
    icon.stop()


def build_menu(server, port=PORT):
    import pystray as p
    return p.Menu(
        p.MenuItem(LABELS[0], lambda icon, item: open_dashboard(port), default=True),
        p.MenuItem(LABELS[1], lambda icon, item: restart_server(server)),
        p.MenuItem(LABELS[2], lambda icon, item: open_data_folder()),
        p.MenuItem(LABELS[3], lambda icon, item: quit_app(server, icon)),
    )


def launch(port=PORT) -> int:
    """Second launch only opens the browser; the first one logs, serves and shows the icon."""
    if is_running(port):
        open_dashboard(port)
        return 0
    setup_logging()
    import pystray
    from PIL import Image
    server = Server(port)
    server.start()
    pystray.Icon("project-hub", Image.open(ICON), tooltip(port), build_menu(server, port)).run()
    return 0


def main():
    sys.exit(launch())


if __name__ == "__main__":
    main()
