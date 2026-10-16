import pytest
from fastapi.testclient import TestClient

from project_hub import hub as hub_module
from project_hub import web
from project_hub.hub import Hub


@pytest.fixture
def env(tmp_path, monkeypatch):
    h = Hub(tmp_path)
    monkeypatch.setattr(web, "_hub", h)
    h.create_project("alpha", "Alpha", "desc", phases=["one", "two"])
    h.create_project("beta", "Beta", "")
    return h, TestClient(web.app)


def test_summaries(env):
    h, c = env
    p1 = h.get_project("alpha")["phases"][0]["id"]
    h.set_phase_status("alpha", p1, "done")
    h.post_message("alpha", "task", "t", "b")
    h.post_message("all", "message", "t2", "b")
    rows = {r["id"]: r for r in c.get("/api/projects").json()}
    a = rows["alpha"]
    assert (a["current_phase"], a["phases_done"], a["phases_total"], a["unread_count"]) == ("two", 1, 2, 2)
    assert rows["beta"]["current_phase"] is None and rows["beta"]["unread_count"] == 1
    for k in ("name", "status", "description", "next_step", "updated_at"):
        assert k in a


def test_overview_order_and_phase_position(env, monkeypatch):
    h, c = env
    ticks = iter(range(1000))  # updated_at has 1 s resolution; a fake clock makes the order deterministic
    monkeypatch.setattr(hub_module, "_now", lambda: f"2030-01-01T00:{next(ticks):04d}+00:00")
    h.create_project("gamma", "Gamma", "", phases=["a", "b", "c", "d", "e", "f"])
    gamma = h.get_project("gamma")["phases"]
    for ph in gamma[:2]:
        h.set_phase_status("gamma", ph["id"], "done")
    h.create_project("delta", "Delta", "")
    h.update_project("delta", status="parked")
    h.update_project("alpha", status="paused")
    h.update_project("beta", next_step="older")
    h.update_project("gamma", next_step="newest")  # both active; gamma is more recent, though alphabetically later
    rows = c.get("/api/projects").json()
    assert [r["id"] for r in rows] == ["gamma", "beta", "alpha", "delta"]  # status order, then most recent first
    g = rows[0]
    assert (g["current_phase"], g["current_phase_pos"], g["phases_total"], g["phases_done"]) == ("c", 3, 6, 2)
    assert rows[1]["current_phase_pos"] is None  # beta has no phases


def test_unread_counts(env):
    h, c = env
    h.post_message("alpha", "task", "to alpha", "b")
    h.post_message("all", "message", "to all", "b")
    read = h.post_message("all", "message", "already read", "b")
    h.mark_message(read["id"], "read")
    # global: unique unread ids, so the "all" message counts once (not once per project)
    assert c.get("/api/unread").json() == {"count": 2}
    # per project: every unread message that applies, including those sent to "all"
    rows = {r["id"]: r["unread_count"] for r in c.get("/api/projects").json()}
    assert rows == {"alpha": 2, "beta": 1}
    assert sum(1 for m in c.get("/api/projects/beta").json()["inbox"] if m["status"] == "unread") == 1


def test_detail_inbox(env):
    h, c = env
    h.post_message("alpha", "task", "t", "b")
    h.post_message("beta", "task", "other", "b")
    d = c.get("/api/projects/alpha").json()
    assert d["id"] == "alpha" and [m["title"] for m in d["inbox"]] == ["t"]


def test_phase_item_message_routes(env):
    h, c = env
    ph = h.get_project("alpha")["phases"][0]["id"]
    r = c.post(f"/api/projects/alpha/phases/{ph}", json={"status": "in_progress", "notes": "n"})
    assert r.status_code == 200
    assert h.get_project("alpha")["phases"][0]["status"] == "in_progress"

    item = c.post("/api/projects/alpha/items", json={"type": "bug", "title": "x"}).json()
    assert h.get_project("alpha")["items"][0]["title"] == "x"
    c.patch(f"/api/projects/alpha/items/{item['id']}", json={"status": "done", "title": "y"})
    got = h.get_project("alpha")["items"][0]
    assert (got["status"], got["title"], got["type"]) == ("done", "y", "bug")

    m = c.post("/api/messages", json={"to_project": "beta", "kind": "task", "title": "t", "body": "b",
                                       "from_project": "alpha"}).json()
    assert h.read_inbox("beta")[0]["from_project"] == "alpha"
    c.patch(f"/api/messages/{m['id']}", json={"status": "read"})
    assert h.read_inbox("beta") == []


def test_errors(env):
    h, c = env
    ph = h.get_project("alpha")["phases"][0]["id"]
    for r in (
        c.get("/api/projects/nope"),
        c.post("/api/projects/nope/items", json={"type": "bug", "title": "x"}),
        c.post(f"/api/projects/alpha/phases/zzz", json={"status": "done"}),
        c.patch("/api/projects/alpha/items/zzz", json={"status": "done"}),
        c.patch("/api/messages/zzz", json={"status": "read"}),
    ):
        assert r.status_code == 404 and r.json()["error"].startswith("unknown ")
    for r in (
        c.post(f"/api/projects/alpha/phases/{ph}", json={"status": "bogus"}),
        c.post("/api/projects/alpha/items", json={"type": "bogus", "title": "x"}),
        c.post("/api/messages", json={"to_project": "alpha", "kind": "bogus", "title": "t", "body": "b"}),
    ):
        assert r.status_code == 400 and "error" in r.json()


def test_index(env):
    r = env[1].get("/")
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]
