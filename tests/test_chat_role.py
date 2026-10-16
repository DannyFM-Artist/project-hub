import sys

import anyio
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from project_hub.hub import Hub, HubError

CHAT = {"approve_gate", "complete_manual_phase"}


def tools_and_calls(tmp_path, role, calls=()):
    async def go():
        env = {"PROJECT_HUB_DATA": str(tmp_path), **({"PROJECT_HUB_ROLE": role} if role else {})}
        params = StdioServerParameters(command=sys.executable, args=["-m", "project_hub.mcp_server"], env=env)
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()
                tools = {t.name: t for t in (await s.list_tools()).tools}
                return tools, [(await s.call_tool(n, a)).content[0].text for n, a in calls]

    return anyio.run(go)


@pytest.fixture
def hub(tmp_path):
    h = Hub(tmp_path)
    h.create_project("demo", "Demo", "", phases=["Rev", "Man"])
    rev, man = [p["id"] for p in h.get_project("demo")["phases"]]
    h.set_gate("demo", rev, "review", "check")
    h.set_gate("demo", man, "manual_test", "try it")
    h.ids = rev, man
    return h


def test_tools_absent_without_flag(tmp_path):
    assert not CHAT & set(tools_and_calls(tmp_path, None)[0])
    assert not CHAT & set(tools_and_calls(tmp_path, "agent")[0])


def test_tools_present_with_flag_and_docs(tmp_path):
    tools = tools_and_calls(tmp_path, "chat")[0]
    assert CHAT <= set(tools)
    for n in CHAT:
        d = tools[n].description
        assert "explicitly told you" in d and "own initiative" in d and "hub" in d and "exactly" in d


@pytest.mark.parametrize("words", ["", "   ", None])
def test_empty_words_refused(hub, words):
    rev, man = hub.ids
    with pytest.raises(HubError):
        hub.approve_gate_chat("demo", rev, words)
    with pytest.raises(HubError):
        hub.complete_manual_phase("demo", man, words)


def test_too_long_words_refused(hub):
    with pytest.raises(HubError, match="300"):
        hub.approve_gate_chat("demo", hub.ids[0], "x" * 301)


def test_approve_records_fields_and_event(hub):
    rev, _ = hub.ids
    ph = hub.approve_gate_chat("demo", rev, "  sí, apruebo Rev  ")
    assert ph["gate_approved"] is True and ph["gate_approved_by"] == "chat" and ph["gate_set_by"] == "agent"
    assert ph["gate_approved_words"] == "sí, apruebo Rev" and ph["gate_approved_at"]
    ev = hub.activity("demo")[-1]
    assert ev["by"] == "chat" and ev["words"] == "sí, apruebo Rev" and "aprobado vía chat: «sí, apruebo Rev»" in ev["text"]
    with pytest.raises(HubError):
        hub.approve_gate_chat("demo", rev, "otra vez")


def test_complete_manual_records_fields_and_event(hub):
    _, man = hub.ids
    ph = hub.complete_manual_phase("demo", man, "ya lo probé")
    assert ph["status"] == "done" and ph["gate_approved_by"] == "chat" and ph["gate_approved_words"] == "ya lo probé"
    ev = hub.activity("demo")[-1]
    assert ev["by"] == "chat" and ev["words"] == "ya lo probé" and "aprobado vía chat" in ev["text"]
    with pytest.raises(HubError):
        hub.complete_manual_phase("demo", man, "otra vez")


def test_wrong_gate_type_refused(hub):
    rev, man = hub.ids
    with pytest.raises(HubError):
        hub.approve_gate_chat("demo", man, "ok")
    with pytest.raises(HubError):
        hub.complete_manual_phase("demo", rev, "ok")


def test_agents_still_refused_on_gated_phases(hub):
    rev, man = hub.ids
    for ph in (rev, man):
        with pytest.raises(HubError, match="gated"):
            hub.set_phase_status("demo", ph, "done", by="agent")


def test_mcp_set_phase_status_cannot_complete_manual_test(hub, tmp_path):
    _, man = hub.ids
    _, out = tools_and_calls(tmp_path, "chat", [("set_phase_status", {"project_id": "demo", "phase_id": man, "status": "done"})])
    assert out[0].startswith("Error:") and "gated" in out[0]
    assert hub.get_project("demo")["phases"][1]["status"] == "todo"


def test_mcp_chat_tool_end_to_end(hub, tmp_path):
    rev, _ = hub.ids
    _, out = tools_and_calls(tmp_path, "chat", [("approve_gate", {"project_id": "demo", "phase_id": rev, "danny_words": " "}),
                                                 ("approve_gate", {"project_id": "demo", "phase_id": rev, "danny_words": "vale"})])
    assert out[0].startswith("Error:") and out[1].startswith("Gate approved")
    assert hub.get_project("demo")["phases"][0]["gate_approved_words"] == "vale"
