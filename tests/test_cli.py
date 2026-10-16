import os
import subprocess
import sys
from pathlib import Path

import project_hub
from project_hub.hub import Hub

SRC = str(Path(project_hub.__file__).resolve().parents[1])  # this checkout, not whatever is installed


def run(cwd, data):
    env = {**os.environ, "PROJECT_HUB_DATA": str(data), "PYTHONIOENCODING": "utf-8", "PYTHONPATH": SRC}
    return subprocess.run([sys.executable, "-m", "project_hub.cli", "session-start"],
                          cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8")


def test_match_prints_context(tmp_path):
    repo = tmp_path / "repo"
    (repo / "src" / "deep").mkdir(parents=True)
    hub = Hub(tmp_path / "data")
    hub.create_project("demo", "Demo App", "d", repo_path=str(repo), phases=["Build"])
    hub.update_project("demo", next_step="Ship it")
    hub.post_message("demo", "task", "Fix the thing", "b")
    r = run(repo / "src" / "deep", tmp_path / "data")
    assert r.returncode == 0
    for text in ("Demo App", "demo", "Build (todo)", "Ship it", "Unread inbox (1)", "Fix the thing"):
        assert text in r.stdout


def test_shows_gates_and_autonomy(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    hub = Hub(tmp_path / "data")
    hub.create_project("demo", "Demo", "d", repo_path=str(repo), phases=["Plan", "Build"])
    hub.add_phase("demo", "Ship")
    p0, p1, p2 = (ph["id"] for ph in hub.get_project("demo")["phases"])
    hub.set_gate("demo", p1, "Danny tests on device")
    hub.set_gate("demo", p2, "resolved")
    hub.resolve_gate("demo", p2, "sigue", "sigue")
    r = run(repo, tmp_path / "data")
    assert r.returncode == 0
    assert "Phase 2 waits for Danny: Danny tests on device" in r.stdout
    assert "Phase 3" not in r.stdout and "Gated phase" not in r.stdout
    assert "Autonomous work allowed up to phase 1 (Plan)" in r.stdout
    print(r.stdout)


def test_no_match_is_silent(tmp_path):
    Hub(tmp_path / "data").create_project("demo", "Demo", "d", repo_path=str(tmp_path / "repo"))
    other = tmp_path / "other"
    other.mkdir()
    r = run(other, tmp_path / "data")
    assert (r.returncode, r.stdout) == (0, "")


def test_missing_data_folder_is_silent(tmp_path):
    r = run(tmp_path, tmp_path / "nope")
    assert (r.returncode, r.stdout) == (0, "")
