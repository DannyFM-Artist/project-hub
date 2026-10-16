import json

import pytest

from project_hub.biblia import autonomy_line, waiting
from project_hub.hub import Hub, HubError


@pytest.fixture
def hub(tmp_path):
    h = Hub(tmp_path)
    h.create_project("demo", "Demo", "", phases=["Plan", "Build", "Ship"])
    return h


def ids(h, project="demo"):
    return [ph["id"] for ph in h.get_project(project)["phases"]]


def stored(h, phase_id, project="demo"):
    return next(ph for ph in json.loads((h.dir / "projects" / f"{project}.json").read_text(encoding="utf-8"))["phases"]
                if ph["id"] == phase_id)


def gate_of(ph):
    return {k: ph[k] for k in ("gate", "gate_reason", "gate_set_by", "gate_approved")}


def test_old_phases_have_no_gate_fields_until_a_gate_is_set(hub):
    p0, p1, _ = ids(hub)
    assert "gate" not in stored(hub, p0)
    hub.set_gate("demo", p1, "review", "check API")
    assert "gate" not in stored(hub, p0)  # untouched phases are not rewritten with defaults
    assert gate_of(stored(hub, p1)) == {"gate": "review", "gate_reason": "check API", "gate_set_by": "agent", "gate_approved": False}


def test_agent_adds_and_tightens(hub):
    p0, p1, _ = ids(hub)
    assert hub.set_gate("demo", p0, "manual_test", "try it on the device")["gate"] == "manual_test"
    hub.set_gate("demo", p1, "review", "check API", by="user")
    hub.approve_gate("demo", p1)
    ph = hub.set_gate("demo", p1, "manual_test", "needs a real test")
    assert gate_of(ph) == {"gate": "manual_test", "gate_reason": "needs a real test", "gate_set_by": "agent", "gate_approved": False}


@pytest.mark.parametrize("current, gate, reason", [
    (None, "none", "x"),               # none is never stricter
    ("review", "review", "x"),         # same gate
    ("manual_test", "review", "x"),    # loosening
    ("review", "none", "x"),           # removing
    (None, "review", ""),              # missing reason
    (None, "review", "   "),           # blank reason
    (None, "review", "x" * 161),       # reason too long
    (None, "bogus", "x"),              # unknown gate
])
def test_agent_refused(hub, current, gate, reason):
    p0 = ids(hub)[0]
    if current:
        hub.set_gate("demo", p0, current, "set first", by="user")
    before = stored(hub, p0)
    with pytest.raises(HubError) as e:
        hub.set_gate("demo", p0, gate, reason)
    assert stored(hub, p0) == before
    if current or gate == "none":
        assert "only add or tighten" in str(e.value) and "Danny" in str(e.value)
    if len(reason) > 160:
        assert "161" in str(e.value) and "limit is 160" in str(e.value)


def test_user_sets_changes_removes_and_approves(hub):
    p0 = ids(hub)[0]
    with pytest.raises(HubError):
        hub.approve_gate("demo", p0)  # no gate
    ph = hub.set_gate("demo", p0, "review", "", by="user")  # user needs no reason
    assert (ph["gate"], ph["gate_set_by"], ph["gate_approved"]) == ("review", "user", False)
    assert hub.approve_gate("demo", p0)["gate_approved"] is True
    with pytest.raises(HubError):
        hub.approve_gate("demo", p0)  # already approved
    assert hub.set_gate("demo", p0, "review", "edited", by="user")["gate_approved"] is True  # same type keeps approval
    ph = hub.set_gate("demo", p0, "manual_test", "test it", by="user")
    assert ph["gate_approved"] is False
    with pytest.raises(HubError):
        hub.approve_gate("demo", p0)  # manual_test cannot be approved
    assert hub.set_gate("demo", p0, "review", "loosened", by="user")["gate_approved"] is False
    ph = hub.set_gate("demo", p0, "none", by="user")
    assert gate_of(ph) == {"gate": "none", "gate_reason": "", "gate_set_by": None, "gate_approved": False}


def test_set_phase_status_review_gate(hub):
    p0 = ids(hub)[0]
    hub.set_gate("demo", p0, "review", "check the plan")
    for status in ("in_progress", "done"):
        with pytest.raises(HubError) as e:
            hub.set_phase_status("demo", p0, status)
        msg = str(e.value)
        assert "gated" in msg and "check the plan" in msg and "report" in msg and "'Plan'" in msg
    assert hub.set_phase_status("demo", p0, "todo")["status"] == "todo"  # moving back is allowed
    hub.approve_gate("demo", p0)
    assert hub.set_phase_status("demo", p0, "in_progress")["status"] == "in_progress"
    assert hub.set_phase_status("demo", p0, "done")["status"] == "done"


def test_set_phase_status_manual_test_gate(hub):
    p0 = ids(hub)[0]
    hub.set_gate("demo", p0, "manual_test", "Danny tests on the phone")
    for status in ("in_progress", "done"):
        with pytest.raises(HubError) as e:
            hub.set_phase_status("demo", p0, status, by="agent")
        assert "gated (manual_test)" in str(e.value) and "Danny tests on the phone" in str(e.value)
    assert hub.get_project("demo")["phases"][0]["status"] == "todo"
    assert hub.set_phase_status("demo", p0, "done", by="user")["status"] == "done"


def test_delete_phase_refuses_gated(hub):
    p0, p1, p2 = ids(hub)
    hub.set_gate("demo", p0, "review", "r")
    with pytest.raises(HubError) as e:
        hub.delete_phase("demo", p0)
    assert "gate" in str(e.value)
    assert ids(hub) == [p0, p1, p2]
    hub.set_gate("demo", p0, "none", by="user")
    hub.delete_phase("demo", p0)  # a removed gate no longer blocks deletion
    assert ids(hub) == [p1, p2]


def test_autonomy_line(hub):
    p0, p1, p2 = ids(hub)
    line = lambda: autonomy_line(hub.get_project("demo"))
    assert line() == "Autonomous work allowed up to phase 3 (Ship)"
    hub.set_gate("demo", p1, "review", "r")
    assert line() == "Autonomous work allowed up to phase 1 (Plan)"
    hub.set_gate("demo", p0, "review", "r")
    assert line() == "Autonomous work allowed up to phase 0 (phase 1 is gated)"
    hub.approve_gate("demo", p0)
    assert line() == "Autonomous work allowed up to phase 1 (Plan)"
    hub.approve_gate("demo", p1)
    hub.set_gate("demo", p2, "manual_test", "r")
    assert line() == "Autonomous work allowed up to phase 2 (Build)"
    hub.set_phase_status("demo", p2, "done", by="user")
    assert line() == "Autonomous work allowed up to phase 3 (Ship)"
    assert autonomy_line({"phases": []}) == "Autonomous work allowed up to phase 0"


def test_waiting_selection(hub):
    h = hub
    h.create_project("aaa", "Aaa", "", phases=["One", "Two"])
    h.create_project("zzz", "Zzz", "", phases=["One", "Two"])
    h.create_project("none", "No gates", "", phases=["One"])
    a0, a1 = ids(h, "aaa")
    z0, z1 = ids(h, "zzz")
    d0, d1, _ = ids(h)
    h.set_gate("demo", d1, "review", "later")  # not waiting: Plan is not done yet
    h.set_gate("aaa", a1, "manual_test", "test it")
    h.set_phase_status("aaa", a0, "done")
    h.set_gate("zzz", z0, "review", "check")
    h.set_gate("zzz", z1, "review", "second")  # behind z0, not waiting
    w = waiting(h.list_projects())
    assert w == [
        {"project_id": "aaa", "project_name": "Aaa", "phase_id": a1, "phase_name": "Two",
         "gate": "manual_test", "gate_reason": "test it", "gate_set_by": "agent"},
        {"project_id": "zzz", "project_name": "Zzz", "phase_id": z0, "phase_name": "One",
         "gate": "review", "gate_reason": "check", "gate_set_by": "agent"},
    ]
    h.set_phase_status("demo", d0, "done")
    assert [x["project_id"] for x in waiting(h.list_projects())] == ["aaa", "demo", "zzz"]
    h.approve_gate("zzz", z0)
    assert [x["project_id"] for x in waiting(h.list_projects())] == ["aaa", "demo"]


def test_biblia_shows_gates(hub):
    p0, p1, _ = ids(hub)
    text = (hub.dir / "BIBLIA.md").read_text(encoding="utf-8")
    assert "## Waiting for Danny\n\n(none)" in text
    assert "- Autonomous work allowed up to phase 3 (Ship)" in text
    hub.set_gate("demo", p0, "review", "check the plan")
    hub.set_gate("demo", p1, "manual_test", "on device", by="user")
    text = (hub.dir / "BIBLIA.md").read_text(encoding="utf-8")
    assert text.index("## Active resources") < text.index("## Waiting for Danny") < text.index("## Demo")
    assert f"1. [todo] Plan (id {p0}) <- current [gate: review, not approved, set by agent] check the plan" in text
    assert f"2. [todo] Build (id {p1}) [gate: manual_test, set by user] on device" in text
    assert f"- Demo (`demo`): phase Plan (id {p0}) [gate: review, not approved, set by agent] check the plan" in text
    assert "- Autonomous work allowed up to phase 0 (phase 1 is gated)" in text
    hub.approve_gate("demo", p0)
    text = (hub.dir / "BIBLIA.md").read_text(encoding="utf-8")
    assert "[gate: review, approved, set by agent]" in text
    assert "## Waiting for Danny\n\n(none)" in text  # Plan approved but not done; Build is behind it
