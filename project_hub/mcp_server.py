"""MCP stdio server: thin text-returning wrappers over Hub. Never print to stdout (protocol channel)."""

from functools import wraps

from mcp.server.mcpserver import MCPServer

from .biblia import current_phase
from .hub import Hub, HubError

mcp = MCPServer("project-hub")
hub = Hub()  # one Hub per process; PROJECT_HUB_DATA read at import


def tool(fn):
    """Register fn as an MCP tool; HubError becomes "Error: <message>"."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except HubError as e:
            return f"Error: {e}"

    mcp.tool()(wrapper)
    return wrapper


def _msg(m):
    return f"[{m['id']}] {m['kind']} from {m['from_project']} to {m['to_project']} ({m['status']}): {m['title']}\n    {m['body']}"


@tool
def list_projects(status: str | None = None) -> str:
    """List projects, one per line: id | name | status | current phase | next step | N unread.
    status filter (optional): active, paused, parked, done."""
    projects = hub.list_projects(status)
    lines = []
    for p in projects:
        cur = current_phase(p)
        unread = len(hub.read_inbox(p["id"]))
        lines.append(f"{p['id']} | {p['name']} | {p['status']} | {cur['name'] + ' (' + cur['status'] + ')' if cur else '-'}"
                     f" | {p['next_step'] or '-'} | {unread} unread")
    return "\n".join(lines) or "(no projects)"


@tool
def get_project(project_id: str) -> str:
    """Full project: phases, items, recent decisions and unread messages, all with ids."""
    p = hub.get_project(project_id)
    out = [f"{p['id']} | {p['name']} | {p['status']}", f"Description: {p['description'] or '-'}",
           f"Repo: {p['repo_path'] or '-'}", f"Next step: {p['next_step'] or '-'}", "Phases:"]
    out += [f"  [{ph['id']}] {ph['status']}: {ph['name']}" + (f" - {ph['notes']}" if ph["notes"] else "") for ph in p["phases"]] or ["  (none)"]
    out.append("Items:")
    out += [f"  [{i['id']}] {i['type']} {i['status']}: {i['title']}" + (f" - {i['details']}" if i["details"] else "") for i in p["items"]] or ["  (none)"]
    out.append("Recent decisions:")
    out += [f"  {d['date']}: {d['decision']} - because {d['reason']}" for d in p["decisions"][-5:]] or ["  (none)"]
    out.append(f"Unread messages: {len(p['unread_messages'])}")
    out += ["  " + _msg(m) for m in p["unread_messages"]]
    return "\n".join(out)


@tool
def create_project(id: str, name: str, description: str, repo_path: str | None = None, phases: list[str] | None = None) -> str:
    """Create a project. id: lowercase slug (a-z, 0-9, '-'); repo_path: absolute path; phases: ordered phase names.
    Limits (characters): description 200, each phase name 60; longer text is rejected, so keep it short."""
    p = hub.create_project(id, name, description, repo_path, phases)
    return f"Created project {p['id']} with {len(p['phases'])} phase(s)"


@tool
def update_project(project_id: str, status: str | None = None, description: str | None = None,
                   next_step: str | None = None, repo_path: str | None = None) -> str:
    """Update project fields. status: active, paused, parked, done. repo_path "" clears it.
    Limits (characters): description 200, next_step 160; longer text is rejected, so keep it short."""
    p = hub.update_project(project_id, status=status, description=description, next_step=next_step, repo_path=repo_path)
    return f"Updated project {p['id']} (status {p['status']})"


@tool
def add_phase(project_id: str, name: str, position: int | None = None) -> str:
    """Add a phase (status todo) at 0-based position, default at the end. Name limit: 60 characters."""
    ph = hub.add_phase(project_id, name, position)
    return f"Added phase {ph['id']}: {ph['name']}"


@tool
def set_phase_status(project_id: str, phase_id: str, status: str, notes: str | None = None) -> str:
    """Set a phase status: todo, in_progress, done. Optional notes replace the phase notes (limit 240 characters)."""
    ph = hub.set_phase_status(project_id, phase_id, status, notes)
    return f"Phase {ph['id']} is now {ph['status']}"


@tool
def update_phase(project_id: str, phase_id: str, name: str | None = None, notes: str | None = None) -> str:
    """Rename a phase and/or replace its notes; status is unchanged. Limits (characters): name 60, notes 240."""
    ph = hub.update_phase(project_id, phase_id, name=name, notes=notes)
    return f"Updated phase {ph['id']}: {ph['name']}"


@tool
def delete_phase(project_id: str, phase_id: str) -> str:
    """Delete a phase from a project."""
    ph = hub.delete_phase(project_id, phase_id)
    return f"Deleted phase {ph['id']}: {ph['name']}"


@tool
def add_item(project_id: str, type: str, title: str, details: str = "") -> str:
    """Add an item (status open). type: idea, future_request, bug. Title limit: 100 characters."""
    i = hub.add_item(project_id, type, title, details)
    return f"Added {i['type']} {i['id']}: {i['title']}"


@tool
def update_item(project_id: str, item_id: str, status: str | None = None, type: str | None = None,
                title: str | None = None, details: str | None = None) -> str:
    """Update an item. status: open, planned, done, discarded. type: idea, future_request, bug.
    Title limit: 100 characters."""
    i = hub.update_item(project_id, item_id, status=status, type=type, title=title, details=details)
    return f"Updated item {i['id']} ({i['type']}, {i['status']}): {i['title']}"


@tool
def log_decision(project_id: str, decision: str, reason: str) -> str:
    """Record a decision and why it was made."""
    d = hub.log_decision(project_id, decision, reason)
    return f"Logged decision on {project_id}: {d['decision']}"


@tool
def post_message(to_project: str, kind: str, title: str, body: str, from_project: str = "user") -> str:
    """Post to a project inbox (to_project may be "all"). kind: message, task, report. from_project: a project id or "user"."""
    m = hub.post_message(to_project, kind, title, body, from_project)
    return f"Posted {m['kind']} {m['id']} to {m['to_project']}"


@tool
def read_inbox(project_id: str, unread_only: bool = True) -> str:
    """Messages addressed to a project (and "all"). unread_only defaults to true."""
    msgs = hub.read_inbox(project_id, unread_only)
    return "\n".join(_msg(m) for m in msgs) or "(no messages)"


@tool
def mark_message(message_id: str, status: str) -> str:
    """Set a message status: unread, read, done."""
    m = hub.mark_message(message_id, status)
    return f"Message {m['id']} is now {m['status']}"


def _lease(l):
    return f"{l['resource']} | holder {l['project_id']} | purpose {l['purpose'] or '-'} | expires_at {l['expires_at']}"


@tool
def claim_resource(resource: str, project_id: str, purpose: str, ttl_minutes: int = 30) -> str:
    """Claim exclusive use of a shared resource before using it; never waits. ttl_minutes 1-1440 (default 30).
    Resource names: gpu, device:<name>, repo:<name>, path:<absolute path> (case-insensitive).
    Result "granted" or "renewed" (same project claiming again extends it): go ahead, release when done.
    Result "busy": another project holds it - do not use it, retry later."""
    r = hub.claim_resource(resource, project_id, purpose, ttl_minutes)
    if r["status"] == "busy":
        return f"busy: {_lease(r['lease'])} - do not use it, retry later"
    return f"{r['status']}: {_lease(r['lease'])}"


@tool
def release_resource(resource: str, project_id: str) -> str:
    """Release a resource this project claimed. Resource names: gpu, device:<name>, repo:<name>, path:<absolute path>.
    A resource held by another project is busy: do not use it, retry later."""
    l = hub.release_resource(resource, project_id)
    return f"released: {l['resource']} (was held by {l['project_id']})"


@tool
def list_resources() -> str:
    """Active resource leases, one per line: resource | holder | purpose | expires_at.
    Resource names: gpu, device:<name>, repo:<name>, path:<absolute path>. A listed resource held by
    another project is busy: do not use it, retry later."""
    return "\n".join(_lease(l) for l in hub.list_resources()) or "(no active resources)"


def main():
    mcp.run()


if __name__ == "__main__":
    main()
