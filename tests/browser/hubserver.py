"""A dashboard instance for the click tests on a free port chosen by the OS, so they never collide with the real one on 8765."""
import socket
import sys
import time


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


PORT = _free_port()  # placeholder until serve() runs; shutdown_check.py uses it for its own in-process server
BASE = f"http://127.0.0.1:{PORT}"
# the server binds its port itself (0 = any free one) and prints it: no gap in which another process can take it
SERVE = [sys.executable, "-c",
         "import socket, sys, uvicorn; from project_hub.web import app; s = socket.socket(); "
         "s.bind(('127.0.0.1', int(sys.argv[1]))); print(s.getsockname()[1], flush=True); "
         "uvicorn.Server(uvicorn.Config(app, log_level='warning')).run(sockets=[s])"]
_served = False


def serve(data):
    """Start the dashboard against the data folder and wait until it answers. The first call takes any free port
    and updates PORT and BASE here and in the running check script; later calls (a restart) reuse that port.
    A server that never answers is replaced: on this laptop a loopback handshake is sometimes dropped under load,
    which can leave a new event loop stuck before it serves anything."""
    for _ in range(3):
        srv = _start(data)
        if srv:
            return srv
    raise SystemExit(f"dashboard did not start on port {PORT} (3 tries)")


def _start(data):
    global PORT, BASE, _served
    import os, subprocess, urllib.request
    srv = subprocess.Popen(SERVE + [str(PORT if _served else 0)], env=dict(os.environ, PROJECT_HUB_DATA=str(data)),
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    line = srv.stdout.readline()  # the bound port, or "" if the process died first
    if not line.strip().isdigit():
        srv.terminate(); srv.wait()
        return None
    PORT, _served = int(line), True
    BASE = f"http://127.0.0.1:{PORT}"
    main = sys.modules["__main__"]  # the checks did "from hubserver import BASE, PORT" before calling serve()
    for name in ("PORT", "BASE"):
        if hasattr(main, name):
            setattr(main, name, globals()[name])
    end = time.time() + 20
    while time.time() < end and srv.poll() is None:
        try:
            urllib.request.urlopen(BASE + "/api/projects", timeout=5); return srv
        except Exception:
            time.sleep(.2)
    srv.terminate(); srv.wait()
    return None


def until(fn, timeout=6.0):
    """Poll fn() until it is truthy or timeout seconds pass; returns the last value."""
    end = time.time() + timeout
    while True:
        v = fn()
        if v or time.time() > end:
            return v
        time.sleep(.1)
