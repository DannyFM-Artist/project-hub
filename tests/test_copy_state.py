"""Per-project state: waiting > working > ready > quiet, in summary() and /api/projects."""

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
    assert state(h) == {"kind": "ready", "label": "Novedades para copiar", "detail": None}


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
    hub.set_gate("p", ph[1]["id"], "check the API")  # after the current phase: does not stop work yet
    assert state(hub)["kind"] == "working"
    hub.set_phase_status("p", ph[0]["id"], "done")  # now Two is the current phase
    assert state(hub) == {"kind": "waiting", "label": "Te espera", "detail": "check the API"}
    hub.resolve_gate("p", ph[1]["id"], "sigue", "sigue")
    assert state(hub)["kind"] == "working"


def test_waiting_needs_no_active_work(hub, clock):
    hub.create_project("p", "P", "", phases=["One"])
    hub.set_gate("p", hub.get_project("p")["phases"][0]["id"], "x" * 160)
    s = state(hub)
    assert s["kind"] == "waiting" and s["detail"] == "x" * 79 + "…"


def test_waiting_gate_beats_active_lease(hub, clock):
    mid = mk(hub)
    hub.claim_resource(f"task:{mid}", "p", "building", ttl_minutes=60)
    hub.set_gate("p", hub.get_project("p")["phases"][0]["id"], "try it on the phone")
    assert state(hub) == {"kind": "waiting", "label": "Te espera", "detail": "try it on the phone"}


def test_several_reasons_show_plus_n(hub, clock):
    hub.create_project("p", "P", "", phases=["One"])
    hub.set_gate("p", hub.get_project("p")["phases"][0]["id"], "review the plan")
    hub.post_message("user", "message", "Need a call", "b", from_project="p")
    hub.post_message("user", "message", "Another", "b", from_project="p")
    assert state(hub)["detail"] == "review the plan +2"


def test_user_message_means_waiting(hub, clock):
    hub.create_project("q", "Q", "")
    m = hub.post_message("user", "message", "Need a call", "b", from_project="q")
    assert state(hub, "q") == {"kind": "waiting", "label": "Te espera", "detail": "Need a call"}
    hub.mark_message(m["id"], "done")
    assert state(hub, "q")["kind"] != "waiting"


def test_report_after_lease_that_says_waiting(hub, clock):
    mid = mk(hub)
    hub.claim_resource(f"task:{mid}", "p", "building", ttl_minutes=600)
    clock[0] += timedelta(minutes=1)
    hub.post_message("p", "report", "Phase done", "all good", from_project="p")
    assert state(hub)["kind"] == "working"  # a report that does not say it waits
    hub.post_message("p", "report", "Build ready", "espero tu aprobación", from_project="p")
    assert state(hub)["detail"] == "Build ready"


def test_report_before_lease_does_not_count(hub, clock):
    mid = mk(hub)
    hub.post_message("p", "report", "Waiting for Danny", "b", from_project="p")
    clock[0] += timedelta(minutes=1)
    hub.claim_resource(f"task:{mid}", "p", "building", ttl_minutes=600)
    assert state(hub)["kind"] == "working"


def test_waiting_even_with_nothing_new(hub, clock):
    mid = mk(hub)
    hub.mark_message(mid, "read")
    hub.post_message("user", "message", "Q?", "b", from_project="p")
    clock[0] += timedelta(hours=1)
    hub.mark_copied("p")
    assert state(hub)["kind"] == "waiting"


def test_stagetrack_real_case(hub, clock):
    hub.create_project("p", "P", "")
    purposes = ["esperando aprobación visual", "esperando puerta", "espera presets"]
    for i, purpose in enumerate(purposes):
        mid = hub.post_message("p", "task", f"T{i}", "b")["id"]
        hub.claim_resource(f"task:{mid}", "p", purpose, ttl_minutes=1440)
    s = state(hub)
    assert s["kind"] == "waiting" and s["label"] == "Te espera"
    assert s["detail"].endswith(" +2") and s["detail"].removesuffix(" +2") in purposes


def test_api_projects_rows_carry_state_and_red_first(tmp_path, monkeypatch, clock):
    from project_hub.hub import Hub
    h = Hub(tmp_path)
    monkeypatch.setattr(web, "_hub", h)
    h.create_project("p", "P", "", phases=["One"])
    clock[0] += timedelta(minutes=1)
    h.create_project("q", "Q", "")  # most recently updated: first unless something is red
    rows = TestClient(web.app).get("/api/projects").json()
    assert [r["id"] for r in rows] == ["q", "p"] and {r["state"]["kind"] for r in rows} <= {"ready", "quiet"}
    assert all(r["state_rank"] in (2, 3) for r in rows)
    clock[0] -= timedelta(minutes=2)  # p's gate write is older than q
    h.set_gate("p", h.get_project("p")["phases"][0]["id"], "check")
    rows = TestClient(web.app).get("/api/projects").json()
    assert [(r["id"], r["state"]["kind"], r["state_rank"]) for r in rows][0] == ("p", "waiting", 0)
    summary_state = next(p for p in h.summary()["projects"] if p["id"] == "p")["state"]
    assert rows[0]["state"] == summary_state
