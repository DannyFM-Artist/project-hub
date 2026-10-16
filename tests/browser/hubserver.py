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


def serve(data):
    """Start the dashboard on PORT against the data folder and wait until it answers; fail loudly instead of
    letting the first page load time out (a slow start used to show up as ERR_CONNECTION_TIMED_OUT)."""
    import os, subprocess, urllib.request
    srv = subprocess.Popen(SERVE, env=dict(os.environ, PROJECT_HUB_DATA=str(data)), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    end = time.time() + 30
    while time.time() < end:
        try:
            urllib.request.urlopen(BASE + "/api/projects", timeout=5); return srv
        except Exception:
            if srv.poll() is not None:
                break
            time.sleep(.2)
    srv.terminate()
    raise SystemExit(f"dashboard did not start on port {PORT}")


def until(fn, timeout=6.0):
    """Poll fn() until it is truthy or timeout seconds pass; returns the last value."""
    end = time.time() + timeout
    while True:
        v = fn()
        if v or time.time() > end:
            return v
        time.sleep(.1)
