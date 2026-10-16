import sys

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

NAMES = {"list_projects", "get_project", "create_project", "update_project", "add_phase", "set_phase_status",
         "add_item", "update_item", "log_decision", "post_message", "read_inbox", "mark_message"}


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
