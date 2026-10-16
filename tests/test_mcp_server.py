import json
import sys

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

NAMES = {"list_projects", "get_project", "create_project", "update_project", "add_phase", "set_phase_status", "update_phase", "delete_phase",
         "add_item", "update_item", "log_decision", "post_message", "read_inbox", "mark_message",
         "claim_resource", "release_resource", "list_resources"}


def run_session(tmp_path, steps):
    async def go():
        params = StdioServerParameters(command=sys.executable, args=["-m", "project_hub.mcp_server"],
                                       env={"PROJECT_HUB_DATA": str(tmp_path)})
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as s:
                await s.initialize()
                return await steps(s)

    return anyio.run(go)


def test_round_trip(tmp_path):
    async def steps(s):
        async def call(tool, /, **args):
            return (await s.call_tool(tool, args)).content[0].text

        out = {"tools": {t.name for t in (await s.list_tools()).tools}}
        out["create"] = await call("create_project", id="demo", name="Demo", description="d", phases=["One"])
        out["item"] = await call("add_item", project_id="demo", type="bug", title="Crash")
        out["msg"] = await call("post_message", to_project="demo", kind="task", title="Do it", body="now")
        out["get"] = await call("get_project", project_id="demo")
        out["list"] = await call("list_projects")
        out["bad"] = await call("get_project", project_id="nope")
        return out

    out = run_session(tmp_path, steps)
    assert out["tools"] == NAMES
    assert out["create"].startswith("Created project demo")
    assert "Crash" in out["get"] and "Do it" in out["get"] and "Unread messages: 1" in out["get"]
    assert "demo | Demo | active" in out["list"] and "1 unread" in out["list"]
    assert out["bad"].startswith("Error:")
    print(out["get"], out["list"], sep="\n")


def test_resources_round_trip(tmp_path):
    async def steps(s):
        async def call(tool, /, **args):
            return (await s.call_tool(tool, args)).content[0].text

        out = {}
        await call("create_project", id="a", name="A", description="")
        await call("create_project", id="b", name="B", description="")
        out["granted"] = await call("claim_resource", resource="GPU", project_id="a", purpose="training", ttl_minutes=10)
        out["busy"] = await call("claim_resource", resource="gpu", project_id="b", purpose="render")
        out["renewed"] = await call("claim_resource", resource="gpu", project_id="a", purpose="training 2")
        out["list"] = await call("list_resources")
        out["wrong"] = await call("release_resource", resource="gpu", project_id="b")
        out["release"] = await call("release_resource", resource="gpu", project_id="a")
        out["empty"] = await call("list_resources")
        out["bad_ttl"] = await call("claim_resource", resource="gpu", project_id="a", purpose="x", ttl_minutes=0)
        return out

    out = run_session(tmp_path, steps)
    assert out["granted"].startswith("granted: gpu | holder a | purpose training | expires_at ")
    assert out["busy"].startswith("busy: gpu | holder a | purpose training | expires_at ")
    assert out["busy"].endswith("do not use it, retry later")
    assert out["renewed"].startswith("renewed: gpu | holder a | purpose training 2")
    assert out["list"].startswith("gpu | holder a | purpose training 2 | expires_at ")
    assert out["wrong"].startswith("Error:") and "'a'" in out["wrong"]
    assert out["release"] == "released: gpu (was held by a)"
    assert out["empty"] == "(no active resources)"
    assert out["bad_ttl"].startswith("Error: ttl_minutes")
    print(*out.values(), sep="\n")


def test_phase_edit_round_trip(tmp_path):
    async def steps(s):
        async def call(tool, /, **args):
            return (await s.call_tool(tool, args)).content[0].text

        out = {}
        await call("create_project", id="demo", name="Demo", description="d", phases=["One", "Two"])
        ids = [ph["id"] for ph in json.loads((tmp_path / "projects" / "demo.json").read_text(encoding="utf-8"))["phases"]]
        out["ids"] = ids
        out["upd"] = await call("update_phase", project_id="demo", phase_id=ids[0], name="Uno", notes="n")
        out["none"] = await call("update_phase", project_id="demo", phase_id=ids[0])
        out["long"] = await call("update_phase", project_id="demo", phase_id=ids[0], notes="x" * 241)
        out["del"] = await call("delete_phase", project_id="demo", phase_id=ids[0])
        out["gone"] = await call("delete_phase", project_id="demo", phase_id=ids[0])
        out["get"] = await call("get_project", project_id="demo")
        return out

    out = run_session(tmp_path, steps)
    assert out["upd"] == f"Updated phase {out['ids'][0]}: Uno"
    assert out["none"].startswith("Error: nothing to update")
    assert out["long"].startswith("Error:") and "241" in out["long"] and "limit is 240" in out["long"]
    assert out["del"] == f"Deleted phase {out['ids'][0]}: Uno"
    assert out["gone"].startswith("Error: unknown phase id")
    assert "Uno" not in out["get"] and "Two" in out["get"]
