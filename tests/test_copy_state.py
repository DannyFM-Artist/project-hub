"""Per-project copy state: working / waiting / ready / quiet, in summary() and /api/projects."""

from datetime import timedelta

from fastapi.testclient import TestClient

from project_hub import web
from test_activity import T0, clock, hub  # noqa: F401  (fixtures)


def state(h, pid="p"):
    return next(p for p in h.summary()["projects"] if p["id"] == pid)["state"]


def mk(h):
    h.create_project("p", "P", "", phases=["One", "Two"])
    return h.post_message("p", "task", "Do the thing", "b")["id"]


def test_quiet_and_ready(hub, clock):
    h = hub
    h.create_project("p", "P", "")
    clock[0] += timedelta(hours=1)
    h.mark_copied("p")
    assert state(h) == {"kind": "quiet", "label": "Sin novedades", "detail": None}
    clock[0] += timedelta(minutes=1)
    h.log_decision("p", "d", "r")
    assert state(h) == {"kind": "ready", "label": "Listo para copiar", "detail": None}


def test_lease_means_working(hub, clock):
    mid = mk(hub)
    hub.claim_resource(f"task:{mid}", "p", "building", ttl_minutes=60)
    assert state(hub) == {"kind": "working", "label": "Trabajando", "detail": "Trabajando en: Do the thing"}
    clock[0] += timedelta(hours=2)  # lease expired
    assert state(hub)["kind"] != "working"


def test_read_task_means_working(hub, clock):
    mid = mk(hub)
    hub.mark_message(mid, "read")
    assert state(hub)["kind"] == "working"
    hub.mark_message(mid, "done")
    assert state(hub)["kind"] != "working"


def test_waiting_gate(hub, clock):
    mid = mk(hub)
    hub.mark_message(mid, "read")
    ph = hub.get_project("p")["phases"]
    hub.set_gate("p", ph[1]["id"], "review", "r")  # not current, not in progress: still working
    assert state(hub)["kind"] == "working"
    hub.set_phase_status("p", ph[0]["id"], "done")  # now Two is the current phase
    assert state(hub) == {"kind": "waiting", "label": "Listo para copiar", "detail": "Esperando a Danny: Two"}


def test_user_message_and_report_mean_waiting(hub, clock):
    mid = mk(hub)
    hub.mark_message(mid, "read")
    clock[0] += timedelta(minutes=1)
    hub.post_message("p", "report", "Done phase", "b", from_project="p")
    assert state(hub)["detail"] == "Esperando a Danny: Done phase"
    hub.create_project("q", "Q", "")
    qid = hub.post_message("q", "task", "T", "b")["id"]
    hub.mark_message(qid, "read")
    assert state(hub, "q")["kind"] == "working"
    hub.post_message("user", "message", "Need a call", "b", from_project="q")
    assert state(hub, "q")["detail"] == "Esperando a Danny: Need a call"


def test_waiting_even_with_nothing_new(hub, clock):
    mid = mk(hub)
    hub.mark_message(mid, "read")
    hub.post_message("user", "message", "Q?", "b", from_project="p")
    clock[0] += timedelta(hours=1)
    hub.mark_copied("p")
    assert state(hub)["kind"] == "waiting"


def test_stagetrack_real_case(hub, clock):
    hub.create_project("p", "P", "")
    for i, purpose in enumerate(["esperando aprobación visual", "esperando puerta", "espera presets"]):
        mid = hub.post_message("p", "task", f"T{i}", "b")["id"]
        hub.claim_resource(f"task:{mid}", "p", purpose, ttl_minutes=1440)
    s = state(hub)
    assert s["kind"] == "waiting" and s["detail"].removeprefix("Esperando a Danny: ") in ("esperando aprobación visual", "esperando puerta", "espera presets")


def test_api_projects_rows_carry_state(tmp_path, monkeypatch, clock):
    from project_hub.hub import Hub
    h = Hub(tmp_path)
    monkeypatch.setattr(web, "_hub", h)
    h.create_project("p", "P", "")
    rows = TestClient(web.app).get("/api/projects").json()
    assert rows[0]["state"]["kind"] in ("ready", "quiet")
