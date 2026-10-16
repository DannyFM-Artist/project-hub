import json
import os
import subprocess
import sys
import textwrap
import time
from datetime import datetime, timedelta, timezone

import pytest

from project_hub import hub as hub_module
from project_hub.hub import Hub, HubError


@pytest.fixture
def hub(tmp_path):
    h = Hub(tmp_path / "data")
    h.create_project("p1", "P1", "")
    h.create_project("p2", "P2", "")
    return h


def leases_file(h):
    return json.loads((h.dir / "resources" / "leases.json").read_text(encoding="utf-8"))


def test_claim_granted(hub):
    r = hub.claim_resource("gpu", "p1", "training", ttl_minutes=10)
    assert r["status"] == "granted"
    lease = r["lease"]
    assert (lease["resource"], lease["project_id"], lease["purpose"]) == ("gpu", "p1", "training")
    acquired, expires = (datetime.fromisoformat(lease[k]) for k in ("acquired_at", "expires_at"))
    assert expires - acquired == timedelta(minutes=10)
    assert leases_file(hub) == [lease]
    assert hub.list_resources() == [lease]


def test_busy_returns_holder_and_writes_nothing(hub):
    held = hub.claim_resource("gpu", "p1", "training")["lease"]
    files = [hub.dir / "resources" / "leases.json", hub.dir / "BIBLIA.md"]
    before = [(f.read_bytes(), f.stat().st_mtime_ns) for f in files]
    r = hub.claim_resource("gpu", "p2", "render")
    assert r == {"status": "busy", "lease": held}
    assert [(f.read_bytes(), f.stat().st_mtime_ns) for f in files] == before


def test_renew_keeps_acquired_at(hub, monkeypatch):
    t0 = datetime(2030, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(hub_module, "_utcnow", lambda: t0)
    first = hub.claim_resource("gpu", "p1", "a", ttl_minutes=5)["lease"]
    monkeypatch.setattr(hub_module, "_utcnow", lambda: t0 + timedelta(minutes=3))
    r = hub.claim_resource("gpu", "p1", "b", ttl_minutes=20)
    assert r["status"] == "renewed"
    assert r["lease"]["acquired_at"] == first["acquired_at"]
    assert r["lease"]["purpose"] == "b"
    assert r["lease"]["expires_at"] == (t0 + timedelta(minutes=23)).isoformat(timespec="seconds")
    assert leases_file(hub) == [r["lease"]]


def test_release(hub):
    hub.claim_resource("gpu", "p1", "x")
    lease = hub.release_resource("gpu", "p1")
    assert lease["resource"] == "gpu"
    assert hub.list_resources() == [] and leases_file(hub) == []
    assert hub.claim_resource("gpu", "p2", "y")["status"] == "granted"


def test_release_by_wrong_project(hub):
    hub.claim_resource("gpu", "p1", "x")
    with pytest.raises(HubError, match="p1"):
        hub.release_resource("gpu", "p2")
    assert hub.list_resources()[0]["project_id"] == "p1"


def test_release_when_not_claimed(hub):
    with pytest.raises(HubError, match="resource 'gpu' is not claimed"):
        hub.release_resource("gpu", "p1")
    with pytest.raises(HubError, match="^unknown resource"):
        hub.force_release("gpu")


def test_force_release(hub):
    hub.claim_resource("gpu", "p1", "x")
    assert hub.force_release(" GPU")["project_id"] == "p1"
    assert hub.list_resources() == []


def test_name_normalization(hub):
    hub.claim_resource("  GPU ", "p1", "x")
    assert hub.list_resources()[0]["resource"] == "gpu"
    assert hub.claim_resource("gpu", "p2", "y")["status"] == "busy"
    assert hub.claim_resource("Gpu", "p1", "z")["status"] == "renewed"
    hub.release_resource("gPU", "p1")


@pytest.mark.parametrize("kwargs", [
    {"project_id": "nope"},
    {"project_id": "Bad Id"},
    {"resource": "   "},
    {"resource": None},
    {"purpose": None},
    {"ttl_minutes": 0},
    {"ttl_minutes": 1441},
    {"ttl_minutes": 1.5},
    {"ttl_minutes": True},
    {"ttl_minutes": "30"},
])
def test_claim_validation(hub, kwargs):
    args = {"resource": "gpu", "project_id": "p1", "purpose": "x", "ttl_minutes": 30, **kwargs}
    with pytest.raises(HubError):
        hub.claim_resource(**args)
    assert hub.list_resources() == []


def test_unknown_project_message(hub):
    with pytest.raises(HubError, match="^unknown project"):
        hub.claim_resource("gpu", "nope", "x")
    with pytest.raises(HubError, match="^unknown project"):
        hub.release_resource("gpu", "nope")


def test_expiry(hub, monkeypatch):
    t0 = datetime(2030, 1, 1, tzinfo=timezone.utc)
    now = [t0]
    monkeypatch.setattr(hub_module, "_utcnow", lambda: now[0])
    hub.claim_resource("gpu", "p1", "x", ttl_minutes=30)
    hub.claim_resource("device:cam", "p1", "x", ttl_minutes=30)
    now[0] = t0 + timedelta(minutes=30)  # expires_at <= now is free
    assert hub.list_resources() == []
    assert len(leases_file(hub)) == 2  # reads only filter
    r = hub.claim_resource("gpu", "p2", "y")
    assert r["status"] == "granted" and r["lease"]["acquired_at"] == now[0].isoformat(timespec="seconds")
    assert [(l["resource"], l["project_id"]) for l in leases_file(hub)] == [("gpu", "p2")]  # expired one dropped on write
    with pytest.raises(HubError, match="not claimed"):
        hub.release_resource("device:cam", "p1")


def test_sorted_by_resource(hub):
    for name in ("repo:zeta", "gpu", "device:cam"):
        hub.claim_resource(name, "p1", "x")
    assert [l["resource"] for l in hub.list_resources()] == ["device:cam", "gpu", "repo:zeta"]
    assert [l["resource"] for l in leases_file(hub)] == ["device:cam", "gpu", "repo:zeta"]


def test_biblia_active_resources(hub):
    biblia = hub.dir / "BIBLIA.md"
    text = biblia.read_text(encoding="utf-8")
    assert "## Active resources\n\n(none)" in text
    hub.claim_resource("path:C:\\work|x", "p1", "nightly render")
    text = biblia.read_text(encoding="utf-8")
    assert text.index("## Index") < text.index("## Active resources") < text.index("## P1")
    assert "| path:c:\\work\\|x | p1 | nightly render |" in text
    hub.release_resource("path:c:\\work|x", "p1")
    assert "## Active resources\n\n(none)" in biblia.read_text(encoding="utf-8")


def test_two_processes_race(hub):
    rounds = 10
    code = textwrap.dedent("""
        import sys, time
        from project_hub.hub import Hub
        hub = Hub()
        start = float(sys.argv[2])
        for i in range(int(sys.argv[3])):
            time.sleep(max(0, start + i * 0.2 - time.time()))  # both processes hit each round together
            print(i, hub.claim_resource(f"race-{i}", sys.argv[1], "race")["status"], flush=True)
    """)
    env = dict(os.environ, PROJECT_HUB_DATA=str(hub.dir))
    start = time.time() + 2  # after both interpreters have started
    procs = [subprocess.Popen([sys.executable, "-c", code, pid, str(start), str(rounds)], env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for pid in ("p1", "p2")]
    results = {}
    for pid, proc in zip(("p1", "p2"), procs):
        out, err = proc.communicate(timeout=180)
        assert proc.returncode == 0, err
        for line in out.splitlines():
            i, status = line.split()
            results.setdefault(int(i), {})[pid] = status
    assert sorted(results) == list(range(rounds))
    holders = {l["resource"]: l["project_id"] for l in hub.list_resources()}
    for i, by_pid in results.items():
        assert sorted(by_pid.values()) == ["busy", "granted"], (i, by_pid)
        assert by_pid[holders[f"race-{i}"]] == "granted"
    assert len(leases_file(hub)) == rounds
    assert not list(hub.dir.rglob("*.tmp"))
