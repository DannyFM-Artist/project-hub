import os
import subprocess
import sys

from project_hub.hub import Hub


def run(cwd, data):
    env = {**os.environ, "PROJECT_HUB_DATA": str(data), "PYTHONIOENCODING": "utf-8"}
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


def test_no_match_is_silent(tmp_path):
    Hub(tmp_path / "data").create_project("demo", "Demo", "d", repo_path=str(tmp_path / "repo"))
    other = tmp_path / "other"
    other.mkdir()
    r = run(other, tmp_path / "data")
    assert (r.returncode, r.stdout) == (0, "")


def test_missing_data_folder_is_silent(tmp_path):
    r = run(tmp_path, tmp_path / "nope")
    assert (r.returncode, r.stdout) == (0, "")
