"""Activity log, summary builder, /api/summary and get_activity."""

import json
import os
import subprocess
import sys
import textwrap
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from project_hub import hub as hub_module
from project_hub import web
from project_hub.hub import Hub, HubError

T0 = datetime(2030, 1, 1, 8, 0, tzinfo=timezone.utc)
LAST = "Revisa el proyecto {} en project-hub (get_project y read_inbox) y prepara los siguientes pasos."


@pytest.fixture
def clock(monkeypatch):
    """A fake UTC clock; _now() and summary's 'until' both follow it. clock[0] += timedelta(...) moves it."""
    now = [T0]
    monkeypatch.setattr(hub_module, "_utcnow", lambda: now[0])
    return now


@pytest.fixture
def hub(tmp_path):
    return Hub(tmp_path / "data")


def events(h):
    return h._events()


def test_event_for_each_kind(hub, clock):
    hub.create_project("demo", "Demo", "d", phases=["One"])
    p0 = hub.get_project("demo")["phases"][0]["id"]
    hub.update_project("demo", status="paused", next_step="go")
    hub.update_project("demo", next_step="go")  # no change: no event
    p1 = hub.add_phase("demo", "Two")["id"]
    hub.update_phase("demo", p1, name="Dos")
    hub.set_phase_status("demo", p0, "in_progress")
    hub.set_phase_status("demo", p0, "in_progress", notes="n")  # notes only
    hub.set_gate("demo", p1, "check")
    hub.set_gate("demo", p1, "test it")
    hub.set_gate("demo", p1, "test it")  # same reason: no event
    hub.resolve_gate("demo", p1, "sigue", "vale")
    hub.set_gate("demo", p1, "again", by="chat")
    p2 = hub.add_phase("demo", "Three")["id"]
    hub.delete_phase("demo", p2)
    item = hub.add_item("demo", "bug", "Crash")["id"]
    hub.update_item("demo", item, status="planned")
    hub.update_item("demo", item, status="done")
    hub.log_decision("demo", "Use X", "fast")
    m = hub.post_message("demo", "task", "Do it", "now", from_project="demo")
    hub.mark_message(m["id"], "read")
    hub.claim_resource("gpu", "demo", "render")  # resources are not logged
    hub.release_resource("gpu", "demo")

    got = [(e["type"], e["by"], e["text"], e.get("phase") or e.get("title")) for e in events(hub)]
    assert got == [
        ("project_created", "agent", "Demo", None),
        ("project_updated", "agent", "status active → paused; next_step updated", None),
        ("phase_added", "agent", "Two", "Two"),
        ("phase_updated", "agent", "Two → Dos", "Dos"),
        ("phase_status", "agent", "todo → in_progress", "One"),
        ("phase_updated", "agent", "notes updated", "One"),
        ("gate_set", "agent", "check", "Dos"),
        ("gate_changed", "agent", "reason updated: test it", "Dos"),
        ("gate_resolved", "chat", "resuelto vía chat (sigue): «vale»", "Dos"),
        ("gate_set", "chat", "again", "Dos"),
        ("phase_added", "agent", "Three", "Three"),
        ("phase_deleted", "agent", "Three", "Three"),
        ("item_added", "agent", "bug: Crash", "Crash"),
        ("item_updated", "agent", "status open → planned", "Crash"),
        ("item_closed", "agent", "status planned → done", "Crash"),
        ("decision", "agent", "Use X", None),
        ("message_posted", "demo", "task from demo to demo: Do it", None),
        ("message_marked", "agent", "Do it: unread → read", None),
    ]
    assert all(e["project_id"] == "demo" and e["at"] == "2030-01-01T08:00:00+00:00" for e in events(hub))
    assert ".gitignore" in os.listdir(hub.dir) and "events.jsonl" not in (hub.dir / ".gitignore").read_text()


def test_failed_change_logs_nothing(hub):
    hub.create_project("demo", "Demo", "", phases=["One"])
    p0 = hub.get_project("demo")["phases"][0]["id"]
    hub.set_gate("demo", p0, "on device")
    with pytest.raises(HubError):
        hub.set_phase_status("demo", p0, "done")
    with pytest.raises(HubError):
        hub.delete_phase("demo", p0)
    with pytest.raises(HubError):
        hub.resolve_gate("demo", p0, "vuelve a cerrar", "x")  # not continued
    assert [e["type"] for e in events(hub)] == ["project_created", "gate_set"]


def test_web_changes_are_by_dashboard(tmp_path, monkeypatch):
    h = Hub(tmp_path)
    monkeypatch.setattr(web, "_hub", h)
    c = TestClient(web.app)
    h.create_project("alpha", "Alpha", "", phases=["one"])
    p0 = h.get_project("alpha")["phases"][0]["id"]
    start = len(events(h))
    assert c.post(f"/api/projects/alpha/phases/{p0}", json={"status": "in_progress"}).status_code == 200
    item = c.post("/api/projects/alpha/items", json={"type": "idea", "title": "Idea"}).json()["id"]
    assert c.patch(f"/api/projects/alpha/items/{item}", json={"status": "discarded"}).status_code == 200
    msg = c.post("/api/messages", json={"to_project": "alpha", "kind": "task", "title": "T", "body": "b"}).json()["id"]
    assert c.patch(f"/api/messages/{msg}", json={"status": "done"}).status_code == 200
    got = [(e["type"], e["by"]) for e in events(h)[start:]]
    assert got == [("phase_status", "dashboard"),
                   ("item_added", "dashboard"), ("item_closed", "dashboard"),
                   ("message_posted", "user"), ("message_marked", "dashboard")]  # post_message: by is from_project


def test_concurrent_appends_two_processes(tmp_path):
    data = tmp_path / "data"
    Hub(data).create_project("shared", "Shared", "")
    code = textwrap.dedent("""
        import sys
        from project_hub.hub import Hub
        hub = Hub()
        for i in range(30):
            hub.add_item("shared", "idea", f"{sys.argv[1]}-{i}")
    """)
    env = dict(os.environ, PROJECT_HUB_DATA=str(data))
    procs = [subprocess.Popen([sys.executable, "-c", code, tag], env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE) for tag in ("p1", "p2")]
    for proc in procs:
        out, err = proc.communicate(timeout=180)
        assert proc.returncode == 0, err.decode()
    lines = (data / "activity" / "events.jsonl").read_text(encoding="utf-8").split("\n")
    assert lines[-1] == ""
    evs = [json.loads(line) for line in lines[:-1]]
    assert len(evs) == 61
    assert {e["title"] for e in evs[1:]} == {f"{t}-{i}" for t in ("p1", "p2") for i in range(30)}


# --- summary -----------------------------------------------------------------


def make_world(hub, clock):
    """alpha: lots happens; beta: nothing; gamma: only a waiting gate. All after the log started."""
    for pid in ("alpha", "beta", "gamma"):
        hub.create_project(pid, pid.title(), "", phases=["One", "Two", "Three"])
    ph = {pid: [p["id"] for p in hub.get_project(pid)["phases"]] for pid in ("alpha", "gamma")}
    hub.set_gate("gamma", ph["gamma"][0], "on device")
    clock[0] = T0 + timedelta(hours=10)
    hub.mark_summary_seen()  # last seen: T0+10h
    clock[0] = T0 + timedelta(hours=11)
    hub.set_phase_status("alpha", ph["alpha"][0], "done")
    hub.set_phase_status("alpha", ph["alpha"][1], "in_progress")
    hub.set_gate("alpha", ph["alpha"][1], "look at the API", by="chat")
    hub.log_decision("alpha", "Use LZ4", "fast")
    item = hub.add_item("alpha", "bug", "Crash on load")["id"]
    hub.add_item("alpha", "idea", "Dark mode")
    hub.update_item("alpha", item, status="done")
    hub.post_message("alpha", "report", "Session report", "Long body that must not be pasted", from_project="alpha")
    hub.post_message("user", "message", "Need a decision", "which one?", from_project="alpha")
    hub.post_message("alpha", "message", "API changed", "see v2", from_project="beta")
    hub.post_message("all", "task", "Broadcast", "b")  # logged under project_id "all": activity for no project
    clock[0] = T0 + timedelta(hours=12)
    return ph


def test_summary_grouping_and_content(hub, clock):
    ph = make_world(hub, clock)
    s = hub.summary()
    assert (s["since"], s["until"], s["last_seen"]) == ("2030-01-01T18:00:00+00:00", "2030-01-01T20:00:00+00:00",
                                                        "2030-01-01T18:00:00+00:00")
    assert s["log_started_at"] == "2030-01-01T08:00:00+00:00" and s["note"] is None
    # activity first (alpha, gamma by overview order: most recently updated first), then the rest
    assert [p["id"] for p in s["projects"]] == ["alpha", "gamma", "beta"]
    a, g, b = s["projects"]
    assert set(a) == {"id", "name", "status", "has_activity", "current", "action", "reports", "phase_changes", "decisions",
                      "items_opened", "items_closed", "blocked", "chat_text", "copied_at", "counts", "copy", "state"}
    assert a["current"] == {"phase": "Two", "n": 2, "total": 3, "next_step": None}
    assert a["action"]["gates"] == [{"phase_id": ph["alpha"][1], "phase": "Two", "reason": "look at the API", "set_by": "chat"}]
    assert [m["title"] for m in a["action"]["user_messages"]] == ["Need a decision"]
    assert [(r["title"], r["from_project"], r["status"]) for r in a["reports"]] == [("Session report", "alpha", "unread")]
    assert [(c["phase"], c["text"], c["by"]) for c in a["phase_changes"]] == [("One", "todo → done", "agent"),
                                                                             ("Two", "todo → in_progress", "agent")]
    assert [d["decision"] for d in a["decisions"]] == ["Use LZ4"]
    assert [i["title"] for i in a["items_opened"]] == ["Crash on load", "Dark mode"]
    assert [(i["title"], i["text"]) for i in a["items_closed"]] == [("Crash on load", "status open → done")]
    assert a["blocked"] == ["fase 'Two' en curso, espera a Danny", "mensaje de beta: API changed"]
    # gamma: nothing happened, but its gate waits for Danny, so it is not hidden
    assert g["has_activity"] and g["action"]["gates"][0]["reason"] == "on device" and not g["reports"] and g["blocked"] == []
    assert not b["has_activity"] and b["chat_text"].split("\n")[1] == "Sin actividad nueva en este periodo."
    # the message to "user" stays out of the project inboxes
    assert [m["title"] for m in hub.read_inbox("alpha")] == ["Session report", "API changed", "Broadcast"]
    assert [e["project_id"] for e in hub.activity() if e["text"].endswith("Broadcast")] == ["all"]


def test_chat_text(hub, clock):
    make_world(hub, clock)
    a = hub.summary()["projects"][0]
    lines = a["chat_text"].split("\n")
    assert lines[0].startswith("Periodo: ")
    assert lines[1:] == ["Espera a Danny: Two — look at the API", "Reports nuevos: Session report", "1 fase terminada: One",
                         "1 decisión de los agentes", LAST.format("alpha")]
    assert "Long body" not in a["chat_text"]
    for i in range(7):
        clock[0] += timedelta(minutes=1)
        hub.post_message("alpha", "report", f"R{i}", "b", from_project="alpha")
    hub.set_gate("alpha", hub.get_project("alpha")["phases"][2]["id"], "y" * 160)
    clock[0] += timedelta(minutes=1)
    hub.post_message("alpha", "report", "x" * 100, "b", from_project="alpha")
    lines = hub.summary()["projects"][0]["chat_text"].split("\n")
    assert lines[1:3] == ["Espera a Danny: Three — " + "y" * 69 + "…", "Espera a Danny: Two — look at the API"]
    # 9 reports, newest first: the 70-char shortening, then R6..R2, and 3 more
    assert lines[3] == "Reports nuevos: " + "x" * 69 + "… · R6 · R5 · R4 · R3 · R2 y 3 más"
    assert len(lines) <= 10 and lines[-1] == LAST.format("alpha")


def test_since_hours_and_default(hub, clock):
    hub.create_project("demo", "Demo", "")
    clock[0] = T0 + timedelta(hours=30)
    s = hub.summary()  # no last_seen stored: 24 h ago
    assert s["last_seen"] is None and s["since"] == "2030-01-01T14:00:00+00:00"
    assert not s["projects"][0]["has_activity"] and s["note"] is None
    assert hub.summary(hours=48)["since"] == "2029-12-31T14:00:00+00:00"
    s = hub.summary(hours=48)
    assert s["projects"][0]["has_activity"] and s["note"] == "sin registro de actividad antes de " + \
        T0.astimezone().strftime("%H:%M %d/%m")
    assert hub.summary(since="2030-01-01T07:00:00")["since"] == "2030-01-01T07:00:00+00:00"  # naive = UTC
    assert hub.summary(since=T0 + timedelta(hours=1), hours=48)["since"] == "2030-01-01T09:00:00+00:00"  # since wins
    hub.mark_summary_seen(at="2030-01-02T10:00:00+00:00")
    assert hub.summary()["since"] == "2030-01-02T10:00:00+00:00"
    for bad in ({"hours": 0}, {"hours": "3"}, {"since": "yesterday"}):
        with pytest.raises(HubError):
            hub.summary(**bad)


def test_before_the_log_existed(hub, clock):
    hub.create_project("demo", "Demo", "")
    hub.log_decision("demo", "Old decision", "r")
    hub.post_message("demo", "report", "Old report", "b", from_project="demo")
    hub.add_item("demo", "idea", "Old idea")
    hub._events_path.unlink()  # as if all of this was written before the activity log existed
    clock[0] = T0 + timedelta(hours=2)
    s = hub.summary()
    assert s["log_started_at"] is None and s["note"] == "sin registro de actividad: el registro aún no ha empezado"
    d = s["projects"][0]
    assert d["has_activity"] and [r["title"] for r in d["reports"]] == ["Old report"]
    assert [x["decision"] for x in d["decisions"]] == ["Old decision"] and [i["title"] for i in d["items_opened"]] == ["Old idea"]
    assert hub.summary(since=T0 + timedelta(hours=1))["projects"][0]["has_activity"] is False
    hub.update_project("demo", next_step="new")  # the log starts now
    s = hub.summary()
    assert s["log_started_at"] == "2030-01-01T10:00:00+00:00"
    assert s["note"] == "sin registro de actividad antes de " + (T0 + timedelta(hours=2)).astimezone().strftime("%H:%M %d/%m")
    assert hub.summary(since=T0 + timedelta(hours=2))["note"] is None


def test_summary_without_data_folder(tmp_path):
    s = Hub(tmp_path / "nothing").summary()
    assert s["projects"] == [] and s["log_started_at"] is None and "no ha empezado" in s["note"]
    assert not (tmp_path / "nothing").exists()


def test_mark_summary_seen_persists(hub, clock):
    assert hub.summary_state() == {}
    assert hub.mark_summary_seen() == {"last_seen": "2030-01-01T08:00:00+00:00"}
    assert hub.mark_summary_seen("2030-01-01T09:30:00+01:00") == {"last_seen": "2030-01-01T08:30:00+00:00"}
    assert Hub(hub.dir).summary_state() == {"last_seen": "2030-01-01T08:30:00+00:00"}
    assert json.loads((hub.dir / "summary_state.json").read_text(encoding="utf-8")) == {"last_seen": "2030-01-01T08:30:00+00:00"}
    assert not list(hub.dir.rglob("*.tmp"))
    with pytest.raises(HubError):
        hub.mark_summary_seen("nope")


def test_summary_api(tmp_path, monkeypatch, clock):
    h = Hub(tmp_path)
    monkeypatch.setattr(web, "_hub", h)
    c = TestClient(web.app)
    make_world(h, clock)
    r = c.get("/api/summary")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"since", "until", "last_seen", "log_started_at", "note", "projects"}
    assert body == json.loads(json.dumps(h.summary()))
    assert c.get("/api/summary", params={"hours": 1}).json()["since"] == "2030-01-01T19:00:00+00:00"
    assert c.get("/api/summary", params={"since": "2030-01-01T10:00:00+00:00"}).json()["since"] == "2030-01-01T10:00:00+00:00"
    assert c.get("/api/summary", params={"since": "bad"}).status_code == 400
    assert c.get("/api/summary", params={"hours": 0}).status_code == 400
    assert c.post("/api/summary/seen", json={"at": body["until"]}).json() == {"last_seen": body["until"]}
    clock[0] += timedelta(minutes=5)
    assert c.post("/api/summary/seen").json() == {"last_seen": "2030-01-01T20:05:00+00:00"}
    assert c.get("/api/summary").json()["last_seen"] == "2030-01-01T20:05:00+00:00"
    assert c.post("/api/summary/seen", json={"at": "bad"}).status_code == 400


# --- get_activity ------------------------------------------------------------


def test_get_activity_tool(hub, clock, monkeypatch):
    from project_hub import mcp_server
    monkeypatch.setattr(mcp_server, "hub", hub)
    assert mcp_server.get_activity() == "(no activity)"
    hub.create_project("demo", "Demo", "", phases=["One"])
    hub.create_project("other", "Other", "")
    p0 = hub.get_project("demo")["phases"][0]["id"]
    clock[0] = T0 + timedelta(hours=1)
    hub.set_phase_status("demo", p0, "done")
    out = mcp_server.get_activity("demo")
    assert out.split("\n") == ["2030-01-01T08:00:00+00:00 | demo | project_created | agent: Demo",
                               "2030-01-01T09:00:00+00:00 | demo | phase_status | agent: One: todo → done"]
    assert mcp_server.get_activity(since="2030-01-01T08:30:00+00:00").count("\n") == 0
    assert mcp_server.get_activity("nope").startswith("Error: unknown project")
    assert mcp_server.get_activity(since="x").startswith("Error: since must be an ISO timestamp")
    for i in range(mcp_server.ACTIVITY_CAP + 5):
        hub.add_item("other", "idea", f"i{i}")
    lines = mcp_server.get_activity("other").split("\n")
    assert lines[0] == f"(showing the last {mcp_server.ACTIVITY_CAP} of {mcp_server.ACTIVITY_CAP + 6} events; pass since to narrow)"
    assert len(lines) == mcp_server.ACTIVITY_CAP + 1 and lines[-1].endswith(f"i{mcp_server.ACTIVITY_CAP + 4}")
