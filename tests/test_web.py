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
    monkeypatch.setattr(hub_module, "_now", lambda: "2030-01-01T00:{:02d}:{:02d}+00:00".format(*divmod(next(ticks), 60)))
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


@pytest.mark.parametrize("url, ctype", [
    ("/favicon.svg", "image/svg+xml"),
    ("/favicon.ico", "image/png"),
    ("/manifest.webmanifest", "application/manifest+json"),
    *[(f"/icons/{n}", "image/png") for n in (
        "icon-16.png", "icon-32.png", "icon-48.png", "apple-touch-icon.png",
        "icon-192.png", "icon-512.png", "icon-512-maskable.png")],
])
def test_icon_routes(env, url, ctype):
    r = env[1].get(url)
    assert r.status_code == 200 and r.headers["content-type"].startswith(ctype)


def test_manifest_lists_icons(env):
    c = env[1]
    m = c.get("/manifest.webmanifest").json()
    assert (m["name"], m["start_url"], m["display"]) == ("project-hub", "/", "standalone")
    got = {(i["src"], i["sizes"], i["purpose"]) for i in m["icons"]}
    assert got == {("/icons/icon-192.png", "192x192", "any"), ("/icons/icon-512.png", "512x512", "any"),
                   ("/icons/icon-512-maskable.png", "512x512", "maskable")}
    for src, *_ in got:
        assert c.get(src).status_code == 200


def test_resources_routes(env):
    h, c = env
    assert c.get("/api/resources").json() == []
    h.claim_resource("gpu", "alpha", "training", ttl_minutes=30)
    rows = c.get("/api/resources").json()
    assert len(rows) == 1
    row = rows[0]
    assert {k: row[k] for k in ("resource", "project_id", "purpose")} == {"resource": "gpu", "project_id": "alpha", "purpose": "training"}
    assert {"acquired_at", "expires_at"} <= row.keys()
    assert type(row["seconds_left"]) is int and 1790 <= row["seconds_left"] <= 1800
    r = c.post("/api/resources/release", json={"resource": "GPU"})
    assert r.status_code == 200 and r.json()["project_id"] == "alpha"
    assert c.get("/api/resources").json() == []
    r = c.post("/api/resources/release", json={"resource": "gpu"})
    assert r.status_code == 404 and r.json()["error"].startswith("unknown resource")
    assert c.post("/api/resources/release", json={"resource": " "}).status_code == 400


def test_gate_fields_and_waiting(env):
    h, c = env
    p0, p1 = (ph["id"] for ph in h.get_project("alpha")["phases"])
    d = c.get("/api/projects/alpha").json()
    assert all(ph["gate_state"] is None and ph["gate_reason"] == "" and ph["gate_set_by"] is None
               and ph["gate_resolved_action"] is None and ph["gate_resolved_words"] is None and ph["gate_resolved_at"] is None
               for ph in d["phases"])  # defaults filled for phases stored without gate fields
    assert d["autonomy"] == "Autonomous work allowed up to phase 2 (two)"
    assert c.get("/api/waiting").json() == []
    h.set_gate("alpha", p0, "look at it")
    assert c.get("/api/waiting").json() == [{"project_id": "alpha", "project_name": "Alpha", "phase_id": p0, "phase_name": "one",
                                             "reason": "look at it", "set_by": "agent"}]
    d = c.get("/api/projects/alpha").json()
    assert d["autonomy"] == "Autonomous work allowed up to phase 0 (phase 1 is gated)"
    assert "gate" not in d["phases"][0] and "gate_approved" not in d["phases"][0]  # legacy keys stay out of the API
    assert (d["phases"][0]["gate_state"], d["phases"][0]["gate_reason"]) == ("waiting", "look at it")
    h.resolve_gate("alpha", p0, "sigue", "sí, sigue")
    ph = c.get("/api/projects/alpha").json()["phases"][0]
    assert (ph["gate_state"], ph["gate_resolved_action"], ph["gate_resolved_words"]) == ("continue", "sigue", "sí, sigue")
    assert ph["gate_resolved_at"]
    assert c.get("/api/waiting").json() == []


def test_gate_endpoints_are_gone(env):
    h, c = env
    p0 = h.get_project("alpha")["phases"][0]["id"]
    base = f"/api/projects/alpha/phases/{p0}"
    assert c.post(f"{base}/gate", json={"gate": "review", "reason": "r"}).status_code in (404, 405)
    assert c.post(f"{base}/gate/approve").status_code in (404, 405)
    assert "gate_state" not in h.get_project("alpha")["phases"][0]


def test_dashboard_phase_status_refused_while_waiting(env):
    h, c = env
    p0 = h.get_project("alpha")["phases"][0]["id"]
    h.set_gate("alpha", p0, "Danny tests it")
    for status in ("in_progress", "done"):
        r = c.post(f"/api/projects/alpha/phases/{p0}", json={"status": status})
        assert r.status_code == 400 and "waits for Danny: Danny tests it" in r.json()["error"]
    assert h.get_project("alpha")["phases"][0]["status"] == "todo"
    h.resolve_gate("alpha", p0, "sigue", "sigue")
    assert c.post(f"/api/projects/alpha/phases/{p0}", json={"status": "done"}).status_code == 200


def test_over_limit_item_title_is_400(env):
    h, c = env
    r = c.post("/api/projects/alpha/items", json={"type": "bug", "title": "x" * 101})
    assert r.status_code == 400
    assert "101" in r.json()["error"] and "limit is 100" in r.json()["error"]
    assert h.get_project("alpha")["items"] == []


def test_attention_fields(env):
    """Overview rows carry every waiting gate, open messages to Danny and unread reports (bell and "Para ti")."""
    h, c = env
    one, two = [ph["id"] for ph in h.get_project("alpha")["phases"]]
    h.set_gate("alpha", one, "look")
    h.set_gate("alpha", two, "test it")
    h.post_message("user", "message", "to danny", "b", "alpha")
    done = h.post_message("user", "message", "done one", "b", "alpha")
    h.mark_message(done["id"], "done")
    h.post_message("alpha", "report", "rep", "body", "alpha")
    h.post_message("all", "report", "rep all", "body", "beta")
    h.post_message("alpha", "task", "not a report", "b")
    rows = {r["id"]: r for r in c.get("/api/projects").json()}
    a = rows["alpha"]
    assert [ph["gate_state"] for ph in a["phases"]] == ["waiting", "waiting"]  # both gates, not only the first one
    assert not any(k in ph for ph in a["phases"] for k in ("gate", "gate_approved"))  # no legacy keys
    assert [m["title"] for m in a["user_messages"]] == ["to danny"]
    assert sorted(m["title"] for m in a["reports"]) == ["rep", "rep all"]
    assert rows["beta"]["user_messages"] == [] and [m["title"] for m in rows["beta"]["reports"]] == ["rep all"]
