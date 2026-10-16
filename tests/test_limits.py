import json

import pytest

from project_hub.hub import Hub, HubError


@pytest.fixture
def hub(tmp_path):
    h = Hub(tmp_path)
    h.create_project("p", "P", "desc", phases=["one", "two", "three"])
    return h


def phases(h):
    return h.get_project("p")["phases"]


def snapshot(h):
    return (h.dir / "projects" / "p.json").read_text(encoding="utf-8")


def test_update_phase(hub):
    a, b, c = phases(hub)
    hub.set_phase_status("p", a["id"], "in_progress")
    r = hub.update_phase("p", a["id"], name="uno")
    assert (r["name"], r["notes"], r["status"]) == ("uno", "", "in_progress")
    r = hub.update_phase("p", a["id"], notes="n")
    assert (r["name"], r["notes"]) == ("uno", "n")
    r = hub.update_phase("p", a["id"], name="x", notes="y")
    assert (r["name"], r["notes"], r["status"]) == ("x", "y", "in_progress")
    assert phases(hub)[0] == r and phases(hub)[1:] == [b, c]


def test_update_phase_errors(hub):
    pid = phases(hub)[0]["id"]
    with pytest.raises(HubError, match="nothing to update: pass name and/or notes"):
        hub.update_phase("p", pid)
    with pytest.raises(HubError, match="unknown phase id"):
        hub.update_phase("p", "nope", name="x")
    with pytest.raises(HubError, match="unknown project"):
        hub.update_phase("nope", pid, name="x")


def test_delete_phase(hub):
    a, b, c = phases(hub)
    removed = hub.delete_phase("p", b["id"])
    assert removed == b
    assert phases(hub) == [a, c]
    assert "two" not in (hub.dir / "BIBLIA.md").read_text(encoding="utf-8")
    with pytest.raises(HubError, match="unknown phase id"):
        hub.delete_phase("p", b["id"])
    with pytest.raises(HubError, match="unknown project"):
        hub.delete_phase("nope", a["id"])


def _item(h):
    items = h.get_project("p")["items"]
    return items[0]["id"] if items else h.add_item("p", "bug", "t")["id"]


# (name, limit, write(hub, text))
CASES = [
    ("create description", 200, lambda h, t: h.create_project("q", "Q", t)),
    ("create phase name", 60, lambda h, t: h.create_project("q", "Q", "", phases=[t])),
    ("update description", 200, lambda h, t: h.update_project("p", description=t)),
    ("update next_step", 160, lambda h, t: h.update_project("p", next_step=t)),
    ("add_phase name", 60, lambda h, t: h.add_phase("p", t)),
    ("set_phase_status notes", 240, lambda h, t: h.set_phase_status("p", phases(h)[0]["id"], "done", t)),
    ("update_phase name", 60, lambda h, t: h.update_phase("p", phases(h)[0]["id"], name=t)),
    ("update_phase notes", 240, lambda h, t: h.update_phase("p", phases(h)[0]["id"], notes=t)),
    ("add_item title", 100, lambda h, t: h.add_item("p", "idea", t)),
    ("update_item title", 100, lambda h, t: h.update_item("p", _item(h), title=t)),
]


@pytest.mark.parametrize("name,limit,write", CASES, ids=[c[0] for c in CASES])
def test_limit_boundary(hub, name, limit, write):
    write(hub, "x" * limit)  # exactly at the limit is fine
    before = snapshot(hub)
    biblia = (hub.dir / "BIBLIA.md").read_text(encoding="utf-8")
    with pytest.raises(HubError) as e:
        write(hub, "x" * (limit + 1))
    assert "limit" in str(e.value) and str(limit + 1) in str(e.value) and f"limit is {limit}" in str(e.value)
    assert snapshot(hub) == before  # nothing written
    assert (hub.dir / "BIBLIA.md").read_text(encoding="utf-8") == biblia


def test_message_format(hub):
    with pytest.raises(HubError) as e:
        hub.update_project("p", next_step="x" * 245)
    assert str(e.value) == "next_step is 245 characters; the limit is 160. Please shorten it."


def test_no_stripping(hub):
    with pytest.raises(HubError):
        hub.add_item("p", "idea", "x" * 100 + " ")


def test_legacy_long_data_survives(hub):
    path = hub.dir / "projects" / "p.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["description"] = "d" * 600
    data["next_step"] = "n" * 300
    data["phases"][0]["notes"] = "z" * 300
    data["phases"][0]["name"] = "m" * 90
    data["items"].append({"id": "legacy01", "type": "bug", "title": "t" * 150, "details": "", "status": "open", "created_at": "x"})
    path.write_text(json.dumps(data), encoding="utf-8")
    pid = data["phases"][0]["id"]
    hub.update_project("p", status="paused")
    hub.set_phase_status("p", pid, "done")
    hub.update_phase("p", data["phases"][1]["id"], name="short")
    hub.update_item("p", "legacy01", status="done")
    hub.add_phase("p", "new")
    got = hub.get_project("p")
    assert (len(got["description"]), len(got["next_step"])) == (600, 300)
    assert (len(got["phases"][0]["notes"]), len(got["phases"][0]["name"])) == (300, 90)
    assert len(got["items"][0]["title"]) == 150
