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


GATE_DEFAULTS = {"gate_state": None, "gate_reason": "", "gate_set_by": None,
                 "gate_resolved_action": None, "gate_resolved_words": None, "gate_resolved_at": None}  # a phase without a gate


def blocking(phase):
    """A waiting gate on a phase that is not done: work stops there until Danny resolves it from his chat."""
    return phase["status"] != "done" and phase.get("gate_state") == "waiting"


def stopping_gates(project):
    """Blocking phases that stop the next work: at or before the current phase, or in progress."""
    phases = project.get("phases", [])
    cur = current_phase(project)
    limit = phases.index(cur) if cur else -1
    return [ph for i, ph in enumerate(phases) if blocking(ph) and (i <= limit or ph["status"] == "in_progress")]


def autonomy_limit(project):
    """Number of phases before the first blocking phase; len(phases) if none blocks."""
    phases = project.get("phases", [])
    return next((i for i, ph in enumerate(phases) if blocking(ph)), len(phases))


def autonomy_line(project):
    n = autonomy_limit(project)
    phases = project.get("phases", [])
    if n > 0:
        return f"Autonomous work allowed up to phase {n} ({phases[n - 1]['name']})"
    return "Autonomous work allowed up to phase 0" + (" (phase 1 is gated)" if phases else "")


def gate_label(phase):
    """`[espera a Danny] reason` for a waiting gate, `[resuelto vía chat (action): «words»]` for a resolved one,
    "" without a gate. A gate resolved before the chat (no words) reads `[resuelto (action)]`."""
    state = phase.get("gate_state")
    if state == "waiting":
        return "[espera a Danny]" + (f" {_cell(phase.get('gate_reason'))}" if phase.get("gate_reason") else "")
    if state == "continue":
        action = phase.get("gate_resolved_action") or "sigue"
        words = phase.get("gate_resolved_words")
        return f"[resuelto vía chat ({action}): «{_cell(words)}»]" if words else f"[resuelto ({action})]"
    return ""


def waiting(projects):
    """One entry per blocking gate, most urgent first: gates that stop the next work, then the rest; project order."""
    now, later = [], []
    for p in projects:
        stop = {ph["id"] for ph in stopping_gates(p)}
        for ph in p.get("phases", []):
            if blocking(ph):
                (now if ph["id"] in stop else later).append(
                    {"project_id": p["id"], "project_name": p["name"], "phase_id": ph["id"], "phase_name": ph["name"],
                     "reason": ph.get("gate_reason", ""), "set_by": ph.get("gate_set_by")})
    return now + later


def _cell(text):
    return str(text or "").replace("|", "\\|").replace("\r", "").replace("\n", " ")


def _block(text):
    # indent continuation lines so multi-line text stays inside its list item
    return str(text or "").replace("\r", "").replace("\n", "\n  ")


def render(projects, messages, generated_at, leases=()):
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

    out += ["", "## Active resources", ""]
    if leases:
        out += ["| Resource | Project | Purpose | Expires |", "|---|---|---|---|"]
        out += [f"| {_cell(l['resource'])} | {l['project_id']} | {_cell(l['purpose']) or '-'} | {l['expires_at']} |" for l in leases]
    else:
        out.append("(none)")

    out += ["", "## Waiting for Danny", ""]
    out += [f"- {_cell(w['project_name'])} (`{w['project_id']}`): phase {_cell(w['phase_name'])} (id {w['phase_id']}) [espera a Danny] {_cell(w['reason'])}"
            for w in waiting(projects)] or ["(none)"]

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
            f"- {autonomy_line(p)}",
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
            if gate := gate_label(ph):
                line += f" {gate}"
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
