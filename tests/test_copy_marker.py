"""Per-project "copied for the chat" marker: Hub.mark_copied, summary copy/counts, /api/summary/copied."""

import json
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from project_hub import web
from project_hub.hub import Hub, HubError
from test_activity import LAST, T0, clock, hub, make_world  # noqa: F401  (fixtures)


def proj(h, pid="alpha", **kw):
    return next(p for p in h.summary(**kw)["projects"] if p["id"] == pid)


def test_marker_persists_and_setters_keep_each_other(hub, clock):
    hub.create_project("demo", "Demo", "")
    assert hub.mark_copied("demo") == {"project_id": "demo", "copied_at": "2030-01-01T08:00:00+00:00"}
    hub.mark_summary_seen("2030-01-01T09:00:00+00:00")
    assert hub.summary_state() == {"last_seen": "2030-01-01T09:00:00+00:00", "copied": {"demo": "2030-01-01T08:00:00+00:00"}}
    hub.create_project("two", "Two", "")
    hub.mark_copied("two", "2030-01-01T10:30:00+01:00")
    state = json.loads((hub.dir / "summary_state.json").read_text(encoding="utf-8"))
    assert state == {"last_seen": "2030-01-01T09:00:00+00:00",
                     "copied": {"demo": "2030-01-01T08:00:00+00:00", "two": "2030-01-01T09:30:00+00:00"}}
    assert Hub(hub.dir).summary_state() == state
    assert not list(hub.dir.rglob("*.tmp"))
    n = len(hub._events())
    hub.mark_copied("demo")
    assert len(hub._events()) == n  # view state: not logged
    with pytest.raises(HubError):
        hub.mark_copied("nope")
    with pytest.raises(HubError):
        hub.mark_copied("demo", "bad")


def test_copy_before_any_copy(hub, clock):
    make_world(hub, clock)
    a, g, b = (proj(hub, x) for x in ("alpha", "gamma", "beta"))
    assert a["copied_at"] is None and a["copy"]["since"] == hub.summary()["since"]
    # reports 1, decisions 1, items opened 2, closed 1, phase changes 2, gate 1 (set in window and waiting: one phase)
    assert a["copy"]["new"] == 8
    assert a["copy"]["chat_text"] == a["chat_text"] and a["copy"]["chat_text"].endswith(LAST.format("alpha"))
    # gamma: its gate was set before the window but waits now
    assert g["copy"]["new"] == 1 and "Gate esperando a Danny: One (prueba manual)" in g["copy"]["chat_text"]
    assert b["copy"] == {"since": a["copy"]["since"], "new": 0, "chat_text": None}


def test_after_copy_only_new_things(hub, clock):
    make_world(hub, clock)
    until = hub.summary()["until"]
    hub.mark_copied("alpha", until)
    clock[0] += timedelta(minutes=5)
    a = proj(hub)
    assert a["copied_at"] == until and a["copy"] == {"since": until, "new": 0, "chat_text": None}
    assert a["chat_text"].count("Reports nuevos") == 1  # the summary period keeps its old text

    hub.post_message("alpha", "report", "Fresh report", "b", from_project="alpha")
    clock[0] += timedelta(minutes=5)
    c = proj(hub)["copy"]
    assert c["new"] == 1
    assert "Fresh report" in c["chat_text"] and "Session report" not in c["chat_text"] and "decisión" not in c["chat_text"]
    assert c["chat_text"].split("\n")[-1] == LAST.format("alpha")

    hub.mark_copied("alpha", hub.summary()["until"])
    clock[0] += timedelta(minutes=5)
    hub.log_decision("alpha", "Use ZSTD", "small")
    c = proj(hub)["copy"]
    assert c["new"] == 1 and "1 decisión" in c["chat_text"] and "informe" not in c["chat_text"]

    # a gate set after the copy counts (the window is inclusive, so move the clock past the decision first)
    clock[0] += timedelta(minutes=5)
    hub.mark_copied("alpha", hub.summary()["until"])
    clock[0] += timedelta(minutes=5)
    hub.set_gate("alpha", hub.get_project("alpha")["phases"][2]["id"], "review", "r")
    c = proj(hub)["copy"]
    assert c["new"] == 1 and "Gate esperando a Danny: Three (review)" in c["chat_text"]


def test_hours_and_since_do_not_touch_markers(hub, clock):
    make_world(hub, clock)
    hub.mark_copied("alpha", hub.summary()["until"])
    clock[0] += timedelta(hours=1)
    before = hub.summary_state()
    s = hub.summary(hours=24)
    a = next(p for p in s["projects"] if p["id"] == "alpha")
    assert a["copy"]["since"] == a["copied_at"] and a["copy"]["new"] == 0
    assert a["counts"]["reports"] == 1  # the period widened, the copy window did not
    hub.summary(since="2030-01-01T00:00:00+00:00")
    assert hub.summary_state() == before


def test_counts(hub, clock):
    make_world(hub, clock)
    assert proj(hub)["counts"] == {"gates": 1, "reports": 1, "decisions": 1, "items_opened": 2, "items_closed": 1, "phase_changes": 2}
    assert proj(hub, "beta")["counts"] == {k: 0 for k in ("gates", "reports", "decisions", "items_opened", "items_closed", "phase_changes")}


def test_copied_api(tmp_path, monkeypatch, clock):
    h = Hub(tmp_path)
    monkeypatch.setattr(web, "_hub", h)
    c = TestClient(web.app)
    make_world(h, clock)
    until = c.get("/api/summary").json()["until"]
    assert c.post("/api/summary/copied", json={"project_id": "alpha", "at": until}).json() == {"project_id": "alpha", "copied_at": until}
    clock[0] += timedelta(minutes=1)
    assert c.post("/api/summary/copied", json={"project_id": "beta"}).json()["copied_at"] == "2030-01-01T20:01:00+00:00"
    body = c.get("/api/summary").json()
    assert {p["id"]: p["copied_at"] for p in body["projects"]} == {
        "alpha": until, "beta": "2030-01-01T20:01:00+00:00", "gamma": None}
    assert c.post("/api/summary/copied", json={"project_id": "nope"}).status_code in (400, 404)
    assert c.post("/api/summary/copied", json={"project_id": "alpha", "at": "bad"}).status_code == 400
