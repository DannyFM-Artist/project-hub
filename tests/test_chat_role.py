import pytest

from project_hub.hub import Hub
from test_mcp_server import run_session

GONE = {"approve_gate", "complete_manual_phase"}


def tools_and_calls(tmp_path, role, calls=()):
    async def steps(s):
        tools = {t.name: t for t in (await s.list_tools()).tools}
        return tools, [(await s.call_tool(n, a)).content[0].text for n, a in calls]

    return run_session(tmp_path, steps, role)


@pytest.fixture
def hub(tmp_path):
    h = Hub(tmp_path)
    h.create_project("demo", "Demo", "", phases=["One", "Two"])
    h.ids = [p["id"] for p in h.get_project("demo")["phases"]]
    h.set_gate("demo", h.ids[0], "check")
    return h


def test_resolve_gate_absent_without_role(tmp_path):
    for role in (None, "agent"):
        names = set(tools_and_calls(tmp_path, role)[0])
        assert "resolve_gate" not in names and not GONE & names and "set_gate" in names


def test_resolve_gate_present_with_role_and_docs(tmp_path):
    tools = tools_and_calls(tmp_path, "chat")[0]
    assert "resolve_gate" in tools and not GONE & set(tools)
    d = tools["resolve_gate"].description
    assert "explicitly said it in this conversation" in d and "own initiative" in d and "report" in d and "hub" in d
    assert "exactly" in d and all(a in d for a in ('"sigue"', '"hecho"', '"vuelve a cerrar"'))
    schema = tools["set_gate"].input_schema["properties"]
    assert set(schema) == {"project_id", "phase_id", "reason"}


def test_mcp_agent_cannot_move_waiting_phase(hub, tmp_path):
    one = hub.ids[0]
    calls = [("set_phase_status", {"project_id": "demo", "phase_id": one, "status": s}) for s in ("in_progress", "done")]
    for role in (None, "chat"):
        _, out = tools_and_calls(tmp_path, role, calls)
        assert all(o.startswith("Error:") and "waits for Danny: check" in o and "report" in o for o in out)
    assert hub.get_project("demo")["phases"][0]["status"] == "todo"


def test_mcp_agent_cannot_delete_gated_phase(hub, tmp_path):
    _, out = tools_and_calls(tmp_path, None, [("delete_phase", {"project_id": "demo", "phase_id": hub.ids[0]})])
    assert out[0].startswith("Error:") and "has a gate" in out[0]
    assert len(hub.get_project("demo")["phases"]) == 2


def test_mcp_set_gate_set_by(hub, tmp_path):
    two = hub.ids[1]
    _, out = tools_and_calls(tmp_path, "chat", [("set_gate", {"project_id": "demo", "phase_id": two, "reason": "try it"})])
    assert out[0] == f"Phase {two} (Two) [espera a Danny] try it"
    assert hub.get_project("demo")["phases"][1]["gate_set_by"] == "chat"
    hub.resolve_gate("demo", two, "sigue", "ok")
    tools_and_calls(tmp_path, None, [("set_gate", {"project_id": "demo", "phase_id": two, "reason": "again"})])
    assert hub.get_project("demo")["phases"][1]["gate_set_by"] == "agent"


def test_mcp_resolve_gate_end_to_end(hub, tmp_path):
    one = hub.ids[0]
    args = {"project_id": "demo", "phase_id": one}
    _, out = tools_and_calls(tmp_path, "chat", [
        ("resolve_gate", {**args, "action": "sigue", "danny_words": " "}),
        ("resolve_gate", {**args, "action": "approve", "danny_words": "ok"}),
        ("resolve_gate", {**args, "action": "hecho", "danny_words": "ya lo hice yo"}),
        ("resolve_gate", {**args, "action": "hecho", "danny_words": "otra vez"}),
    ])
    assert out[0].startswith("Error:") and out[1].startswith("Error:") and out[3].startswith("Error:")
    assert out[2] == f"Phase {one} (One, done) [resuelto vía chat (hecho): «ya lo hice yo»]"
    ph = hub.get_project("demo")["phases"][0]
    assert (ph["status"], ph["gate_resolved_words"], ph["gate_resolved_action"]) == ("done", "ya lo hice yo", "hecho")
    ev = [e for e in hub.activity("demo") if e["type"] == "gate_resolved"]
    assert [(e["by"], e["action"], e["words"]) for e in ev] == [("chat", "hecho", "ya lo hice yo")]
