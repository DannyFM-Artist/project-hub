# project-hub

Local project-tracking hub. Three parts share one data folder:

1. a data layer (Python, file-locked, atomic writes),
2. an MCP stdio server (`project-hub mcp`) for Claude Desktop and Claude Code,
3. a local web dashboard (`project-hub dashboard`).

Plus `project-hub session-start`, a Claude Code SessionStart hook that prints the current project's phase, next step and unread inbox. Everything is local; no auth, nothing is exposed to the network.

## Data folder

```
<data>/
  projects/<project_id>.json   one pretty-printed JSON file per project (stable key order)
  inbox/messages.jsonl         one message per line
  BIBLIA.md                    auto-regenerated after every write; paste it into any AI chat for full context
```

Pretty JSON with sorted keys, so the folder diffs cleanly and can live in git.

## Install

```
pip install -e .          # from this folder
pip install -e ".[dev]"   # plus pytest
python -m pytest
```

The `project-hub` script lands in Python's `Scripts` folder (Windows: e.g. `C:\Users\you\AppData\Local\Programs\Python\Python313\Scripts`). That folder must be on `PATH`, otherwise use the full path to `project-hub.exe` in every snippet below.

## Data folder location (important)

The data folder is `~/project-hub-data` (your home folder, e.g. `C:/Users/you/project-hub-data`), whatever directory a command is started from, so the MCP server, the dashboard and the hook always share it. Set `PROJECT_HUB_DATA` to override it; it must be an absolute path (`~` is expanded), and a relative value is rejected. The snippets below set it explicitly to the default, `C:/Users/you/project-hub-data`; drop the `env` entries if you keep the default, or change the path in every snippet together (forward slashes work on Windows; in JSON use forward slashes or escape backslashes as `\\`).

The data folder is meant to be its own git repository (`cd ~/project-hub-data && git init`). On first write project-hub creates a `.gitignore` there for its lock and temp files (`.lock`, `*.tmp`); if a `.gitignore` already exists, only the missing entries are appended.

Nothing in this repo modifies Claude config files. You paste the snippets yourself.

## Claude Desktop

Edit `claude_desktop_config.json`:

- Windows: `%APPDATA%\Claude\claude_desktop_config.json`, or for the Microsoft Store version `%LOCALAPPDATA%\Packages\Claude_<id>\LocalCache\Roaming\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "project-hub": {
      "command": "project-hub",
      "args": ["mcp"],
      "env": { "PROJECT_HUB_DATA": "C:/Users/you/project-hub-data" }
    }
  }
}
```

Desktop may not see your shell `PATH`; if the server fails to start, set `"command"` to the full path, e.g. `"C:/Users/you/AppData/Local/Programs/Python/Python313/Scripts/project-hub.exe"`. Restart Claude Desktop after editing.

## Claude Code (MCP server, user scope)

```
claude mcp add project-hub --scope user --env PROJECT_HUB_DATA=C:/Users/you/project-hub-data -- project-hub mcp
```

Put the server name first: `--env` takes multiple values and would otherwise swallow the name. Everything after `--` is the server command. Check with `claude mcp list`.

## Claude Code SessionStart hook

Add to `~/.claude/settings.json` (merge with existing `hooks`/`env` keys):

```json
{
  "env": { "PROJECT_HUB_DATA": "C:/Users/you/project-hub-data" },
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          { "type": "command", "command": "project-hub session-start" }
        ]
      }
    ]
  }
}
```

Notes (per the Claude Code hooks/settings docs): `matcher` is optional (omit it to fire on every start type; or use `startup`, `resume`, `clear`, `compact`). Plain-text stdout of a SessionStart hook is added to Claude's context. Hooks run in the session's working directory. The `env` block applies to every Claude Code run, but the docs do not explicitly say it reaches hook processes (hooks inherit Claude Code's environment), so if the hook prints nothing for a project that should match, also set `PROJECT_HUB_DATA` as a real user environment variable (Windows: `setx PROJECT_HUB_DATA C:/Users/you/project-hub-data`, then restart Claude Code). On Windows the command runs in Git Bash if installed, otherwise PowerShell.

The hook prints nothing and exits 0 when the working directory is not inside any project's `repo_path`, or when anything goes wrong (a hook must never break session start; errors go to stderr). Sample output:

```
[project-hub] Demo App (demo) — status: active
Current phase: Build (in_progress)
Next step: Write README
Unread inbox (1):
- [report] Hello — from user (id 808b4f07)
```

Set `repo_path` (absolute) when you create a project; session-start matches the working directory against it (cwd equal to or inside `repo_path`, longest match wins).

## Suggested CLAUDE.md rule (per repo)

```
## project-hub
- Update this project in project-hub as you go, not only at the end: after each completed phase or significant step, update phase status, items, decisions and next_step right away.
- Mark an inbox message "done" only when the work it asks for is actually finished; "read" means seen, not done.
- At the end of the session, post a report message summarizing what changed.
- Before using a shared resource (GPU-heavy runs, physical sensors, shared repos such as dannyfm-ui, files outside this repo), claim it in project-hub with claim_resource; release it as soon as you are done. If it is busy, do not use it: work on something else and retry later. Tests must bind to free ports chosen by the OS, never to fixed ports.
- Keep hub text short and readable at a glance: no commit hashes, file:line citations or logs in descriptions, notes or titles; details belong in the repo.
- Before starting a phase, check its gate in project-hub. If it has an unapproved review gate or a manual_test gate, do not start it: post a report message describing what is ready for review or what needs testing, and stop.
- If you judge that the next phase needs a manual review or a test by Danny (real hardware, visual approval, anything you cannot verify yourself), add a gate with set_gate and a short reason.
```

Updating as you go means a session cut off by a usage limit doesn't lose the project's state.

## Dashboard

```
project-hub dashboard
```

Opens at http://127.0.0.1:8765 (bound to 127.0.0.1 only). Uses `~/project-hub-data` unless `PROJECT_HUB_DATA` is set.

## Browser checks

`tests/browser/` holds click checks that drive the dashboard in real Chrome with Playwright. They are separate from `pytest` (which never collects them). Each script seeds a throwaway data folder in your temp directory, starts its own dashboard on a free port chosen by the OS (so it runs while the real dashboard is up on 8765) and prints `PASS`/`FAIL` lines ending in `FAILED: []` when everything passes. They need Google Chrome installed, plus Playwright in a separate virtual environment:

```
python -m venv .venv-browser
.venv-browser\Scripts\pip install playwright -e .
.venv-browser\Scripts\python tests\browser\clicks.py
```

- `clicks.py` - every dashboard action by mouse and keyboard, polling, offline banner, focus, target sizes, headings
- `shots.py` - overview order, phase position, repo in header; retakes `mockups/impl-B-overview.png` and `impl-B-project.png`
- `unread_align_check.py` - unique unread count and phase label alignment
- `longtext_check.py` - very long text at 1280/1440/1920 px: no horizontal scroll, clamps, expand
- `res_check.py` - resources pane against the real API, force release

The screenshot-taking scripts overwrite the PNGs in `mockups/`; discard those changes with `git checkout -- mockups/` if nothing visual changed.

## MCP tools

- `list_projects(status?)` - all projects, optionally filtered by status.
- `get_project(project_id)` - full project plus unread messages.
- `create_project(id, name, description, repo_path?, phases?)` - new project (id is a slug).
- `update_project(project_id, status?, description?, next_step?, repo_path?)` - change project fields.
- `add_phase(project_id, name, position?)` - add a phase.
- `set_phase_status(project_id, phase_id, status, notes?)` - todo / in_progress / done.
- `update_phase(project_id, phase_id, name?, notes?)` - rename a phase or replace its notes.
- `delete_phase(project_id, phase_id)` - remove a phase (refused for a gated phase).
- `set_gate(project_id, phase_id, gate, reason)` - add or tighten a phase gate (none → review → manual_test); agents can never remove, loosen or approve one.
- `add_item(project_id, type, title, details?)` - idea / future_request / bug.
- `update_item(project_id, item_id, status?, type?, title?, details?)` - edit or move an item.
- `log_decision(project_id, decision, reason)` - append to the decision log.
- `post_message(to_project, kind, title, body, from_project?)` - message / task / report; `to_project` may be `all`.
- `read_inbox(project_id, unread_only=true)` - messages for a project (including `all`).
- `mark_message(message_id, status)` - unread / read / done.
- `claim_resource(resource, project_id, purpose, ttl_minutes=30)` - reserve a shared resource: granted, renewed (same project) or busy (shows the holder). Never waits.
- `release_resource(resource, project_id)` - release a resource this project holds.
- `list_resources()` - all active leases.

Text limits on every write (MCP and dashboard): project description 200 characters, next_step 160, phase name 60, phase notes 240, item title 100. A longer text is refused with a message asking for a shorter one; data already stored is left as is.

## Phase gates

A gate on a phase limits how far sessions work on their own:

- `review` - no agent may start the phase until Danny approves the gate in the dashboard.
- `manual_test` - Danny does this phase himself; no agent may start it or mark it done.

Agents can add or tighten gates with `set_gate` (with a reason, at most 160 characters) and are refused when they try to start a gated phase; the refusal tells them to post a report and stop. Gates are approved, changed and removed only in the dashboard, which also lists every phase that is waiting for you. `get_project`, `session-start` and BIBLIA.md show each gate and the line "Autonomous work allowed up to phase N".

## Autonomous work with /loop

The user-level skill `~/.claude/skills/hub-sync/SKILL.md` (not part of this repo) does one round of hub-driven work in a registered repo: it reads the project id from the repo's CLAUDE.md, takes the oldest unread task or message (marks it read, does it, marks it done only when finished, posts a report), or else works on the in-progress or next allowed phase within its gates. With nothing to do it answers `hub-sync: nothing new`. Run it on a schedule from a Claude Code session in that repo:

```
/loop 5m /hub-sync
```

- It only fires while that Claude Code session is open and idle. Closing the terminal stops it; a run that comes due while Claude is busy happens once when it is idle again (no catch-up).
- Recurring loops expire 7 days after they are created: they fire one last time and delete themselves. Run the command again to continue.
- To stop it, ask Claude in the session: "cancel the hub-sync loop" (or "what scheduled tasks do I have?" to see it first). `Esc` only stops a self-paced `/loop` started without an interval.
- The skill never approves, loosens or removes a gate; you do that in the dashboard.

## Resource reservations

Several Claude Code sessions can work on different projects at once. A lease in `<data>/resources/leases.json` tells the others a shared resource is in use. Leases are exclusive and expire after `ttl_minutes` (an expired lease counts as free); claiming again from the same project renews it. The dashboard overview lists active leases with a force-release button for stale ones.

Resource names are free-form, trimmed and lowercased. Convention:

- `gpu` - GPU-heavy runs
- `device:<name>` - physical devices, e.g. `device:orbbec-femto-mega`
- `repo:<name>` - shared repos, e.g. `repo:dannyfm-ui`
- `path:<absolute path>` - files or folders outside the claiming repo
