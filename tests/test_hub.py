import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from project_hub.hub import Hub, HubError, data_dir


@pytest.fixture
def hub(tmp_path):
    return Hub(tmp_path / "data")


def test_data_dir_from_env(tmp_path, monkeypatch):
    monkeypatch.setenv("PROJECT_HUB_DATA", str(tmp_path / "x"))
    assert data_dir() == (tmp_path / "x").resolve()
    assert Hub().dir == (tmp_path / "x").resolve()


def test_data_dir_default_is_home_not_cwd(tmp_path, monkeypatch):
    monkeypatch.delenv("PROJECT_HUB_DATA")
    monkeypatch.chdir(tmp_path)
    assert data_dir() == Path.home() / "project-hub-data"
    assert Path.home() == tmp_path / "home"  # conftest points HOME at a temp folder
    assert Hub().dir == tmp_path / "home" / "project-hub-data"


def test_data_dir_rejects_relative_env(monkeypatch):
    monkeypatch.setenv("PROJECT_HUB_DATA", "data")
    with pytest.raises(HubError, match="absolute"):
        data_dir()


def test_data_dir_expands_user(monkeypatch):
    monkeypatch.setenv("PROJECT_HUB_DATA", "~/hub")
    assert data_dir() == (Path.home() / "hub").resolve()


def test_gitignore_created_on_first_write(hub):
    assert not (hub.dir / ".gitignore").exists()
    hub.create_project("app", "App", "")
    assert (hub.dir / ".gitignore").read_text(encoding="utf-8") == ".lock\n*.tmp\nlogs/\n"


def test_gitignore_merges_with_existing(tmp_path):
    folder = tmp_path / "data"
    folder.mkdir()
    (folder / ".gitignore").write_text("# mine\n*.bak\n*.tmp", encoding="utf-8")  # no trailing newline
    Hub(folder).create_project("app", "App", "")
    Hub(folder).create_project("app2", "App 2", "")  # a second process-like instance adds nothing more
    assert (folder / ".gitignore").read_text(encoding="utf-8") == "# mine\n*.bak\n*.tmp\n.lock\nlogs/\n"


def test_create_and_get(hub):
    p = hub.create_project("app", "App", "An app", phases=["Design", "Build"])
    assert p["status"] == "active" and p["next_step"] == "" and p["items"] == [] and p["decisions"] == []
    assert [ph["name"] for ph in p["phases"]] == ["Design", "Build"]
    assert all(ph["status"] == "todo" and ph["notes"] == "" and len(ph["id"]) == 8 for ph in p["phases"])
    assert p["updated_at"].endswith("+00:00")
    got = hub.get_project("app")
    assert got["unread_messages"] == []
    assert got["name"] == "App" and got["repo_path"] is None
    # stored JSON is pretty, sorted, newline-terminated
    text = (hub.dir / "projects" / "app.json").read_text(encoding="utf-8")
    assert text.endswith("}\n") and text == json.dumps(json.loads(text), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def test_returns_copies(hub):
    p = hub.create_project("app", "App", "")
    p["name"] = "mutated"
    assert hub.get_project("app")["name"] == "App"


def test_update_ops(hub, tmp_path):
    hub.create_project("app", "App", "desc", phases=["One"])
    p = hub.update_project("app", status="paused", next_step="ship it", description="new", repo_path=str(tmp_path))
    assert (p["status"], p["next_step"], p["description"], p["repo_path"]) == ("paused", "ship it", "new", str(tmp_path))
    assert hub.update_project("app", repo_path="")["repo_path"] is None

    ph = hub.add_phase("app", "Zero", position=0)
    hub.add_phase("app", "Two")
    assert [x["name"] for x in hub.get_project("app")["phases"]] == ["Zero", "One", "Two"]
    ph = hub.set_phase_status("app", ph["id"], "done", notes="finished")
    assert (ph["status"], ph["notes"]) == ("done", "finished")

    it = hub.add_item("app", "bug", "Crash", "on start")
    assert (it["status"], it["details"]) == ("open", "on start") and "created_at" in it
    it = hub.update_item("app", it["id"], status="planned", type="idea", title="Crash2")
    assert (it["status"], it["type"], it["title"], it["details"]) == ("planned", "idea", "Crash2", "on start")

    d = hub.log_decision("app", "Use JSON", "simple")
    assert d["decision"] == "Use JSON" and d["date"].endswith("+00:00")
    assert hub.get_project("app")["decisions"] == [d]

    assert [p["id"] for p in hub.list_projects()] == ["app"]
    assert hub.list_projects(status="active") == []
    assert len(hub.list_projects(status="paused")) == 1


@pytest.mark.parametrize("bad_id", ["", "Bad", "-x", "a b", "../x", "a/b", None, 5])
def test_bad_project_ids(hub, bad_id):
    with pytest.raises(HubError, match="invalid project id"):
        hub.create_project(bad_id, "N", "")


def test_validation_errors(hub):
    hub.create_project("app", "App", "")
    with pytest.raises(HubError, match="already exists"):
        hub.create_project("app", "Again", "")
    with pytest.raises(HubError, match="reserved"):
        hub.create_project("all", "All", "")
    with pytest.raises(HubError, match="absolute"):
        hub.create_project("rel", "Rel", "", repo_path="relative/path")
    with pytest.raises(HubError, match="unknown project"):
        hub.get_project("nope")
    with pytest.raises(HubError, match="allowed: active, paused, parked, done"):
        hub.update_project("app", status="sleeping")
    with pytest.raises(HubError, match="allowed: active"):
        hub.list_projects(status="x")
    with pytest.raises(HubError, match="unknown phase"):
        hub.set_phase_status("app", "deadbeef", "done")
    ph = hub.add_phase("app", "P")
    with pytest.raises(HubError, match="allowed: todo, in_progress, done"):
        hub.set_phase_status("app", ph["id"], "finished")
    with pytest.raises(HubError, match="position"):
        hub.add_phase("app", "Q", position=5)
    with pytest.raises(HubError, match="allowed: idea, future_request, bug"):
        hub.add_item("app", "feature", "t")
    with pytest.raises(HubError, match="title"):
        hub.add_item("app", "idea", "  ")
    with pytest.raises(HubError, match="unknown item"):
        hub.update_item("app", "deadbeef", status="done")
    it = hub.add_item("app", "idea", "t")
    with pytest.raises(HubError, match="allowed: open, planned, done, discarded"):
        hub.update_item("app", it["id"], status="closed")
    with pytest.raises(HubError, match="allowed: message, task, report"):
        hub.post_message("app", "note", "t", "b")
    with pytest.raises(HubError, match="unknown project"):
        hub.post_message("nope", "task", "t", "b")
    with pytest.raises(HubError, match="unknown project"):
        hub.post_message("app", "task", "t", "b", from_project="nope")
    with pytest.raises(HubError, match="unknown message"):
        hub.mark_message("deadbeef", "read")
    m = hub.post_message("app", "task", "t", "b")
    with pytest.raises(HubError, match="allowed: unread, read, done"):
        hub.mark_message(m["id"], "gone")
    # failed operations left nothing half-written
    p = hub.get_project("app")
    assert len(p["phases"]) == 1 and len(p["items"]) == 1


def test_inbox_and_all_messages(hub):
    hub.create_project("a", "A", "")
    hub.create_project("b", "B", "")
    m1 = hub.post_message("a", "task", "Do it", "body", from_project="b")
    m2 = hub.post_message("all", "message", "Broadcast", "hi")
    assert m2["to_project"] == "all" and m2["from_project"] == "user" and m2["status"] == "unread"
    assert [m["id"] for m in hub.read_inbox("a")] == [m1["id"], m2["id"]]
    assert [m["id"] for m in hub.read_inbox("b")] == [m2["id"]]
    assert len(hub.get_project("a")["unread_messages"]) == 2
    assert len(hub.get_project("b")["unread_messages"]) == 1
    # stored once
    lines = (hub.dir / "inbox" / "messages.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2

    assert hub.mark_message(m1["id"], "done")["status"] == "done"
    assert [m["id"] for m in hub.read_inbox("a")] == [m2["id"]]
    assert len(hub.read_inbox("a", unread_only=False)) == 2
    hub.mark_message(m2["id"], "read")  # marks the broadcast for everyone
    assert hub.read_inbox("b") == []
    assert hub.get_project("b")["unread_messages"] == []


def test_unicode_roundtrip(hub):
    hub.create_project("app", "Café ✓", "ünïcode")
    hub.post_message("app", "report", "Résumé", "naïve")
    assert hub.get_project("app")["name"] == "Café ✓"
    assert hub.read_inbox("app")[0]["title"] == "Résumé"
    assert "Café ✓" in (hub.dir / "BIBLIA.md").read_text(encoding="utf-8")
    body = "line\u2028sep\u2029para\x85nel"
    hub.post_message("app", "message", "pasted", body)
    assert hub.read_inbox("app")[-1]["body"] == body


def test_missing_data_folder_reads(tmp_path):
    hub = Hub(tmp_path / "nothing")
    assert hub.list_projects() == []
    assert hub.find_project_for_path(tmp_path) is None
    with pytest.raises(HubError, match="unknown project"):
        hub.get_project("x")
    assert not (tmp_path / "nothing").exists()


def test_concurrent_writes_two_processes(tmp_path):
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
        assert out == b""  # nothing printed to stdout
    project = json.loads((data / "projects" / "shared.json").read_text(encoding="utf-8"))
    titles = {it["title"] for it in project["items"]}
    assert titles == {f"{t}-{i}" for t in ("p1", "p2") for i in range(30)}
    assert len({it["id"] for it in project["items"]}) == 60
    assert not list(data.rglob("*.tmp"))
    assert "Unread: 0" in (data / "BIBLIA.md").read_text(encoding="utf-8")


def test_biblia_regenerated(hub, tmp_path):
    biblia = hub.dir / "BIBLIA.md"
    hub.create_project("app", "My App", "Does things", repo_path=str(tmp_path), phases=["Design", "Build"])
    text = biblia.read_text(encoding="utf-8")
    assert "| My App | app | active | Design (todo) | - |" in text

    p = hub.get_project("app")
    hub.set_phase_status("app", p["phases"][0]["id"], "done", notes="wireframes ok")
    hub.set_phase_status("app", p["phases"][1]["id"], "in_progress")
    hub.update_project("app", next_step="write tests")
    bug = hub.add_item("app", "bug", "Crash on save", "stack trace")
    done = hub.add_item("app", "idea", "Finished idea")
    hub.update_item("app", done["id"], status="done")
    for i in range(6):
        hub.log_decision("app", f"Decision {i}", f"reason {i}")
    text = biblia.read_text(encoding="utf-8")
    assert "| My App | app | active | Build (in_progress) | write tests |" in text
    assert "## My App (`app`)" in text
    assert "Does things" in text and str(tmp_path) in text
    assert "[done] Design" in text and "wireframes ok" in text
    assert "[in_progress] Build" in text and "<- current" in text
    assert "**bug**" in text and f"- [open] Crash on save (id {bug['id']}): stack trace" in text
    assert "Finished idea" not in text
    assert "Decision 5 - because reason 5" in text and "Decision 1" in text and "Decision 0" not in text
    assert "Unread: 0" in text

    # inbox writes regenerate it too
    m = hub.post_message("app", "task", "Review PR", "please")
    text = biblia.read_text(encoding="utf-8")
    assert "Unread: 1" in text and "[task] Review PR" in text
    hub.post_message("all", "message", "Hello all", "")
    assert "Unread: 2" in biblia.read_text(encoding="utf-8")
    hub.mark_message(m["id"], "read")
    text = biblia.read_text(encoding="utf-8")
    assert "Unread: 1" in text and "Review PR" not in text


def test_biblia_escapes_table_cells(hub):
    hub.create_project("app", "A|B", "")
    hub.update_project("app", next_step="line1\nline2 | x")
    assert "| A\\|B | app | active | - | line1 line2 \\| x |" in (hub.dir / "BIBLIA.md").read_text(encoding="utf-8")


# --- find_project_for_path ----------------------------------------------------

@pytest.fixture
def repos(hub, tmp_path):
    outer = tmp_path / "work" / "outer"
    inner = outer / "packages" / "inner"
    inner.mkdir(parents=True)
    hub.create_project("outer", "Outer", "", repo_path=str(outer))
    hub.create_project("inner", "Inner", "", repo_path=str(inner))
    hub.create_project("norepo", "No repo", "")
    return outer, inner


def test_find_exact_match(hub, repos):
    outer, _ = repos
    assert hub.find_project_for_path(outer)["id"] == "outer"


def test_find_subdirectory(hub, repos):
    outer, _ = repos
    found = hub.find_project_for_path(outer / "src" / "deep")
    assert found["id"] == "outer" and found["unread_messages"] == []


def test_find_nested_longest_wins(hub, repos):
    _, inner = repos
    assert hub.find_project_for_path(inner)["id"] == "inner"
    assert hub.find_project_for_path(inner / "lib")["id"] == "inner"


def test_find_no_match(hub, repos, tmp_path):
    outer, _ = repos
    assert hub.find_project_for_path(tmp_path / "work") is None
    assert hub.find_project_for_path(tmp_path / "work" / "outer-sibling") is None  # prefix but not inside


def test_find_skips_project_without_repo_path(hub, tmp_path):
    hub.create_project("norepo", "No repo", "")
    assert hub.find_project_for_path(tmp_path) is None


def test_find_includes_unread(hub, repos):
    outer, _ = repos
    hub.post_message("outer", "task", "Do X", "")
    assert [m["title"] for m in hub.find_project_for_path(outer)["unread_messages"]] == ["Do X"]


@pytest.mark.skipif(os.name != "nt", reason="case-insensitive paths only on Windows")
def test_find_case_insensitive_on_windows(hub, tmp_path):
    repo = tmp_path / "MixedCase" / "Repo"
    repo.mkdir(parents=True)
    hub.create_project("mixed", "Mixed", "", repo_path=str(repo).upper())
    assert hub.find_project_for_path(Path(str(repo).lower()) / "sub")["id"] == "mixed"
