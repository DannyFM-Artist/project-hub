"""A dashboard instance for the click tests on a free port chosen by the OS, so they never collide with the real one on 8765."""
import socket
import sys
import time


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


PORT = _free_port()  # shortcut: the port is released before uvicorn binds it again; a tiny race, fine for local test runs
BASE = f"http://127.0.0.1:{PORT}"
SERVE = [sys.executable, "-c",
         f"import uvicorn; from project_hub.web import app; uvicorn.run(app, host='127.0.0.1', port={PORT}, log_level='warning')"]

# the app icon files ship from another branch; until they are merged, only their exact 404s are not console errors
ICONS = ("/favicon.svg", "/icons/icon-32.png", "/icons/apple-touch-icon.png", "/manifest.webmanifest")


def real_error(m):
    """A console message that counts as an error: any error except the 404 of one of the app icon files."""
    url = (m.location or {}).get("url", "").replace(BASE, "")
    return m.type == "error" and not ("404" in m.text and url in ICONS)


def until(fn, timeout=6.0):
    """Poll fn() until it is truthy or timeout seconds pass; returns the last value."""
    end = time.time() + timeout
    while True:
        v = fn()
        if v or time.time() > end:
            return v
        time.sleep(.1)
