"""A dashboard instance for the click tests on a free port chosen by the OS, so they never collide with the real one on 8765."""
import socket
import sys


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


PORT = _free_port()  # shortcut: the port is released before uvicorn binds it again; a tiny race, fine for local test runs
BASE = f"http://127.0.0.1:{PORT}"
SERVE = [sys.executable, "-c",
         f"import uvicorn; from project_hub.web import app; uvicorn.run(app, host='127.0.0.1', port={PORT}, log_level='warning')"]
