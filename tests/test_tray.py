import http.server
import socket
import threading

import pytest

from project_hub import tray


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class FakeServer:
    def __init__(self):
        self.calls = []

    def start(self):
        self.calls.append("start")

    def stop(self):
        self.calls.append("stop")


class FakeIcon:
    stopped = False

    def stop(self):
        self.stopped = True


@pytest.fixture
def opened(monkeypatch):
    urls = []
    monkeypatch.setattr(tray.webbrowser, "open", urls.append)
    return urls


def test_free_port_is_not_running():
    assert not tray.is_running(free_port())


def test_second_launch_only_opens_browser(opened):
    srv = http.server.HTTPServer(("127.0.0.1", 0), http.server.BaseHTTPRequestHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_address[1]
    try:
        assert tray.is_running(port)
        assert tray.launch(port) == 0
    finally:
        srv.shutdown()
        srv.server_close()
    assert opened == [f"http://127.0.0.1:{port}"]


def test_open_dashboard(opened):
    tray.open_dashboard()
    assert opened == ["http://127.0.0.1:8765"]


def test_open_data_folder(monkeypatch, tmp_path):
    monkeypatch.setenv("PROJECT_HUB_DATA", str(tmp_path))
    got = []
    monkeypatch.setattr(tray.os, "startfile", got.append, raising=False)
    tray.open_data_folder()
    assert got == [tmp_path.resolve()]


def test_restart_and_quit():
    s, i = FakeServer(), FakeIcon()
    tray.restart_server(s)
    assert s.calls == ["stop", "start"]
    tray.quit_app(s, i)
    assert s.calls[-1] == "stop" and i.stopped


def test_log_file_created_in_data_folder(tmp_path):
    import logging
    root = logging.getLogger()
    saved = root.handlers[:], root.level
    try:
        path = tray.setup_logging(tmp_path)
        logging.getLogger("uvicorn.error").info("hello")
        assert path == tmp_path / "logs" / "dashboard.log"
        assert "hello" in path.read_text(encoding="utf-8")
    finally:
        for h in root.handlers:
            h.close()
        root.handlers, root.level = saved


def test_tooltip():
    assert tray.tooltip() == "project-hub · 127.0.0.1:8765"


def test_menu_labels_and_order():
    pytest.importorskip("pystray")
    menu = tray.build_menu(FakeServer())
    assert tuple(i.text for i in menu.items) == (
        "Abrir dashboard", "Reiniciar servidor", "Abrir carpeta de datos", "Salir")
    assert menu.items[0].default


def test_real_server_start_stop_restart():
    port = free_port()
    s = tray.Server(port)
    s.start()
    try:
        for _ in range(100):
            if tray.is_running(port):
                break
            threading.Event().wait(0.1)
        assert tray.is_running(port)
        tray.restart_server(s)
        for _ in range(100):
            if tray.is_running(port):
                break
            threading.Event().wait(0.1)
        assert tray.is_running(port)
    finally:
        s.stop()
    assert not tray.is_running(port)
