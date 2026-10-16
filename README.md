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

- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
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
```

Updating as you go means a session cut off by a usage limit doesn't lose the project's state.

## Dashboard

```
project-hub dashboard
```

Opens at http://127.0.0.1:8765 (bound to 127.0.0.1 only). Set `PROJECT_HUB_DATA` in the shell first (same absolute path).

## MCP tools

- `list_projects(status?)` - all projects, optionally filtered by status.
- `get_project(project_id)` - full project plus unread messages.
- `create_project(id, name, description, repo_path?, phases?)` - new project (id is a slug).
- `update_project(project_id, status?, description?, next_step?, repo_path?)` - change project fields.
- `add_phase(project_id, name, position?)` - add a phase.
- `set_phase_status(project_id, phase_id, status, notes?)` - todo / in_progress / done.
- `add_item(project_id, type, title, details?)` - idea / future_request / bug.
- `update_item(project_id, item_id, status?, type?, title?, details?)` - edit or move an item.
- `log_decision(project_id, decision, reason)` - append to the decision log.
- `post_message(to_project, kind, title, body, from_project?)` - message / task / report; `to_project` may be `all`.
- `read_inbox(project_id, unread_only=true)` - messages for a project (including `all`).
- `mark_message(message_id, status)` - unread / read / done.
