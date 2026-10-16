"""Data layer: projects (one JSON file each), inbox (JSONL), resource leases and BIBLIA.md, all under one file lock."""

import contextlib
import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from filelock import FileLock

from .biblia import GATE_DEFAULTS, blocking, current_phase, render, unread_for

PROJECT_STATUSES = ("active", "paused", "parked", "done")
PHASE_STATUSES = ("todo", "in_progress", "done")
ITEM_TYPES = ("idea", "future_request", "bug")
ITEM_STATUSES = ("open", "planned", "done", "discarded")
MESSAGE_KINDS = ("message", "task", "report")
MESSAGE_STATUSES = ("unread", "read", "done")
GATES = ("none", "review", "manual_test")  # strictness order
GATE_BY = ("agent", "user", "dashboard")  # "user" and "dashboard" are both Danny
LIMITS = {"description": 200, "next_step": 160, "phase name": 60, "notes": 240, "title": 100, "gate_reason": 160}  # max characters
SLUG = re.compile(r"[a-z0-9][a-z0-9-]*")


class HubError(ValueError):
    """Invalid id or value. Messages for missing ids start with "unknown "."""


GITIGNORE_ENTRIES = (".lock", "*.tmp")  # the lock file and atomic-write temp files this module creates


def data_dir() -> Path:
    """The one place the data folder is decided: PROJECT_HUB_DATA, else ~/project-hub-data. Never cwd-relative."""
    env = os.environ.get("PROJECT_HUB_DATA")
    if not env:
        return Path.home() / "project-hub-data"
    path = Path(env).expanduser()
    if not path.is_absolute():
        raise HubError(f"PROJECT_HUB_DATA must be an absolute path, got {env!r}")
    return path.resolve()


_default_data_dir = data_dir


def _utcnow():
    return datetime.now(timezone.utc)


def _now():
    return _utcnow().isoformat(timespec="seconds")


def _resource_name(resource):
    _check_text(resource, "resource", required=True)
    return resource.strip().lower()


def _new_id(existing):
    taken = {x["id"] for x in existing}
    while (new := uuid.uuid4().hex[:8]) in taken:
        pass
    return new


def _check_enum(value, allowed, what):
    if value not in allowed:
        raise HubError(f"invalid {what} {value!r}; allowed: {', '.join(allowed)}")


def _check_text(value, what, required=False):
    if not isinstance(value, str) or (required and not value.strip()):
        raise HubError(f"{what} must be a {'non-empty ' if required else ''}string")


def _check_len(value, what, limit):
    if len(value) > limit:
        raise HubError(f"{what} is {len(value)} characters; the limit is {limit}. Please shorten it.")


def _check_repo_path(repo_path):
    if repo_path is not None:
        _check_text(repo_path, "repo_path")
        if repo_path and not Path(repo_path).is_absolute():
            raise HubError(f"repo_path must be absolute, got {repo_path!r}")
    return repo_path or None


def _dump(obj):
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _write_atomic(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def _ensure_gitignore(folder):
    """Add the missing GITIGNORE_ENTRIES to folder/.gitignore, keeping whatever is already there."""
    path = folder / ".gitignore"
    text = path.read_text(encoding="utf-8") if path.is_file() else ""
    have = {line.strip() for line in text.splitlines()}
    missing = [e for e in GITIGNORE_ENTRIES if e not in have]
    if missing:
        sep = "\n" if text and not text.endswith("\n") else ""
        _write_atomic(path, text + sep + "\n".join(missing) + "\n")


def _find(entries, entry_id, what):
    for entry in entries:
        if entry["id"] == entry_id:
            return entry
    raise HubError(f"unknown {what} id {entry_id!r}")


def _short(text, limit=120):
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[:limit - 1] + "…"


def _parse_time(value, what="since"):
    """datetime or ISO string -> aware datetime; naive values are taken as UTC."""
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.strip())
        except ValueError:
            raise HubError(f"{what} must be an ISO timestamp, got {value!r}") from None
    if not isinstance(value, datetime):
        raise HubError(f"{what} must be an ISO timestamp")
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _iso(dt):
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def _local(dt):
    return dt.astimezone().strftime("%H:%M %d/%m")


def _plural(n, one, many):
    return f"{n} {one if n == 1 else many}"


def overview_order(rows):
    """Dashboard overview order: status order, most recently updated first within a status."""
    rows = sorted(rows, key=lambda r: r["updated_at"], reverse=True)  # stable, so this survives the status sort below
    return sorted(rows, key=lambda r: PROJECT_STATUSES.index(r["status"]))


def _message_project(m):
    """The project_id a message event is logged under: its addressee ("all" included), or its sender when sent to "user"."""
    return m["from_project"] if m["to_project"] == "user" else m["to_project"]


class Hub:
    def __init__(self, data_dir: Path | str | None = None):
        self.dir = Path(data_dir).resolve() if data_dir is not None else _default_data_dir()
        self._lock = FileLock(str(self.dir / ".lock"))
        self._gitignore_checked = False

    # --- locking and files -------------------------------------------------

    def _read_lock(self):
        # missing data folder: read without a lock and return empty results
        return self._lock if self.dir.is_dir() else contextlib.nullcontext()

    @contextlib.contextmanager
    def _write_lock(self):
        self.dir.mkdir(parents=True, exist_ok=True)
        with self._lock:
            if not self._gitignore_checked:  # once per process, under the lock so writers never race on it
                _ensure_gitignore(self.dir)
                self._gitignore_checked = True
            yield

    @property
    def _inbox(self):
        return self.dir / "inbox" / "messages.jsonl"

    def _project_path(self, project_id):
        if not isinstance(project_id, str) or not SLUG.fullmatch(project_id):
            raise HubError(f"invalid project id {project_id!r}; must match {SLUG.pattern}")
        return self.dir / "projects" / f"{project_id}.json"

    def _load(self, project_id):
        path = self._project_path(project_id)
        if not path.is_file():
            raise HubError(f"unknown project {project_id!r}")
        return json.loads(path.read_text(encoding="utf-8"))

    def _projects(self):
        folder = self.dir / "projects"
        if not folder.is_dir():
            return []
        return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.json"))]

    def _messages(self):
        if not self._inbox.is_file():
            return []
        return [json.loads(line) for line in self._inbox.read_text(encoding="utf-8").split("\n") if line.strip()]  # not splitlines(): U+2028 etc. are valid inside a JSON line

    @property
    def _leases_path(self):
        return self.dir / "resources" / "leases.json"

    def _leases(self):
        """Active leases, sorted by resource; a lease with expires_at <= now is free."""
        if not self._leases_path.is_file():
            return []
        now = _utcnow()
        leases = json.loads(self._leases_path.read_text(encoding="utf-8"))
        return [l for l in leases if datetime.fromisoformat(l["expires_at"]) > now]

    def _save_leases(self, leases):
        # leases come from _leases(), so expired ones are dropped here
        _write_atomic(self._leases_path, _dump(sorted(leases, key=lambda l: l["resource"])))
        self.regenerate_biblia()

    def _save(self, project):
        project["updated_at"] = _now()
        _write_atomic(self._project_path(project["id"]), _dump(project))
        self.regenerate_biblia()

    @property
    def _events_path(self):
        return self.dir / "activity" / "events.jsonl"

    def _events(self):
        if not self._events_path.is_file():
            return []
        return [json.loads(line) for line in self._events_path.read_text(encoding="utf-8").split("\n") if line.strip()]

    def _append_events(self, project_id, by, events):
        """Append activity events. Call inside the write lock, after the change is saved."""
        if not events:
            return
        self._events_path.parent.mkdir(parents=True, exist_ok=True)
        at = _now()
        with open(self._events_path, "a", encoding="utf-8", newline="\n") as f:
            f.write("".join(json.dumps({"at": at, "project_id": project_id, "by": by, **e}, sort_keys=True, ensure_ascii=False) + "\n"
                            for e in events))

    def _modify(self, project_id, change, by="agent"):
        """Load, apply change(project, log) -> result, save, append the logged events, return a copy of result.
        change calls log(type, text, **extra) once per activity event."""
        with self._write_lock():
            project = self._load(project_id)
            events = []
            result = change(project, lambda type, text, **extra: events.append({"type": type, "text": _short(text), **extra}))
            self._save(project)
            self._append_events(project_id, by, events)
            return json.loads(json.dumps(result))

    # --- projects ----------------------------------------------------------

    def list_projects(self, status: str | None = None) -> list[dict]:
        if status is not None:
            _check_enum(status, PROJECT_STATUSES, "project status")
        with self._read_lock():
            return [p for p in self._projects() if status is None or p["status"] == status]

    def get_project(self, project_id) -> dict:
        with self._read_lock():
            project = self._load(project_id)
            project["unread_messages"] = unread_for(project_id, self._messages())
            return project

    def create_project(self, id, name, description, repo_path=None, phases: list[str] | None = None, *, by="agent") -> dict:
        self._project_path(id)
        if id in ("all", "user"):
            raise HubError(f"project id {id!r} is reserved for the inbox")
        _check_text(name, "name", required=True)
        _check_text(description, "description")
        _check_len(description, "description", LIMITS["description"])
        repo_path = _check_repo_path(repo_path)
        phases = phases or []
        if not isinstance(phases, list):
            raise HubError("phases must be a list of names")
        for phase_name in phases:
            _check_text(phase_name, "phase name", required=True)
            _check_len(phase_name, "phase name", LIMITS["phase name"])
        with self._write_lock():
            if self._project_path(id).exists():
                raise HubError(f"project {id!r} already exists")
            project = {
                "id": id,
                "name": name,
                "description": description,
                "repo_path": repo_path,
                "status": "active",
                "phases": [],
                "items": [],
                "decisions": [],
                "next_step": "",
            }
            for phase_name in phases:
                project["phases"].append({"id": _new_id(project["phases"]), "name": phase_name, "status": "todo", "notes": ""})
            self._save(project)
            self._append_events(id, by, [{"type": "project_created", "text": _short(name)}])
            return json.loads(json.dumps(project))

    def update_project(self, project_id, *, status=None, description=None, next_step=None, repo_path=None, by="agent") -> dict:
        if status is not None:
            _check_enum(status, PROJECT_STATUSES, "project status")
        if description is not None:
            _check_text(description, "description")
            _check_len(description, "description", LIMITS["description"])
        if next_step is not None:
            _check_text(next_step, "next_step")
            _check_len(next_step, "next_step", LIMITS["next_step"])
        new_repo = _check_repo_path(repo_path)

        def change(p, log):
            changed = [f"status {p['status']} → {status}"] if status is not None and status != p["status"] else []
            changed += [f"{key} updated" for key, new, given in (("description", description, description is not None),
                                                                 ("next_step", next_step, next_step is not None),
                                                                 ("repo_path", new_repo, repo_path is not None))
                        if given and new != p.get(key)]
            if status is not None:
                p["status"] = status
            if description is not None:
                p["description"] = description
            if next_step is not None:
                p["next_step"] = next_step
            if repo_path is not None:  # "" clears it
                p["repo_path"] = new_repo
            if changed:
                log("project_updated", "; ".join(changed))
            return p

        return self._modify(project_id, change, by)

    # --- phases ------------------------------------------------------------

    def add_phase(self, project_id, name, position: int | None = None, *, by="agent") -> dict:
        _check_text(name, "phase name", required=True)
        _check_len(name, "phase name", LIMITS["phase name"])

        def change(p, log):
            if position is not None and not (type(position) is int and 0 <= position <= len(p["phases"])):
                raise HubError(f"position must be an integer from 0 to {len(p['phases'])}, got {position!r}")
            phase = {"id": _new_id(p["phases"]), "name": name, "status": "todo", "notes": ""}
            p["phases"].insert(len(p["phases"]) if position is None else position, phase)
            log("phase_added", name, phase=name)
            return phase

        return self._modify(project_id, change, by)

    def set_phase_status(self, project_id, phase_id, status, notes=None, *, by="agent") -> dict:
        """by="agent" is refused to in_progress/done on an unapproved review or a manual_test gate; by="user"/"dashboard" never."""
        _check_enum(status, PHASE_STATUSES, "phase status")
        _check_enum(by, GATE_BY, "by")
        if notes is not None:
            _check_text(notes, "notes")
            _check_len(notes, "notes", LIMITS["notes"])

        def change(p, log):
            phase = _find(p["phases"], phase_id, "phase")
            gate = phase.get("gate", "none")
            if by == "agent" and status in ("in_progress", "done") and (
                    gate == "manual_test" or (gate == "review" and not phase.get("gate_approved"))):
                state, todo = ("review, not approved", "what is ready for review") if gate == "review" else ("manual_test", "what needs testing")
                raise HubError(f"phase {phase['name']!r} is gated ({state}): {phase.get('gate_reason', '')}. "
                               f"Post a report message describing {todo}, then stop.")
            if status != phase["status"]:
                log("phase_status", f"{phase['status']} → {status}", phase=phase["name"])
            elif notes is not None and notes != phase["notes"]:
                log("phase_updated", "notes updated", phase=phase["name"])
            phase["status"] = status
            if notes is not None:
                phase["notes"] = notes
            return phase

        return self._modify(project_id, change, by)

    def update_phase(self, project_id, phase_id, *, name=None, notes=None, by="agent") -> dict:
        if name is None and notes is None:
            raise HubError("nothing to update: pass name and/or notes")
        if name is not None:
            _check_text(name, "phase name", required=True)
            _check_len(name, "phase name", LIMITS["phase name"])
        if notes is not None:
            _check_text(notes, "notes")
            _check_len(notes, "notes", LIMITS["notes"])

        def change(p, log):
            phase = _find(p["phases"], phase_id, "phase")
            changed = ([f"{phase['name']} → {name}"] if name is not None and name != phase["name"] else []) + \
                      (["notes updated"] if notes is not None and notes != phase["notes"] else [])
            if changed:
                log("phase_updated", "; ".join(changed), phase=name or phase["name"])
            if name is not None:
                phase["name"] = name
            if notes is not None:
                phase["notes"] = notes
            return phase

        return self._modify(project_id, change, by)

    def delete_phase(self, project_id, phase_id, *, by="agent") -> dict:
        def change(p, log):
            phase = _find(p["phases"], phase_id, "phase")
            if phase.get("gate", "none") != "none":  # so agents cannot remove a gate by deleting its phase
                raise HubError(f"phase {phase['name']!r} has a {phase['gate']} gate and cannot be deleted; "
                               "only Danny removes gates, in the dashboard")
            p["phases"].remove(phase)
            log("phase_deleted", phase["name"], phase=phase["name"])
            return phase

        return self._modify(project_id, change, by)

    def set_gate(self, project_id, phase_id, gate, reason="", *, by="agent") -> dict:
        """by="agent" may only add or tighten a gate (none < review < manual_test), with a reason.
        by="user"/"dashboard" (Danny) may set any gate, stored as gate_set_by "user"; "none" clears it.
        A change of gate type resets the approval."""
        _check_enum(gate, GATES, "gate")
        _check_enum(by, GATE_BY, "by")
        _check_text(reason, "gate reason", required=by == "agent")
        _check_len(reason, "gate reason", LIMITS["gate_reason"])

        def change(p, log):
            phase = _find(p["phases"], phase_id, "phase")
            current = phase.get("gate", "none")
            if by == "agent" and GATES.index(gate) <= GATES.index(current):
                raise HubError(f"phase {phase['name']!r} already has gate {current!r}; agents can only add or tighten "
                               "gates (none < review < manual_test). Only Danny removes, loosens or approves gates, in the dashboard.")
            if current == "none" and gate != "none":
                log("gate_set", f"{gate}: {reason}" if reason else gate, phase=phase["name"])
            elif gate == "none" and current != "none":
                log("gate_removed", f"{current} → none", phase=phase["name"])
            elif gate != current:
                log("gate_changed", f"{current} → {gate}", phase=phase["name"])
            elif gate != "none" and reason != phase.get("gate_reason", ""):
                log("gate_changed", f"{gate}: reason updated", phase=phase["name"])
            if gate == "none":
                phase.update(GATE_DEFAULTS)
            else:
                phase.update(gate=gate, gate_reason=reason, gate_set_by="agent" if by == "agent" else "user",
                             gate_approved=phase.get("gate_approved", False) and gate == current)
            return phase

        return self._modify(project_id, change, by)

    def approve_gate(self, project_id, phase_id, *, by="dashboard") -> dict:
        """Dashboard only: approve an unapproved review gate."""
        def change(p, log):
            phase = _find(p["phases"], phase_id, "phase")
            if phase.get("gate", "none") != "review" or phase.get("gate_approved"):
                raise HubError(f"phase {phase['name']!r} has no unapproved review gate to approve")
            phase["gate_approved"] = True
            log("gate_approved", "review approved", phase=phase["name"])
            return phase

        return self._modify(project_id, change, by)

    # --- items -------------------------------------------------------------

    def add_item(self, project_id, type, title, details="", *, by="agent") -> dict:
        _check_enum(type, ITEM_TYPES, "item type")
        _check_text(title, "title", required=True)
        _check_len(title, "title", LIMITS["title"])
        _check_text(details, "details")

        def change(p, log):
            item = {"id": _new_id(p["items"]), "type": type, "title": title, "details": details,
                    "status": "open", "created_at": _now()}
            p["items"].append(item)
            log("item_added", f"{type}: {title}", title=title)
            return item

        return self._modify(project_id, change, by)

    def update_item(self, project_id, item_id, *, status=None, type=None, title=None, details=None, by="agent") -> dict:
        if status is not None:
            _check_enum(status, ITEM_STATUSES, "item status")
        if type is not None:
            _check_enum(type, ITEM_TYPES, "item type")
        if title is not None:
            _check_text(title, "title", required=True)
            _check_len(title, "title", LIMITS["title"])
        if details is not None:
            _check_text(details, "details")

        def change(p, log):
            item = _find(p["items"], item_id, "item")
            fields = (("status", status), ("type", type), ("title", title), ("details", details))
            changed = [f"{key} {item[key]} → {value}" if key in ("status", "type") else f"{key} updated"
                       for key, value in fields if value is not None and value != item[key]]
            closed = status in ("done", "discarded") and item["status"] not in ("done", "discarded")
            for key, value in fields:
                if value is not None:
                    item[key] = value
            if changed:
                log("item_closed" if closed else "item_updated", "; ".join(changed), title=item["title"])
            return item

        return self._modify(project_id, change, by)

    # --- decisions ---------------------------------------------------------

    def log_decision(self, project_id, decision, reason, *, by="agent") -> dict:
        _check_text(decision, "decision", required=True)
        _check_text(reason, "reason")

        def change(p, log):
            entry = {"date": _now(), "decision": decision, "reason": reason}
            p["decisions"].append(entry)
            log("decision", decision)
            return entry

        return self._modify(project_id, change, by)

    # --- inbox -------------------------------------------------------------

    def post_message(self, to_project, kind, title, body, from_project="user") -> dict:
        """to_project: a project id, "all", or "user" (to Danny). The activity event is logged with by=from_project."""
        _check_enum(kind, MESSAGE_KINDS, "message kind")
        _check_text(title, "title", required=True)
        _check_text(body, "body")
        with self._write_lock():
            if to_project not in ("all", "user"):
                self._load(to_project)
            if from_project != "user":
                self._load(from_project)
            message = {
                "id": _new_id(self._messages()),
                "created_at": _now(),
                "from_project": from_project,
                "to_project": to_project,
                "kind": kind,
                "title": title,
                "body": body,
                "status": "unread",
            }
            self._inbox.parent.mkdir(parents=True, exist_ok=True)
            with open(self._inbox, "a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(message, sort_keys=True, ensure_ascii=False) + "\n")
            self.regenerate_biblia()
            self._append_events(_message_project(message), from_project,
                                [{"type": "message_posted", "text": _short(f"{kind} from {from_project} to {to_project}: {title}")}])
            return message

    def read_inbox(self, project_id, unread_only=True) -> list[dict]:
        with self._read_lock():
            self._load(project_id)
            return [m for m in self._messages()
                    if m["to_project"] in (project_id, "all") and (not unread_only or m["status"] == "unread")]

    def mark_message(self, message_id, status, *, by="agent") -> dict:
        _check_enum(status, MESSAGE_STATUSES, "message status")
        with self._write_lock():
            messages = self._messages()
            # shortcut: an "all" message has one shared status, so marking it marks it for everyone
            message = _find(messages, message_id, "message")
            old = message["status"]
            message["status"] = status
            _write_atomic(self._inbox, "".join(json.dumps(m, sort_keys=True, ensure_ascii=False) + "\n" for m in messages))
            self.regenerate_biblia()
            if old != status:
                self._append_events(_message_project(message), by,
                                    [{"type": "message_marked", "text": _short(f"{message['title']}: {old} → {status}")}])
            return dict(message)

    # --- resource leases ---------------------------------------------------

    def claim_resource(self, resource, project_id, purpose, ttl_minutes=30) -> dict:
        """Exclusive lease. Returns {"status": "granted"|"renewed"|"busy", "lease"}; busy writes nothing. Never waits."""
        resource = _resource_name(resource)
        _check_text(purpose, "purpose")
        if type(ttl_minutes) is not int or not 1 <= ttl_minutes <= 1440:
            raise HubError(f"ttl_minutes must be an integer from 1 to 1440, got {ttl_minutes!r}")
        with self._write_lock():
            self._load(project_id)
            leases = self._leases()
            lease = next((l for l in leases if l["resource"] == resource), None)
            if lease and lease["project_id"] != project_id:
                return {"status": "busy", "lease": dict(lease)}
            now = _utcnow()
            expires_at = (now + timedelta(minutes=ttl_minutes)).isoformat(timespec="seconds")
            if lease:
                status = "renewed"
                lease.update(purpose=purpose, expires_at=expires_at)
            else:
                status = "granted"
                lease = {"resource": resource, "project_id": project_id, "purpose": purpose,
                         "acquired_at": now.isoformat(timespec="seconds"), "expires_at": expires_at}
                leases.append(lease)
            self._save_leases(leases)
            return {"status": status, "lease": dict(lease)}

    def release_resource(self, resource, project_id) -> dict:
        self._load(project_id)
        return self._release(resource, project_id)

    def force_release(self, resource) -> dict:
        """Release whoever holds it (dashboard)."""
        return self._release(resource, None)

    def _release(self, resource, project_id):
        resource = _resource_name(resource)
        with self._write_lock():
            leases = self._leases()
            lease = next((l for l in leases if l["resource"] == resource), None)
            if lease is None:
                raise HubError(f"resource {resource!r} is not claimed" if project_id else f"unknown resource {resource!r} (not claimed)")
            if project_id is not None and lease["project_id"] != project_id:
                raise HubError(f"resource {resource!r} is held by {lease['project_id']!r}, not {project_id!r}")
            leases.remove(lease)
            self._save_leases(leases)
            return dict(lease)

    def list_resources(self) -> list[dict]:
        with self._read_lock():
            return self._leases()

    # --- activity and summary ----------------------------------------------

    @property
    def _summary_state_path(self):
        return self.dir / "summary_state.json"

    def activity(self, project_id=None, since=None) -> list[dict]:
        """Activity events, oldest first, optionally for one project and/or at or after since."""
        since = _parse_time(since) if since is not None else None
        with self._read_lock():
            if project_id is not None:
                self._load(project_id)
            return [e for e in self._events() if (project_id is None or e["project_id"] == project_id)
                    and (since is None or datetime.fromisoformat(e["at"]) >= since)]

    def summary_state(self) -> dict:
        """{"last_seen": iso} once mark_summary_seen has run, else {}."""
        with self._read_lock():
            path = self._summary_state_path
            return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}

    def mark_summary_seen(self, at=None) -> dict:
        state = {"last_seen": _iso(_parse_time(at, "at") if at is not None else _utcnow())}
        with self._write_lock():
            _write_atomic(self._summary_state_path, _dump(state))
        return state

    def summary(self, since: datetime | str | None = None, hours: int | None = None) -> dict:
        """What happened per project in [since, now]. since wins over hours; with neither, since is the stored
        last-seen time, else 24 h ago. Projects with activity (or with something waiting for Danny) come first."""
        if hours is not None and (type(hours) is not int or hours < 1):
            raise HubError(f"hours must be a positive integer, got {hours!r}")
        until = _utcnow()
        with self._read_lock():
            projects = overview_order(self._projects())
            messages = self._messages()
            events = self._events()
        last_seen = self.summary_state().get("last_seen")
        if since is not None:
            start = _parse_time(since)
        elif hours is not None:
            start = until - timedelta(hours=hours)
        else:
            start = _parse_time(last_seen, "last_seen") if last_seen else until - timedelta(hours=24)
        log_started = events[0]["at"] if events else None
        if log_started is None:
            note = "sin registro de actividad: el registro aún no ha empezado"
        elif start < datetime.fromisoformat(log_started):
            note = f"sin registro de actividad antes de {_local(datetime.fromisoformat(log_started))}"
        else:
            note = None

        def in_period(ts):
            return bool(ts) and start <= datetime.fromisoformat(ts) <= until

        active, rest = [], []
        for p in projects:
            entry = self._project_summary(p, messages, [e for e in events if e["project_id"] == p["id"] and in_period(e["at"])],
                                          in_period, f"Periodo: {_local(start)} - {_local(until)}")
            (active if entry["has_activity"] else rest).append(entry)
        return {"since": _iso(start), "until": _iso(until), "last_seen": last_seen, "log_started_at": log_started,
                "note": note, "projects": active + rest}

    @staticmethod
    def _project_summary(p, messages, events, in_period, period_line):
        pid = p["id"]
        mine = [m for m in messages if m["to_project"] in (pid, "all") or (m["to_project"] == "user" and m["from_project"] == pid)]
        gates = [{"phase_id": ph["id"], "phase": ph["name"], "gate": ph["gate"], "reason": ph.get("gate_reason", "")}
                 for ph in p["phases"] if blocking(ph)]
        user_messages = [{k: m[k] for k in ("id", "title", "from_project", "created_at")}
                         for m in mine if m["to_project"] == "user" and m["status"] != "done"]
        reports = [{k: m[k] for k in ("id", "title", "body", "from_project", "created_at", "status")}
                   for m in mine if m["kind"] == "report" and in_period(m["created_at"])]
        phase_changes = [{k: e.get(k) for k in ("at", "phase", "text", "by")} for e in events if e["type"] == "phase_status"]
        decisions = [{k: d[k] for k in ("date", "decision", "reason")} for d in p["decisions"] if in_period(d.get("date"))]
        items_opened = [{k: i[k] for k in ("id", "type", "title", "created_at")} for i in p["items"] if in_period(i.get("created_at"))]
        items_closed = [{k: e.get(k) for k in ("at", "title", "text")} for e in events if e["type"] == "item_closed"]
        # blocked: work that cannot go on without someone else - an in_progress phase stopped at its gate,
        # or a message from another project (an agent) to this one that is not done yet
        blocked = [f"fase '{ph['name']}' en curso, espera gate {ph['gate']}" for ph in p["phases"]
                   if ph["status"] == "in_progress" and blocking(ph)]
        blocked += [f"mensaje de {m['from_project']}: {_short(m['title'], 80)}" for m in messages
                    if m["to_project"] == pid and m["kind"] == "message" and m["from_project"] not in ("user", pid) and m["status"] != "done"]
        cur = current_phase(p)

        done = [c["phase"] for c in phase_changes if c["text"].endswith("→ done")]
        lines = [period_line]
        if reports:
            lines.append(_plural(len(reports), "informe nuevo", "informes nuevos")
                         + (": " + "; ".join(_short(r["title"], 80) for r in reports) if len(reports) <= 2 else ""))
        if done:
            lines.append(_plural(len(done), "fase terminada", "fases terminadas") + (": " + ", ".join(done) if len(done) <= 2 else ""))
        if decisions:
            lines.append(_plural(len(decisions), "decisión de los agentes", "decisiones de los agentes"))
        if gates:
            lines.append(_plural(len(gates), "gate esperando a Danny", "gates esperando a Danny"))
        if len(lines) == 1:
            lines.append("Sin actividad nueva en este periodo.")
        lines.append(f"Revisa el proyecto {pid} en project-hub (get_project y read_inbox) y prepara los siguientes pasos.")

        return {
            "id": pid, "name": p["name"], "status": p["status"],
            # a waiting gate or a message to Danny counts as activity, so it is never hidden in the "nothing happened" group
            "has_activity": bool(events or reports or decisions or items_opened or gates or user_messages),
            "current": {"phase": cur["name"] if cur else None, "n": p["phases"].index(cur) + 1 if cur else None,
                        "total": len(p["phases"]), "next_step": p["next_step"] or None},
            "action": {"gates": gates, "user_messages": user_messages},
            "reports": reports, "phase_changes": phase_changes, "decisions": decisions,
            "items_opened": items_opened, "items_closed": items_closed, "blocked": blocked,
            "chat_text": "\n".join(lines),
        }

    # --- misc --------------------------------------------------------------

    def regenerate_biblia(self) -> None:
        with self._write_lock():
            _write_atomic(self.dir / "BIBLIA.md", render(self._projects(), self._messages(), _now(), self._leases()))

    def find_project_for_path(self, path) -> dict | None:
        """Project whose repo_path equals or contains path (longest repo_path wins), as get_project returns it."""
        target = os.path.normcase(str(Path(path).resolve()))
        best = None
        with self._read_lock():
            for p in self._projects():
                if not p.get("repo_path"):
                    continue
                repo = os.path.normcase(str(Path(p["repo_path"]).resolve()))
                if target == repo or target.startswith(repo.rstrip(os.sep) + os.sep):
                    if best is None or len(repo) > len(best[0]):
                        best = (repo, p)
            if best is None:
                return None
            best[1]["unread_messages"] = unread_for(best[1]["id"], self._messages())
            return best[1]
