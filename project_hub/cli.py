"""Command line entry point: project-hub mcp | dashboard | session-start."""

import argparse
import sys
from pathlib import Path


def session_start() -> None:
    # A SessionStart hook must never break session start: any failure -> silent stdout, exit 0.
    try:
        from .biblia import autonomy_line, current_phase, gate_label
        from .hub import Hub

        p = Hub().find_project_for_path(Path.cwd())
        if p is None:
            return
        cur = current_phase(p)
        unread = p["unread_messages"]
        lines = [
            f"[project-hub] {p['name']} ({p['id']}) — status: {p['status']}",
            f"Current phase: {cur['name']} ({cur['status']})" if cur else "Current phase: none",
            f"Next step: {p['next_step'] or '(not set)'}",
        ]
        lines += [f"Gated phase {i}: {ph['name']} ({ph['status']}) {gate_label(ph)}"
                  for i, ph in enumerate(p["phases"], 1) if gate_label(ph)]
        lines.append(autonomy_line(p))
        if unread:
            lines.append(f"Unread inbox ({len(unread)}):")
            lines += [f"- [{m['kind']}] {m['title']} — from {m['from_project']} (id {m['id']})" for m in unread]
        text = "\n".join(lines) + "\n"
    except Exception as e:
        print(f"project-hub session-start: {type(e).__name__}: {e}", file=sys.stderr)
        return
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdout.write(text)


def main() -> None:
    parser = argparse.ArgumentParser(prog="project-hub", description="Local project-tracking hub.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("mcp", help="run the MCP stdio server")
    sub.add_parser("dashboard", help="run the web dashboard on http://127.0.0.1:8765")
    sub.add_parser("session-start", help="print project context for the current directory (SessionStart hook)")
    command = parser.parse_args().command
    if command == "mcp":
        from .mcp_server import main as run
    elif command == "dashboard":
        from .web import main as run
    else:
        run = session_start
    run()


if __name__ == "__main__":
    main()
