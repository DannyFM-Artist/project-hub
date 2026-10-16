"""Render BIBLIA.md: a single Markdown file from which any AI chat can recover full context."""

ITEM_TYPES = ("idea", "future_request", "bug")


def current_phase(project):
    """First in_progress phase, else first todo, else last phase, else None."""
    phases = project.get("phases", [])
    for status in ("in_progress", "todo"):
        for phase in phases:
            if phase["status"] == status:
                return phase
    return phases[-1] if phases else None


def unread_for(project_id, messages):
    return [m for m in messages if m["to_project"] in (project_id, "all") and m["status"] == "unread"]


def _cell(text):
    return str(text or "").replace("|", "\\|").replace("\r", "").replace("\n", " ")


def _block(text):
    # indent continuation lines so multi-line text stays inside its list item
    return str(text or "").replace("\r", "").replace("\n", "\n  ")


def render(projects, messages, generated_at):
    out = [
        "# BIBLIA - project-hub",
        "",
        f"Generated: {generated_at}",
        "",
        "Auto-generated after every write. Do not edit by hand; use the project-hub tools.",
        "",
        "## Index",
        "",
        "| Name | ID | Status | Current phase | Next step | Updated |",
        "|---|---|---|---|---|---|",
    ]
    for p in projects:
        cur = current_phase(p)
        phase = f"{cur['name']} ({cur['status']})" if cur else "-"
        out.append(
            f"| {_cell(p['name'])} | {p['id']} | {p['status']} | {_cell(phase)} "
            f"| {_cell(p['next_step']) or '-'} | {p['updated_at']} |"
        )
    if not projects:
        out.append("| (no projects) | | | | | |")

    for p in projects:
        cur = current_phase(p)
        out += [
            "",
            f"## {_cell(p['name'])} (`{p['id']}`)",
            "",
            f"- Status: {p['status']}",
            f"- Repo path: {p['repo_path'] or '-'}",
            f"- Next step: {_block(p['next_step']) or '-'}",
            f"- Updated: {p['updated_at']}",
            "",
            "### Description",
            "",
            str(p["description"] or "-"),
            "",
            "### Phases",
            "",
        ]
        for i, ph in enumerate(p["phases"], 1):
            line = f"{i}. [{ph['status']}] {ph['name']} (id {ph['id']})"
            if cur is ph:
                line += " <- current"
            if ph["notes"]:
                line += f" - {_block(ph['notes'])}"
            out.append(line)
        if not p["phases"]:
            out.append("(no phases)")

        out += ["", "### Open items", ""]
        open_items = [it for it in p["items"] if it["status"] in ("open", "planned")]
        for t in ITEM_TYPES:
            group = [it for it in open_items if it["type"] == t]
            if group:
                out.append(f"**{t}**")
                out.append("")
                for it in group:
                    line = f"- [{it['status']}] {_cell(it['title'])} (id {it['id']})"
                    if it["details"]:
                        line += f": {_block(it['details'])}"
                    out.append(line)
                out.append("")
        if not open_items:
            out += ["(none)", ""]

        out += ["### Recent decisions", ""]
        for d in p["decisions"][-5:]:
            out.append(f"- {d['date']}: {_block(d['decision'])} - because {_block(d['reason'])}")
        if not p["decisions"]:
            out.append("(none)")

        unread = unread_for(p["id"], messages)
        out += ["", "### Inbox", "", f"Unread: {len(unread)}"]
        for m in unread:
            out.append(f"- [{m['kind']}] {_cell(m['title'])} (from {m['from_project']}, to {m['to_project']}, id {m['id']})")
    return "\n".join(out) + "\n"
