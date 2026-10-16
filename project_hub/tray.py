"""Windows tray app: runs the dashboard (uvicorn in a thread of this process) behind a notification-area icon."""

import logging
import logging.handlers
import os
import socket
import sys
import threading
import webbrowser
from pathlib import Path

from .hub import data_dir

HOST, PORT = "127.0.0.1", 8765
ICON = Path(__file__).parent / "static" / "icons" / "app.ico"
LABELS = ("Abrir dashboard", "Reiniciar servidor", "Abrir carpeta de datos", "Salir")


def url(port=PORT) -> str:
    return f"http://{HOST}:{port}"


def tooltip(port=PORT) -> str:
    return f"project-hub · {HOST}:{port}"


def is_running(port=PORT) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex((HOST, port)) == 0


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

        from .web import app
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


def restart_server(server):
    server.stop()
    server.start()


def quit_app(server, icon):
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
