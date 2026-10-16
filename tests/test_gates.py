import json
import os
import subprocess
import sys

import pytest

from project_hub.biblia import autonomy_line, gate_label, waiting
from project_hub.hub import Hub, HubError

NEW = ("gate_state", "gate_reason", "gate_set_by", "gate_resolved_action", "gate_resolved_words", "gate_resolved_at")


@pytest.fixture
def hub(tmp_path):
    h = Hub(tmp_path)
    h.create_project("demo", "Demo", "", phases=["Plan", "Build", "Ship"])
    return h


def ids(h, project="demo"):
    return [ph["id"] for ph in h.get_project(project)["phases"]]


def path(h, project="demo"):
    return h.dir / "projects" / f"{project}.json"


def stored(h, phase_id, project="demo"):
    return next(ph for ph in json.loads(path(h, project).read_text(encoding="utf-8"))["phases"] if ph["id"] == phase_id)


def gate_of(ph):
    return {k: ph.get(k) for k in NEW + ("gate", "gate_approved")}


# --- set_gate ------------------------------------------------------------------


def test_untouched_phases_get_no_gate_fields(hub):
    p0, p1, _ = ids(hub)
    hub.set_gate("demo", p1, "check API")
    assert not any(k.startswith("gate") for k in stored(hub, p0))
    assert gate_of(stored(hub, p1)) == {"gate_state": "waiting", "gate_reason": "check API", "gate_set_by": "agent",
                                        "gate_resolved_action": None, "gate_resolved_words": None, "gate_resolved_at": None,
                                        "gate": "review", "gate_approved": False}  # legacy keys for old readers


def test_legacy_keys_follow_every_write(hub):
    p0 = ids(hub)[0]
    hub.set_gate("demo", p0, "r")
    assert (stored(hub, p0)["gate"], stored(hub, p0)["gate_approved"]) == ("review", False)
    hub.resolve_gate("demo", p0, "sigue", "sigue")
    assert (stored(hub, p0)["gate"], stored(hub, p0)["gate_approved"]) == ("review", True)
    hub.resolve_gate("demo", p0, "vuelve a cerrar", "no, espera")
    assert (stored(hub, p0)["gate"], stored(hub, p0)["gate_approved"]) == ("review", False)
    hub.resolve_gate("demo", p0, "hecho", "ya está")
    assert (stored(hub, p0)["gate"], stored(hub, p0)["gate_approved"]) == ("review", True)


def test_set_gate_on_waiting_updates_reason_only(hub):
    p0 = ids(hub)[0]
    hub.set_gate("demo", p0, "first")
    ph = hub.set_gate("demo", p0, "second", by="chat")
    assert (ph["gate_state"], ph["gate_reason"], ph["gate_set_by"]) == ("waiting", "second", "agent")


def test_set_gate_puts_continued_gate_back_to_waiting(hub):
    p0 = ids(hub)[0]
    hub.set_gate("demo", p0, "first")
    hub.resolve_gate("demo", p0, "sigue", "dale")
    ph = hub.set_gate("demo", p0, "look again", by="chat")
    assert gate_of(ph) == {"gate_state": "waiting", "gate_reason": "look again", "gate_set_by": "chat",
                           "gate_resolved_action": None, "gate_resolved_words": None, "gate_resolved_at": None,
                           "gate": "review", "gate_approved": False}


@pytest.mark.parametrize("reason", ["", "   ", None, "x" * 161])
def test_set_gate_reason_required_and_limited(hub, reason):
    p0 = ids(hub)[0]
    with pytest.raises(HubError) as e:
        hub.set_gate("demo", p0, reason)
    assert "gate" not in stored(hub, p0)
    if reason and len(reason) > 160:
        assert "161" in str(e.value) and "limit is 160" in str(e.value)


def test_set_gate_has_no_gate_type_argument(hub):
    with pytest.raises(TypeError):
        hub.set_gate("demo", ids(hub)[0], "review", "check")
    with pytest.raises(HubError):
        hub.set_gate("demo", ids(hub)[0], "r", by="dashboard")  # only agent or chat


# --- refusals --------------------------------------------------------------------


@pytest.mark.parametrize("by", ["agent", "dashboard", "chat"])
def test_set_phase_status_refused_while_waiting_for_everyone(hub, by):
    p0 = ids(hub)[0]
    hub.set_gate("demo", p0, "check the plan")
    for status in ("in_progress", "done"):
        with pytest.raises(HubError) as e:
            hub.set_phase_status("demo", p0, status, by=by)
        msg = str(e.value)
        assert "'Plan' waits for Danny: check the plan" in msg and "report" in msg and "stop" in msg
    assert hub.set_phase_status("demo", p0, "todo", by=by)["status"] == "todo"  # moving back is allowed
    hub.resolve_gate("demo", p0, "sigue", "sigue")
    assert hub.set_phase_status("demo", p0, "in_progress", by=by)["status"] == "in_progress"
    assert hub.set_phase_status("demo", p0, "done", by=by)["status"] == "done"


def test_delete_phase_refuses_any_gate(hub):
    p0, p1, p2 = ids(hub)
    hub.set_gate("demo", p0, "r")
    hub.set_gate("demo", p1, "r")
    hub.resolve_gate("demo", p1, "sigue", "ok")
    for ph in (p0, p1):
        with pytest.raises(HubError, match="has a gate"):
            hub.delete_phase("demo", ph)
    assert ids(hub) == [p0, p1, p2]


def test_hub_has_no_old_gate_methods(hub):
    for name in ("approve_gate", "approve_gate_chat", "complete_manual_phase", "_chat_action"):
        assert not hasattr(hub, name)


# --- resolve_gate ----------------------------------------------------------------


@pytest.mark.parametrize("action", ["sigue", "hecho"])
def test_resolve_records_words_time_action(hub, action):
    p0 = ids(hub)[0]
    hub.set_gate("demo", p0, "check")
    ph = hub.resolve_gate("demo", p0, action, "  sí, adelante  ")
    assert (ph["gate_state"], ph["gate_resolved_action"], ph["gate_resolved_words"]) == ("continue", action, "sí, adelante")
    assert ph["gate_resolved_at"] and ph["status"] == ("done" if action == "hecho" else "todo")
    ev = [e for e in hub.activity("demo") if e["type"] == "gate_resolved"][-1]
    assert (ev["by"], ev["words"], ev["action"], ev["phase"]) == ("chat", "sí, adelante", action, "Plan")
    assert ev["text"] == f"resuelto vía chat ({action}): «sí, adelante»"
    if action == "hecho":
        last = hub.activity("demo")[-1]
        assert (last["type"], last["text"], last["by"]) == ("phase_status", "todo → done", "chat")
    assert gate_label(ph) == f"[resuelto vía chat ({action}): «sí, adelante»]"


def test_vuelve_a_cerrar_after_hecho_reopens(hub):
    p0 = ids(hub)[0]
    hub.set_gate("demo", p0, "check")
    hub.resolve_gate("demo", p0, "hecho", "hecho")
    ph = hub.resolve_gate("demo", p0, "vuelve a cerrar", "no, vuelve a cerrar")
    assert (ph["status"], ph["gate_state"], ph["gate_resolved_action"]) == ("todo", "waiting", "vuelve a cerrar")
    assert ph["gate_resolved_words"] == "no, vuelve a cerrar"
    ev = [e for e in hub.activity("demo") if e["type"] == "gate_resolved"][-1]
    assert ev["action"] == "vuelve a cerrar" and ev["words"] == "no, vuelve a cerrar"
    assert hub.activity("demo")[-1]["text"] == "done → todo"
    assert gate_label(ph) == "[espera a Danny] check"


def test_vuelve_a_cerrar_after_sigue_keeps_status(hub):
    p0 = ids(hub)[0]
    hub.set_gate("demo", p0, "check")
    hub.resolve_gate("demo", p0, "sigue", "sigue")
    hub.set_phase_status("demo", p0, "in_progress")
    ph = hub.resolve_gate("demo", p0, "vuelve a cerrar", "para")
    assert (ph["status"], ph["gate_state"]) == ("in_progress", "waiting")


def test_resolve_refused_when_action_does_not_fit(hub):
    p0, p1, _ = ids(hub)
    with pytest.raises(HubError, match="has no gate"):
        hub.resolve_gate("demo", p1, "sigue", "ok")
    hub.set_gate("demo", p0, "check")
    with pytest.raises(HubError, match="state waiting"):
        hub.resolve_gate("demo", p0, "vuelve a cerrar", "ok")
    hub.resolve_gate("demo", p0, "sigue", "ok")
    for action in ("sigue", "hecho"):
        with pytest.raises(HubError, match="state continue"):
            hub.resolve_gate("demo", p0, action, "ok")
    with pytest.raises(HubError, match="invalid action"):
        hub.resolve_gate("demo", p0, "approve", "ok")


@pytest.mark.parametrize("words", ["", "   ", None, "x" * 301])
def test_resolve_refuses_bad_words(hub, words):
    p0 = ids(hub)[0]
    hub.set_gate("demo", p0, "check")
    before = stored(hub, p0)
    with pytest.raises(HubError):
        hub.resolve_gate("demo", p0, "sigue", words)
    assert stored(hub, p0) == before


# --- migration -------------------------------------------------------------------


def write_old(h, phases):
    """Store demo with these raw phase dicts, as older code wrote them."""
    data = json.loads(path(h).read_text(encoding="utf-8"))
    data["phases"] = [{"id": f"p{i}", "name": f"P{i}", "status": "todo", "notes": "", **ph} for i, ph in enumerate(phases)]
    path(h).write_text(json.dumps(data), encoding="utf-8")


OLD = [
    {"gate": "review", "gate_reason": "look", "gate_set_by": "agent", "gate_approved": False},
    {"gate": "review", "gate_reason": "ok'd", "gate_set_by": "user", "gate_approved": True},
    {"gate": "manual_test", "gate_reason": "phone", "gate_set_by": "dashboard", "gate_approved": False},
    {"gate": "manual_test", "gate_reason": "done by hand", "gate_set_by": "agent", "gate_approved": False, "status": "done"},
    {"gate": "review", "gate_reason": "chat ok", "gate_set_by": "agent", "gate_approved": True,
     "gate_approved_by": "chat", "gate_approved_words": "apruebo", "gate_approved_at": "2030-01-01T08:00:00+00:00"},
    {"gate": "manual_test", "gate_reason": "tested", "gate_set_by": "agent", "gate_approved": False, "status": "done",
     "gate_approved_by": "chat", "gate_approved_words": "ya lo probé", "gate_approved_at": "2030-01-02T08:00:00+00:00"},
    {"gate": "none", "gate_reason": "", "gate_set_by": None, "gate_approved": False},
    {"gate": "none", "gate_reason": "", "gate_set_by": None, "gate_approved": False, "gate_approved_by": "chat",
     "gate_approved_words": "stale", "gate_approved_at": "2030-01-01T08:00:00+00:00"},
    {},
]


def r(state, reason, by, action=None, words=None, at=None):
    return {"gate_state": state, "gate_reason": reason, "gate_set_by": by, "gate_resolved_action": action,
            "gate_resolved_words": words, "gate_resolved_at": at, "gate": "review", "gate_approved": state == "continue"}


EXPECTED = [
    r("waiting", "look", "agent"),
    r("continue", "ok'd", "chat", "sigue"),
    r("waiting", "phone", "chat"),
    r("waiting", "done by hand", "agent"),  # literal rule; a done phase never blocks
    r("continue", "chat ok", "agent", "sigue", "apruebo", "2030-01-01T08:00:00+00:00"),
    r("continue", "tested", "agent", "hecho", "ya lo probé", "2030-01-02T08:00:00+00:00"),
]


def check_migrated(phases):
    for ph, want in zip(phases, EXPECTED):
        assert {k: v for k, v in ph.items() if k.startswith("gate")} == want, ph["id"]
    for ph in phases[len(EXPECTED):]:
        assert not any(k.startswith("gate") for k in ph), ph["id"]  # no gate: legacy-only keys cleaned up


def test_migration_on_load_persisted_on_next_write(hub):
    write_old(hub, OLD)
    raw = path(hub).read_text(encoding="utf-8")
    check_migrated(hub.get_project("demo")["phases"])
    check_migrated(hub.list_projects()[0]["phases"])
    assert path(hub).read_text(encoding="utf-8") == raw  # reading never writes
    hub.update_project("demo", next_step="go")
    check_migrated(json.loads(path(hub).read_text(encoding="utf-8"))["phases"])
    p = hub.get_project("demo")
    assert autonomy_line(p) == "Autonomous work allowed up to phase 0 (phase 1 is gated)"
    assert [w["phase_id"] for w in waiting([p])] == ["p0", "p2"]  # p3 is done: never waiting


def test_migrate_gates_rewrites_every_file_once(hub):
    write_old(hub, OLD)
    hub.create_project("other", "Other", "", phases=["A"])
    before = json.loads(path(hub).read_text(encoding="utf-8"))
    assert hub.migrate_gates() == {"projects": 2, "migrated": 1}
    after = json.loads(path(hub).read_text(encoding="utf-8"))
    check_migrated(after["phases"])
    assert after["updated_at"] == before["updated_at"]
    assert hub.migrate_gates() == {"projects": 2, "migrated": 0}  # idempotent
    assert "[espera a Danny] look" in (hub.dir / "BIBLIA.md").read_text(encoding="utf-8")
    assert not list(hub.dir.rglob("*.tmp"))


def test_migrate_gates_cli(hub):
    write_old(hub, OLD)
    env = dict(os.environ, PROJECT_HUB_DATA=str(hub.dir))
    out = subprocess.run([sys.executable, "-m", "project_hub.cli", "migrate-gates"], env=env,
                         capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "migrate-gates: 1 of 1 project files rewritten"
    check_migrated(json.loads(path(hub).read_text(encoding="utf-8"))["phases"])


def test_old_session_writes_after_migration_win(hub):
    """A session still on the old code only sees gate/gate_approved: its approvals and re-gating are picked up."""
    p0, p1, _ = ids(hub)
    hub.set_gate("demo", p0, "check")
    hub.set_gate("demo", p1, "check")
    hub.resolve_gate("demo", p1, "sigue", "ok")
    data = json.loads(path(hub).read_text(encoding="utf-8"))
    data["phases"][0].update(gate_approved=True, gate_approved_by="chat", gate_approved_words="vale",
                             gate_approved_at="2030-01-01T08:00:00+00:00")  # old approve_gate
    data["phases"][1].update(gate="manual_test", gate_approved=False, gate_reason="test it")  # old agent tightened
    path(hub).write_text(json.dumps(data), encoding="utf-8")
    a, b = hub.get_project("demo")["phases"][:2]
    assert (a["gate_state"], a["gate_resolved_action"], a["gate_resolved_words"]) == ("continue", "sigue", "vale")
    assert "gate_approved_by" not in a
    assert (b["gate_state"], b["gate_reason"], b["gate"], b["gate_resolved_action"]) == ("waiting", "test it", "review", None)


# --- texts -----------------------------------------------------------------------


def test_autonomy_line(hub):
    p0, p1, p2 = ids(hub)
    line = lambda: autonomy_line(hub.get_project("demo"))
    assert line() == "Autonomous work allowed up to phase 3 (Ship)"
    hub.set_gate("demo", p1, "r")
    assert line() == "Autonomous work allowed up to phase 1 (Plan)"
    hub.set_gate("demo", p0, "r")
    assert line() == "Autonomous work allowed up to phase 0 (phase 1 is gated)"
    hub.resolve_gate("demo", p0, "sigue", "sigue")
    assert line() == "Autonomous work allowed up to phase 1 (Plan)"
    hub.resolve_gate("demo", p1, "hecho", "hecho")
    assert line() == "Autonomous work allowed up to phase 3 (Ship)"
    assert autonomy_line({"phases": []}) == "Autonomous work allowed up to phase 0"


def test_waiting_one_entry_per_gate_most_urgent_first(hub):
    h = hub
    h.create_project("aaa", "Aaa", "", phases=["One", "Two"])
    h.create_project("zzz", "Zzz", "", phases=["One", "Two"])
    a0, a1 = ids(h, "aaa")
    z0, z1 = ids(h, "zzz")
    d0, d1, _ = ids(h)
    h.set_gate("demo", d1, "later")  # behind Plan: not urgent
    h.set_gate("aaa", a1, "test it")
    h.set_phase_status("aaa", a0, "done")
    h.set_gate("zzz", z0, "check", by="chat")
    h.set_gate("zzz", z1, "second")
    w = waiting(h.list_projects())
    assert w == [
        {"project_id": "aaa", "project_name": "Aaa", "phase_id": a1, "phase_name": "Two", "reason": "test it", "set_by": "agent"},
        {"project_id": "zzz", "project_name": "Zzz", "phase_id": z0, "phase_name": "One", "reason": "check", "set_by": "chat"},
        {"project_id": "demo", "project_name": "Demo", "phase_id": d1, "phase_name": "Build", "reason": "later", "set_by": "agent"},
        {"project_id": "zzz", "project_name": "Zzz", "phase_id": z1, "phase_name": "Two", "reason": "second", "set_by": "agent"},
    ]
    h.resolve_gate("zzz", z0, "sigue", "sigue")
    assert [x["phase_id"] for x in waiting(h.list_projects())] == [a1, d1, z1]


def test_biblia_shows_gates(hub):
    p0, p1, _ = ids(hub)
    text = (hub.dir / "BIBLIA.md").read_text(encoding="utf-8")
    assert "## Waiting for Danny\n\n(none)" in text
    hub.set_gate("demo", p0, "check the plan")
    hub.set_gate("demo", p1, "on device")
    hub.resolve_gate("demo", p1, "sigue", "dale")
    text = (hub.dir / "BIBLIA.md").read_text(encoding="utf-8")
    assert text.index("## Active resources") < text.index("## Waiting for Danny") < text.index("## Demo")
    assert f"1. [todo] Plan (id {p0}) <- current [espera a Danny] check the plan" in text
    assert f"2. [todo] Build (id {p1}) [resuelto vía chat (sigue): «dale»]" in text
    assert f"- Demo (`demo`): phase Plan (id {p0}) [espera a Danny] check the plan" in text
    assert "- Autonomous work allowed up to phase 0 (phase 1 is gated)" in text


def test_gate_label_for_resolution_without_words():
    assert gate_label({"gate_state": "continue", "gate_resolved_action": "sigue"}) == "[resuelto (sigue)]"
    assert gate_label({"status": "todo"}) == ""
