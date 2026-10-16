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
    """Create a project. id: lowercase slug (a-z, 0-9, '-'); repo_path: absolute path; phases: ordered phase names."""
    p = hub.create_project(id, name, description, repo_path, phases)
    return f"Created project {p['id']} with {len(p['phases'])} phase(s)"


@tool
def update_project(project_id: str, status: str | None = None, description: str | None = None,
                   next_step: str | None = None, repo_path: str | None = None) -> str:
    """Update project fields. status: active, paused, parked, done. repo_path "" clears it."""
    p = hub.update_project(project_id, status=status, description=description, next_step=next_step, repo_path=repo_path)
    return f"Updated project {p['id']} (status {p['status']})"


@tool
def add_phase(project_id: str, name: str, position: int | None = None) -> str:
    """Add a phase (status todo) at 0-based position, default at the end."""
    ph = hub.add_phase(project_id, name, position)
    return f"Added phase {ph['id']}: {ph['name']}"


@tool
def set_phase_status(project_id: str, phase_id: str, status: str, notes: str | None = None) -> str:
    """Set a phase status: todo, in_progress, done. Optional notes replace the phase notes."""
    ph = hub.set_phase_status(project_id, phase_id, status, notes)
    return f"Phase {ph['id']} is now {ph['status']}"


@tool
def add_item(project_id: str, type: str, title: str, details: str = "") -> str:
    """Add an item (status open). type: idea, future_request, bug."""
    i = hub.add_item(project_id, type, title, details)
    return f"Added {i['type']} {i['id']}: {i['title']}"


@tool
def update_item(project_id: str, item_id: str, status: str | None = None, type: str | None = None,
                title: str | None = None, details: str | None = None) -> str:
    """Update an item. status: open, planned, done, discarded. type: idea, future_request, bug."""
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


def main():
    mcp.run()


if __name__ == "__main__":
    main()
