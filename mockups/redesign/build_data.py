"""Snapshot the real hub data (read-only) into data.js for the redesign mockups."""
import json, sys
from datetime import datetime, timezone
from pathlib import Path

src = Path.home() / "project-hub-data"
out = Path(__file__).resolve().parent / "data.js"
projects = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((src / "projects").glob("*.json"))]
messages = [json.loads(l) for l in (src / "inbox" / "messages.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
leases_file = src / "resources" / "leases.json"
leases = json.loads(leases_file.read_text(encoding="utf-8")) if leases_file.exists() else []
data = {"snapshot": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "projects": projects, "messages": messages, "leases": leases}
js = (Path(__file__).resolve().parent / "stress.js").read_text(encoding="utf-8")
out.write_text("// Copy of the real project-hub data, taken by build_data.py. Do not edit by hand.\n"
               "window.HUB = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n" + js, encoding="utf-8")
print(f"wrote {out}: {len(projects)} projects, {len(messages)} messages")
