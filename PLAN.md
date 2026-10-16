# project-hub — build plan

Local project-tracking hub: data layer + MCP stdio server + local web dashboard + session-start CLI, sharing one data folder.
Full spec: see "Spec" at the bottom of this file. Keep code minimal (no abstractions nobody asked for).

## Layout

```
pyproject.toml            # name project-hub, requires-python >=3.11, deps: mcp, fastapi, uvicorn, filelock; extra dev: pytest
                          # [project.scripts] project-hub = "project_hub.cli:main"
project_hub/
  __init__.py
  hub.py                  # data layer (phase 1)
  biblia.py               # BIBLIA.md renderer (phase 1)
  mcp_server.py           # FastMCP stdio server (phase 2)
  web.py                  # FastAPI app + uvicorn runner (phase 3 backend)
  static/index.html       # dashboard page (phase 3 frontend, gated on Danny's mockup choice)
  cli.py                  # argparse: mcp | dashboard | session-start (phase 4)
tests/                    # pytest, always tmp_path, never ./data
mockups/                  # dashboard design options for Danny (not shipped)
README.md                 # phase 4
```

## Data-layer contract (phase 1 defines it; phases 2-4 only consume it)

```python
class HubError(ValueError): ...           # every invalid id / value raises this, with a clear message

def data_dir() -> Path                    # PROJECT_HUB_DATA (absolute, ~ expanded) else Path.home()/"project-hub-data"; never cwd-relative

class Hub:
    def __init__(self, data_dir: Path | str | None = None)   # None -> data_dir()
    # projects
    def list_projects(self, status: str | None = None) -> list[dict]
    def get_project(self, project_id) -> dict                 # full project + key "unread_messages": [msg, ...]
    def create_project(self, id, name, description, repo_path=None, phases: list[str] | None = None) -> dict
    def update_project(self, project_id, *, status=None, description=None, next_step=None, repo_path=None) -> dict
    # phases
    def add_phase(self, project_id, name, position: int | None = None) -> dict        # returns the phase
    def set_phase_status(self, project_id, phase_id, status, notes=None) -> dict      # returns the phase
    # items
    def add_item(self, project_id, type, title, details="") -> dict                   # returns the item
    def update_item(self, project_id, item_id, *, status=None, type=None, title=None, details=None) -> dict
    # decisions
    def log_decision(self, project_id, decision, reason) -> dict
    # inbox
    def post_message(self, to_project, kind, title, body, from_project="user") -> dict
    def read_inbox(self, project_id, unread_only=True) -> list[dict]
    def mark_message(self, message_id, status) -> dict
    # misc
    def regenerate_biblia(self) -> None
    def find_project_for_path(self, path) -> dict | None
```

Rules:
- Project id: slug `^[a-z0-9][a-z0-9-]*$`, validated; duplicate id -> HubError.
- Phase / item / message ids: short random hex (`uuid4().hex[:8]`), unique within their list.
- Enums: project status active|paused|parked|done; phase todo|in_progress|done; item type idea|future_request|bug; item status open|planned|done|discarded; message kind message|task|report; message status unread|read|done. Bad value -> HubError listing allowed values.
- `to_project` must be an existing project id or "all"; `from_project` must be an existing project id or "user".
- Messages to "all": stored once with to_project="all"; read_inbox(pid) and unread counts include to_project in (pid, "all"). shortcut: marking an "all" message marks it for everyone.
- "Current phase" = first phase with status in_progress, else first todo, else last phase, else none.
- Timestamps: ISO 8601 UTC with seconds (`datetime.now(timezone.utc).isoformat(timespec="seconds")`). `updated_at` set on every project write; decision `date` = same format.
- New projects: status active, next_step "", empty items/decisions, phases from the given names (status todo, notes "").

Concurrency / files:
- One global `FileLock(data_dir / ".lock")`, held for every read and every read-modify-write, including BIBLIA regeneration. (On Windows `os.replace` fails if another process has the target open.)
- Atomic write: temp file in the same directory as the target, then `os.replace`.
- JSON: `json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n"`. Inbox `.jsonl`: one `sort_keys=True` JSON object per line. post_message appends; mark_message rewrites the whole file atomically.
- After every write (project or inbox), regenerate `data/BIBLIA.md` while still holding the lock.
- Missing data folder: created on first write; reads on a missing folder return empty results, never crash.
- Nothing in the package prints to stdout except the CLI's session-start output (stdout is the MCP protocol channel). Logging goes to stderr.

BIBLIA.md: header + generated timestamp; index table (name, id, status, current phase, next step, updated_at); then one section per project: description, repo_path, status, next step, phases (with status and notes), open items (status open or planned, grouped by type), last 5 decisions, unread inbox count and unread titles. Must be enough for an AI chat to recover full context.

session-start matching: `Path(cwd).resolve()` vs `Path(repo_path).resolve()`, compared with `os.path.normcase`, cwd equal to or inside repo_path; longest repo_path wins; projects without repo_path skipped. No match / no data folder -> None.

## Phases

1. Data layer + tests (heavy-implementer). Tests: create/update ops and validation errors, concurrent writes from two `subprocess.Popen([sys.executable, "-c", ...])` processes (assert no lost items), BIBLIA regeneration content, session-start matching (nested paths, no match, case on Windows).
2. MCP server (feature): FastMCP stdio, one tool per spec entry, thin wrappers over Hub. Each tool catches HubError and returns `"Error: ..."`. Concise structured text output.
3. Dashboard backend (feature): FastAPI JSON routes over Hub, bound to 127.0.0.1:8765, HubError -> 400 (unknown id -> 404), serves static/index.html. Frontend: GATED. Mockups first; Danny picks; then ui-implementer builds it; Danny approves screenshots.
4. CLI + README (feature): `project-hub mcp|dashboard|session-start`; README with install, Claude Desktop config JSON, `claude mcp add --scope user`, SessionStart hook snippet, suggested CLAUDE.md rule. Tell the user to set PROJECT_HUB_DATA to an absolute path in every snippet. Never modify global Claude config.

## Dashboard API (phase 3 backend, contract for the UI)

Errors: HubError -> `{"error": msg}`, 404 if msg starts with "unknown ", else 400; malformed body -> 422.
- GET /api/projects -> [{id, name, status, description, next_step, updated_at, current_phase (name|null), current_phase_pos (1-based|null), phases_done, phases_total, unread_count}], sorted by status (active, paused, parked, done) then updated_at newest first
- GET /api/unread -> {count}: unique unread message ids (a message to "all" counts once)
- GET /api/projects/{id} -> get_project fields (incl. phases, items, decisions, unread_messages) + `inbox`: all messages to id or "all", newest first
- POST /api/projects/{id}/phases/{phase_id} {status, notes?} -> phase
- POST /api/projects/{id}/items {type, title, details?} -> item
- PATCH /api/projects/{id}/items/{item_id} {status?, type?, title?, details?} -> item
- POST /api/messages {to_project, kind, title, body, from_project?} -> message
- PATCH /api/messages/{message_id} {status} -> message
- GET / -> static/index.html

## Resource leases (contract, 2026-10-16)

Data: `<data>/resources/leases.json`, a JSON list (pretty, sorted keys, sorted by resource) of
`{resource, project_id, purpose, acquired_at, expires_at}` (ISO 8601 UTC, seconds). Same lock + atomic write as everything else; BIBLIA regenerated after every lease write.
Resource names: `resource.strip().lower()`; empty -> HubError. Convention: `gpu`, `device:<name>`, `repo:<name>`, `path:<absolute path>`.
Exclusive. A lease with expires_at <= now is free; expired leases are dropped on the next lease write (reads just filter them out). Time comes from a module-level `_utcnow() -> datetime` in hub.py so tests can fake it.

Hub methods:
- `claim_resource(resource, project_id, purpose, ttl_minutes=30) -> {"status": "granted"|"renewed"|"busy", "lease": {...}}`. project_id must exist; ttl_minutes int 1..1440 (bool rejected); purpose str. Free/expired -> granted (new acquired_at). Held by same project -> renewed (keeps acquired_at, new purpose + expires_at). Held by another -> busy, lease = the holder's lease, nothing written. Never waits.
- `release_resource(resource, project_id) -> lease`. Not held -> HubError "resource 'x' is not claimed"; held by another -> HubError naming the holder.
- `list_resources() -> [lease]` active only, sorted by resource.
- `force_release(resource) -> lease` (dashboard). Not held -> HubError starting "unknown resource".

MCP tools: `claim_resource`, `release_resource`, `list_resources` (text; busy is a normal result line naming holder, purpose, expires_at, not "Error:").
API: `GET /api/resources` -> `[{resource, project_id, purpose, acquired_at, expires_at, seconds_left}]` (seconds_left computed server-side, int >= 0); `POST /api/resources/release {resource}` -> force_release (404 if not held).
BIBLIA.md: "## Active resources" table (resource, project, purpose, expires) after the index table, "(none)" when empty. `biblia.render` gains a `leases=()` parameter.
Dashboard: overview gets a "resources" pane under projects (resource, project, purpose, time left, force release with confirm), refreshed by the existing 5 s poll; host text in the status bar uses `location.host`, not a hard-coded port.

## Phase gates (contract, 2026-10-16)

Phase fields (optional, defaults when missing; stored data is never rewritten just to add them): `gate` none|review|manual_test (default "none"), `gate_reason` str ≤160 (default ""), `gate_set_by` "user"|"agent"|null, `gate_approved` bool (default false). Strictness order none < review < manual_test.
A phase is **blocking** when its status is not done and (gate == review and not gate_approved, or gate == manual_test).

Hub (hub.py):
- `set_gate(project_id, phase_id, gate, reason="", *, by="agent") -> phase`. by="agent": gate must be strictly stricter than the current gate (adding or tightening only; same gate, none, or looser -> HubError explaining agents can only add or tighten gates and that only Danny removes, loosens or approves them in the dashboard); reason required (non-empty). by="user": any gate; "none" clears reason/set_by/approved. Any change of gate type resets gate_approved to false. reason ≤160 (LIMITS["gate_reason"]). gate_set_by = by.
- `approve_gate(project_id, phase_id) -> phase`: user only (dashboard); only for an unapproved review gate, else HubError.
- `set_phase_status(..., *, by="agent")`: by="agent" refuses moving to in_progress or done when gate == review and not approved, and refuses in_progress or done when gate == manual_test. Error: `phase '<name>' is gated (<review, not approved | manual_test>): <reason>. Post a report message describing what is ready for review (or what needs testing), then stop.` by="user" (dashboard) is never refused.
- `delete_phase` (MCP/agents) refuses a phase that has a gate, so agents cannot remove a gate by deleting its phase.
- biblia.py pure helpers: `blocking(phase) -> bool`, `autonomy_limit(project) -> int` (number of phases before the first blocking phase; len(phases) if none), `autonomy_line(project) -> str`: `Autonomous work allowed up to phase N` (+ ` (<phase name>)` when N > 0; `Autonomous work allowed up to phase 0 (phase 1 is gated)` when the first phase blocks), `waiting(projects) -> [{project_id, project_name, phase_id, phase_name, gate, gate_reason, gate_set_by}]`: blocking phases whose previous phases are all done, in project order.
- BIBLIA: phase lines show `[gate: review, approved|not approved, set by agent] reason`; a `## Waiting for Danny` section (after Active resources) from `waiting()`, "(none)" when empty; each project section shows its autonomy line.
- MCP: new `set_gate(project_id, phase_id, gate, reason)` (always by="agent"); `set_phase_status` uses by="agent"; `get_project` text shows each gated phase's gate, reason, approved state and set_by, plus the autonomy line. CLI session-start output: same gated-phase lines and the autonomy line.
- API (dashboard acts as the user): existing `POST /api/projects/{id}/phases/{phase_id}` passes by="user"; `POST /api/projects/{id}/phases/{phase_id}/gate {gate, reason?}` -> set_gate(by="user"); `POST /api/projects/{id}/phases/{phase_id}/gate/approve` -> approve_gate; `GET /api/waiting` -> waiting(); `GET /api/projects/{id}` phases carry the gate fields with defaults filled in (gate "none", etc.) plus `autonomy` (the line).

## Progress log
- 2026-10-16: plan written.
- 2026-10-16: phase 1 done (26 tests pass, verified by director). Reserved project ids "all"/"user"; missing-id errors start with "unknown "; update_project(repo_path="") clears it; find_project_for_path returns get_project shape. Phase 1 review, phases 2, 3-backend, 4 and dashboard mockups running in parallel.
- 2026-10-16: phase 1 review fixed: inbox split on "\n" only (U+2028 corrupted inbox), phases must be a list, bool position rejected, BIBLIA titles single-line. Phase 2 done (mcp 2.x: `mcp.server.mcpserver.MCPServer`, pinned mcp>=2). Phase 3 backend done; unread count now via locked read_inbox. 35 tests pass.
- 2026-10-16: Danny chose mockup option B (Console); ui-implementer building static/index.html. Phase 4 done (cli.py, README). Director smoke test: `project-hub session-start` output OK, `project-hub dashboard` serves API + page, `project-hub mcp` answers initialize over stdio. 35 tests pass.
- 2026-10-16: dashboard frontend built (Console, `--dim`/`--faint` raised for contrast). Not yet click-tested; ui-implementer running a Playwright click-through (scratch venv). Then Danny approves screenshots. Added PRODUCT.md (impeccable init) and design-system/MASTER.md (tokens).
- 2026-10-16: data folder default moved to ~/project-hub-data (Danny's request; spec's ./data superseded). Relative PROJECT_HUB_DATA rejected. Data folder gets a .gitignore (.lock, *.tmp) on first write, merged into an existing one. tests/conftest.py isolates every test (PROJECT_HUB_DATA + HOME/USERPROFILE to tmp) and fails the session if the real ~/project-hub-data changes. 40 tests pass.
- 2026-10-16: dashboard click-tested in Chrome via Playwright (scratch venv, scratchpad ui_test.py): 10 functional checks + target size + headings all PASS, rerun by director. Awaiting Danny's approval of mockups/impl-B-*.png.
- 2026-10-16: top-bar unread now counts unique ids via new GET /api/unread {"count"}; per-project counts unchanged (include "all"). Phase card button pinned to top so labels align. 41 tests pass; click checks all PASS; fix_check.py confirms 4 unique vs 9 old sum and identical label tops.
- 2026-10-16: overview sorted by status then updated_at desc (server side); phase column shows current phase position (current_phase_pos/total); repo already in project header before "next" (verified, unchanged). 42 tests pass; click checks + shots.py all PASS; screenshots retaken with repo paths and phase notes.
- 2026-10-16: Danny's handover marks the dashboard approved (mockup B). README's suggested CLAUDE.md rule replaced with the "update as you go" rule. All four phases done. Remaining steps are setup on Danny's side (GitHub repos, Claude configs, Tailscale, real projects, dashboard autostart).
- 2026-10-16 (Danny approved each): code repo initialised (first commit 57bd7fd on main, no remote yet); ~/project-hub-data created with git init + .gitignore, nothing committed; Startup-folder shortcut runs `project-hub dashboard` minimized at login (running now); Claude Desktop (Store config path) mcpServers.project-hub added; `claude mcp add --scope user project-hub` (connected); SessionStart hook appended in ~/.claude/settings.json. Backups of both JSON configs in the session scratchpad.
- 2026-10-16: resource leases (contract above) in hub/biblia/MCP/API + overview "resources" pane; status bar uses location.host. Long-text layout: fixed-layout tables, wrapping/breaking everywhere, overview description clamp 2 lines, phase notes clamp 4 lines with click/Enter expand, full description in project header. New MCP tools update_phase/delete_phase; length limits (description 200, next_step 160, phase name 60, notes 240, item title 100) enforced in Hub. README rules added. Click tests use an OS-chosen free port (scratchpad hubserver.py). 85 tests pass; ui_test, shots, longtext_check, res_check all FAILED: []. Real dashboard restarted on the new code. Not committed.
- 2026-10-16: phase gates (contract above) in hub/biblia/MCP/CLI/API + dashboard badges, controls, "waiting for you" pane, autonomy line; agents cannot delete a gated phase. README + CLAUDE.md rules. 106 tests; all 6 tests/browser scripts FAILED: []. Real dashboard restarted. Hub: review gate on the project-hub gates phase pending Danny's screenshot approval; report posted. Not committed.

## Spec

(verbatim from Danny's request)

Build a local project-tracking hub called "project-hub". It has three parts that share one data folder: a data layer, an MCP server (stdio) used by Claude Code and Claude Desktop, and a local web dashboard. Everything runs locally only; no auth, no internet exposure.

Tech: Python 3.11+, cross-platform (pathlib; must work on Windows). MCP server: official MCP Python SDK (`mcp`, FastMCP), stdio. Dashboard: FastAPI + a single static HTML/CSS/vanilla JS page, no build step, no npm. Concurrency: filelock around every read-modify-write, atomic writes. Data folder from env PROJECT_HUB_DATA, default ./data, git-friendly (pretty JSON, stable key order).

Data model: data/projects/<project_id>.json — id (slug), name, description, repo_path (absolute, optional), status active|paused|parked|done; phases: ordered list of {id, name, status todo|in_progress|done, notes}; items: list of {id, type idea|future_request|bug, title, details, status open|planned|done|discarded, created_at}; decisions: list of {date, decision, reason}; next_step (string), updated_at (ISO 8601).
data/inbox/messages.jsonl — id, created_at, from_project (or "user"), to_project, kind message|task|report, title, body, status unread|read|done.
After every write regenerate data/BIBLIA.md: index table (name, status, current phase, next step, updated_at), then one section per project with phases, open items, recent decisions and unread inbox count. Any AI chat must recover full context from it alone.

MCP tools: list_projects(status filter optional); get_project(project_id): full project plus unread messages; create_project(id, name, description, repo_path optional, phases optional); update_project(project_id, fields: status, description, next_step, repo_path); add_phase(project_id, name, position optional); set_phase_status(project_id, phase_id, status, notes optional); add_item(project_id, type, title, details optional); update_item(project_id, item_id, status and/or fields); log_decision(project_id, decision, reason); post_message(to_project, kind, title, body, from_project optional), to_project may be "all"; read_inbox(project_id, unread_only default true); mark_message(message_id, status). Concise structured text; invalid ids/values -> clear error, never a crash.

Dashboard (http://127.0.0.1:8765): bind 127.0.0.1 only, poll every 5 s. Overview: card per project with status badge, current phase, progress bar (done phases / total), next step, unread count. Project view: horizontal phase timeline; kanban for items with columns open/planned/done (discarded behind a toggle) and filter by type; decisions log; inbox feed with reports visually distinct from messages and tasks. From the UI: change phase status, add item, move item between columns, post message, mark message read or done — all through the same data layer. Visual: dark, clean, modern, readable at a glance.

Session-start: `project-hub session-start` reads cwd, finds the project whose repo_path contains it, prints phase, next step and unread inbox; no match -> prints nothing, exit 0. Used as a Claude Code SessionStart hook.

Packaging/docs: `pip install -e .` exposing `project-hub mcp`, `project-hub dashboard`, `project-hub session-start`. README: install steps; Claude Desktop claude_desktop_config.json snippet; `claude mcp add` at user scope; SessionStart hook snippet for ~/.claude/settings.json; suggested repo CLAUDE.md rule ("At the end of each session, update this project in project-hub: phase status, items, decisions, next_step, and post a report message"). Do NOT modify global Claude config files.

Tests: pytest for the data layer: create/update, concurrent writes from two processes, BIBLIA.md regeneration, session-start matching.
