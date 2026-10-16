from pathlib import Path

import pytest

REAL_DEFAULT = Path.home() / "project-hub-data"  # captured before any test patches HOME


def _snapshot(folder):
    if not folder.exists():
        return None
    # logs/ is written by the running tray dashboard, never by tests
    return sorted((str(p), p.stat().st_mtime_ns) for p in folder.rglob("*") if "logs" not in p.relative_to(folder).parts)


@pytest.fixture(scope="session", autouse=True)
def real_data_folder_untouched():
    """Fail the run if any test created or modified the real ~/project-hub-data."""
    before = _snapshot(REAL_DEFAULT)
    yield
    assert _snapshot(REAL_DEFAULT) == before, f"a test touched the real data folder {REAL_DEFAULT}"


@pytest.fixture(autouse=True)
def isolated_data_folder(tmp_path, monkeypatch):
    """Every test (and every subprocess that inherits os.environ) uses a temporary data folder and home."""
    monkeypatch.setenv("PROJECT_HUB_DATA", str(tmp_path / "hub-data"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
