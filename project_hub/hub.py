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

from .biblia import GATE_DEFAULTS, render, unread_for

PROJECT_STATUSES = ("active", "paused", "parked", "done")
PHASE_STATUSES = ("todo", "in_progress", "done")
ITEM_TYPES = ("idea", "future_request", "bug")
ITEM_STATUSES = ("open", "planned", "done", "discarded")
MESSAGE_KINDS = ("message", "task", "report")
MESSAGE_STATUSES = ("unread", "read", "done")
GATES = ("none", "review", "manual_test")  # strictness order
GATE_BY = ("agent", "user")
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

    def _modify(self, project_id, change):
        """Load, apply change(project) -> result, save, return a copy of result."""
        with self._write_lock():
            project = self._load(project_id)
            result = change(project)
            self._save(project)
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

    def create_project(self, id, name, description, repo_path=None, phases: list[str] | None = None) -> dict:
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
            return json.loads(json.dumps(project))

    def update_project(self, project_id, *, status=None, description=None, next_step=None, repo_path=None) -> dict:
        if status is not None:
            _check_enum(status, PROJECT_STATUSES, "project status")
        if description is not None:
            _check_text(description, "description")
            _check_len(description, "description", LIMITS["description"])
        if next_step is not None:
            _check_text(next_step, "next_step")
            _check_len(next_step, "next_step", LIMITS["next_step"])
        new_repo = _check_repo_path(repo_path)

        def change(p):
            if status is not None:
                p["status"] = status
            if description is not None:
                p["description"] = description
            if next_step is not None:
                p["next_step"] = next_step
            if repo_path is not None:  # "" clears it
                p["repo_path"] = new_repo
            return p

        return self._modify(project_id, change)

    # --- phases ------------------------------------------------------------

    def add_phase(self, project_id, name, position: int | None = None) -> dict:
        _check_text(name, "phase name", required=True)
        _check_len(name, "phase name", LIMITS["phase name"])

        def change(p):
            if position is not None and not (type(position) is int and 0 <= position <= len(p["phases"])):
                raise HubError(f"position must be an integer from 0 to {len(p['phases'])}, got {position!r}")
            phase = {"id": _new_id(p["phases"]), "name": name, "status": "todo", "notes": ""}
            p["phases"].insert(len(p["phases"]) if position is None else position, phase)
            return phase

        return self._modify(project_id, change)

    def set_phase_status(self, project_id, phase_id, status, notes=None, *, by="agent") -> dict:
        """by="agent" is refused to in_progress/done on an unapproved review or a manual_test gate; by="user" never."""
        _check_enum(status, PHASE_STATUSES, "phase status")
        _check_enum(by, GATE_BY, "by")
        if notes is not None:
            _check_text(notes, "notes")
            _check_len(notes, "notes", LIMITS["notes"])

        def change(p):
            phase = _find(p["phases"], phase_id, "phase")
            gate = phase.get("gate", "none")
            if by == "agent" and status in ("in_progress", "done") and (
                    gate == "manual_test" or (gate == "review" and not phase.get("gate_approved"))):
                state, todo = ("review, not approved", "what is ready for review") if gate == "review" else ("manual_test", "what needs testing")
                raise HubError(f"phase {phase['name']!r} is gated ({state}): {phase.get('gate_reason', '')}. "
                               f"Post a report message describing {todo}, then stop.")
            phase["status"] = status
            if notes is not None:
                phase["notes"] = notes
            return phase

        return self._modify(project_id, change)

    def update_phase(self, project_id, phase_id, *, name=None, notes=None) -> dict:
        if name is None and notes is None:
            raise HubError("nothing to update: pass name and/or notes")
        if name is not None:
            _check_text(name, "phase name", required=True)
            _check_len(name, "phase name", LIMITS["phase name"])
        if notes is not None:
            _check_text(notes, "notes")
            _check_len(notes, "notes", LIMITS["notes"])

        def change(p):
            phase = _find(p["phases"], phase_id, "phase")
            if name is not None:
                phase["name"] = name
            if notes is not None:
                phase["notes"] = notes
            return phase

        return self._modify(project_id, change)

    def delete_phase(self, project_id, phase_id) -> dict:
        def change(p):
            phase = _find(p["phases"], phase_id, "phase")
            if phase.get("gate", "none") != "none":  # so agents cannot remove a gate by deleting its phase
                raise HubError(f"phase {phase['name']!r} has a {phase['gate']} gate and cannot be deleted; "
                               "only Danny removes gates, in the dashboard")
            p["phases"].remove(phase)
            return phase

        return self._modify(project_id, change)

    def set_gate(self, project_id, phase_id, gate, reason="", *, by="agent") -> dict:
        """by="agent" may only add or tighten a gate (none < review < manual_test), with a reason.
        by="user" (dashboard) may set any gate; "none" clears it. A change of gate type resets the approval."""
        _check_enum(gate, GATES, "gate")
        _check_enum(by, GATE_BY, "by")
        _check_text(reason, "gate reason", required=by == "agent")
        _check_len(reason, "gate reason", LIMITS["gate_reason"])

        def change(p):
            phase = _find(p["phases"], phase_id, "phase")
            current = phase.get("gate", "none")
            if by == "agent" and GATES.index(gate) <= GATES.index(current):
                raise HubError(f"phase {phase['name']!r} already has gate {current!r}; agents can only add or tighten "
                               "gates (none < review < manual_test). Only Danny removes, loosens or approves gates, in the dashboard.")
            if gate == "none":
                phase.update(GATE_DEFAULTS)
            else:
                phase.update(gate=gate, gate_reason=reason, gate_set_by=by,
                             gate_approved=phase.get("gate_approved", False) and gate == current)
            return phase

        return self._modify(project_id, change)

    def approve_gate(self, project_id, phase_id) -> dict:
        """Dashboard only: approve an unapproved review gate."""
        def change(p):
            phase = _find(p["phases"], phase_id, "phase")
            if phase.get("gate", "none") != "review" or phase.get("gate_approved"):
                raise HubError(f"phase {phase['name']!r} has no unapproved review gate to approve")
            phase["gate_approved"] = True
            return phase

        return self._modify(project_id, change)

    # --- items -------------------------------------------------------------

    def add_item(self, project_id, type, title, details="") -> dict:
        _check_enum(type, ITEM_TYPES, "item type")
        _check_text(title, "title", required=True)
        _check_len(title, "title", LIMITS["title"])
        _check_text(details, "details")

        def change(p):
            item = {"id": _new_id(p["items"]), "type": type, "title": title, "details": details,
                    "status": "open", "created_at": _now()}
            p["items"].append(item)
            return item

        return self._modify(project_id, change)

    def update_item(self, project_id, item_id, *, status=None, type=None, title=None, details=None) -> dict:
        if status is not None:
            _check_enum(status, ITEM_STATUSES, "item status")
        if type is not None:
            _check_enum(type, ITEM_TYPES, "item type")
        if title is not None:
            _check_text(title, "title", required=True)
            _check_len(title, "title", LIMITS["title"])
        if details is not None:
            _check_text(details, "details")

        def change(p):
            item = _find(p["items"], item_id, "item")
            for key, value in (("status", status), ("type", type), ("title", title), ("details", details)):
                if value is not None:
                    item[key] = value
            return item

        return self._modify(project_id, change)

    # --- decisions ---------------------------------------------------------

    def log_decision(self, project_id, decision, reason) -> dict:
        _check_text(decision, "decision", required=True)
        _check_text(reason, "reason")

        def change(p):
            entry = {"date": _now(), "decision": decision, "reason": reason}
            p["decisions"].append(entry)
            return entry

        return self._modify(project_id, change)

    # --- inbox -------------------------------------------------------------

    def post_message(self, to_project, kind, title, body, from_project="user") -> dict:
        _check_enum(kind, MESSAGE_KINDS, "message kind")
        _check_text(title, "title", required=True)
        _check_text(body, "body")
        with self._write_lock():
            if to_project != "all":
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
            return message

    def read_inbox(self, project_id, unread_only=True) -> list[dict]:
        with self._read_lock():
            self._load(project_id)
            return [m for m in self._messages()
                    if m["to_project"] in (project_id, "all") and (not unread_only or m["status"] == "unread")]

    def mark_message(self, message_id, status) -> dict:
        _check_enum(status, MESSAGE_STATUSES, "message status")
        with self._write_lock():
            messages = self._messages()
            # shortcut: an "all" message has one shared status, so marking it marks it for everyone
            message = _find(messages, message_id, "message")
            message["status"] = status
            _write_atomic(self._inbox, "".join(json.dumps(m, sort_keys=True, ensure_ascii=False) + "\n" for m in messages))
            self.regenerate_biblia()
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
