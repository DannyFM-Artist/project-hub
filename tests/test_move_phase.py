import pytest

from project_hub.hub import Hub, HubError
from test_chat_role import tools_and_calls

GATE_KEYS = ("gate_state", "gate_reason", "gate_set_by", "gate_resolved_action", "gate_resolved_words", "gate_resolved_at")


@pytest.fixture
def hub(tmp_path):
    h = Hub(tmp_path)
    h.create_project("demo", "Demo", "", phases=["One", "Two", "Three"])
    h.ids = [p["id"] for p in h.get_project("demo")["phases"]]
    return h


def names(hub):
    return [p["name"] for p in hub.get_project("demo")["phases"]]


def test_move_to_end_and_front(hub):
    hub.move_phase("demo", hub.ids[0], 2)
    assert names(hub) == ["Two", "Three", "One"]
    hub.move_phase("demo", hub.ids[2], 0)
    assert names(hub) == ["Three", "Two", "One"]
    biblia = (hub.dir / "BIBLIA.md").read_text(encoding="utf-8")
    assert all(f"{n}. [todo] {name} " in biblia for n, name in ((1, "Three"), (2, "Two"), (3, "One")))


def test_unknown_phase_and_bad_position(hub):
    with pytest.raises(HubError):
        hub.move_phase("demo", "nope", 0)
    for pos in (-1, 3, "1", None, True):
        with pytest.raises(HubError, match="from 0 to 2"):
            hub.move_phase("demo", hub.ids[0], pos)
    assert names(hub) == ["One", "Two", "Three"]


def test_gate_and_history_kept(hub):
    one = hub.ids[0]
    hub.set_gate("demo", one, "check")
    hub.resolve_gate("demo", one, "sigue", "dale")
    hub.set_phase_status("demo", one, "in_progress", "some notes")
    before = hub.get_project("demo")["phases"][0]
    hub.move_phase("demo", one, 2)
    after = hub.get_project("demo")["phases"][2]
    assert after == before and all(after.get(k) for k in GATE_KEYS)


def test_move_logged_by_chat(hub):
    hub.move_phase("demo", hub.ids[0], 2)
    hub.move_phase("demo", hub.ids[0], 2)  # already there: nothing to log
    ev = [e for e in hub.activity("demo") if e["type"] == "phase_moved"]
    assert [(e["by"], e["phase"], e["text"]) for e in ev] == [("chat", "One", "position 0 → 2")]


def test_mcp_move_phase_only_for_chat(hub, tmp_path):
    for role in (None, "agent"):
        assert "move_phase" not in tools_and_calls(tmp_path, role)[0]
    args = {"project_id": "demo", "phase_id": hub.ids[2]}
    tools, out = tools_and_calls(tmp_path, "chat", [("move_phase", {**args, "position": 0}),
                                                    ("move_phase", {**args, "position": 9})])
    assert "move_phase" in tools
    assert out[0] == f"Moved phase {hub.ids[2]} (Three) to position 0" and out[1].startswith("Error:")
    assert names(hub) == ["Three", "One", "Two"]
