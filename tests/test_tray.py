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
    visible = True

    def stop(self):
        self.stopped = True


@pytest.fixture
def status(monkeypatch):
    from project_hub import web
    monkeypatch.setattr(web, "STATUS", {"state": "running", "polled": 0.0})
    return web.STATUS


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


def test_restart_and_quit(status):
    s, i = FakeServer(), FakeIcon()
    tray.restart_server(s)
    assert s.calls == ["stop", "start"] and status["state"] == "restarting"  # the real Server.start sets it back
    tray.quit_app(s, i, confirm=lambda: True)
    assert s.calls[-1] == "stop" and i.stopped and not i.visible and status["state"] == "stopping"


def test_tests_never_reach_the_real_dialog(status):
    with pytest.raises(AssertionError, match="real tray quit dialog"):
        tray.quit_app(FakeServer(), FakeIcon())


def test_quit_cancelled_keeps_everything(status):
    s, i = FakeServer(), FakeIcon()
    tray.quit_app(s, i, confirm=lambda: False)
    assert s.calls == [] and not i.stopped and i.visible and status["state"] == "running"


def test_status_endpoint_reports_the_flag_and_poll_time(status):
    from fastapi.testclient import TestClient
    from project_hub import web
    c = TestClient(web.app)
    assert c.get("/api/status").json() == {"state": "running"} and status["polled"] > 0
    status["state"] = "stopping"
    assert c.get("/api/status").json() == {"state": "stopping"}


def test_announce_waits_only_when_a_page_polled_lately(status, monkeypatch):
    slept = []
    monkeypatch.setattr(tray.time, "sleep", slept.append)
    tray.announce("stopping")
    assert slept == [] and status["state"] == "stopping"  # no open page: quit at once
    status["polled"] = tray.time.monotonic()
    tray.announce("restarting")
    assert slept == [tray.POLL_WAIT] and status["state"] == "restarting"


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
        from project_hub import web
        assert web.STATUS["state"] == "running"  # the restarted server serves "running" again
        for _ in range(100):
            if tray.is_running(port):
                break
            threading.Event().wait(0.1)
        assert tray.is_running(port)
    finally:
        s.stop()
    assert not tray.is_running(port)
