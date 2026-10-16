"""Local dashboard backend: JSON API over Hub plus the static page."""

from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import hub as hub_module  # module reference so a faked hub._utcnow applies here too
from .biblia import GATE_DEFAULTS, autonomy_line, current_phase, waiting
from .hub import Hub, HubError, overview_order

STATIC = Path(__file__).parent / "static"
ICONS = STATIC / "icons"  # app icons and web manifest; regenerate the PNGs with tools/make_icons.py

app = FastAPI(title="project-hub")
_hub: Hub | None = None  # tests may replace this with Hub(tmp_path)


def hub() -> Hub:
    global _hub
    if _hub is None:
        _hub = Hub()
    return _hub


@app.exception_handler(HubError)
async def _hub_error(request: Request, exc: HubError):
    msg = str(exc)
    return JSONResponse({"error": msg}, status_code=404 if msg.startswith("unknown ") else 400)


class PhaseIn(BaseModel):
    status: str
    notes: str | None = None


class ItemIn(BaseModel):
    type: str
    title: str
    details: str = ""


class ItemPatch(BaseModel):
    status: str | None = None
    type: str | None = None
    title: str | None = None
    details: str | None = None


class MessageIn(BaseModel):
    to_project: str
    kind: str
    title: str
    body: str
    from_project: str = "user"


class MessagePatch(BaseModel):
    status: str


@app.get("/api/projects")
def list_projects():
    h = hub()
    out = []
    for p in h.list_projects():
        cur = current_phase(p)
        out.append({
            "id": p["id"], "name": p["name"], "status": p["status"], "description": p["description"],
            "next_step": p["next_step"], "updated_at": p["updated_at"],
            "current_phase": cur["name"] if cur else None,
            "current_phase_pos": p["phases"].index(cur) + 1 if cur else None,  # 1-based position in the phase list
            "phases_done": sum(ph["status"] == "done" for ph in p["phases"]),
            "phases_total": len(p["phases"]),
            "unread_count": len(h.read_inbox(p["id"])),
        })
    return overview_order(out)


@app.get("/api/unread")
def unread_total():
    """Unique unread messages across all projects: a message to "all" is one record, counted once."""
    h = hub()
    return {"count": len({m["id"] for p in h.list_projects() for m in h.read_inbox(p["id"])})}


@app.get("/api/projects/{project_id}")
def get_project(project_id: str):
    project = hub().get_project(project_id)
    project["phases"] = [{**GATE_DEFAULTS, **ph} for ph in project["phases"]]
    project["autonomy"] = autonomy_line(project)
    project["inbox"] = sorted(hub().read_inbox(project_id, unread_only=False),
                              key=lambda m: m["created_at"], reverse=True)
    return project


# the dashboard is Danny: every change here is by="dashboard", which gates treat like by="user"
@app.post("/api/projects/{project_id}/phases/{phase_id}")
def set_phase(project_id: str, phase_id: str, body: PhaseIn):
    return hub().set_phase_status(project_id, phase_id, body.status, body.notes, by="dashboard")


class GateIn(BaseModel):
    gate: str
    reason: str = ""


@app.post("/api/projects/{project_id}/phases/{phase_id}/gate")
def set_gate(project_id: str, phase_id: str, body: GateIn):
    return hub().set_gate(project_id, phase_id, body.gate, body.reason, by="dashboard")


@app.post("/api/projects/{project_id}/phases/{phase_id}/gate/approve")
def approve_gate(project_id: str, phase_id: str):
    return hub().approve_gate(project_id, phase_id, by="dashboard")


@app.get("/api/waiting")
def list_waiting():
    return waiting(hub().list_projects())


@app.post("/api/projects/{project_id}/items")
def add_item(project_id: str, body: ItemIn):
    return hub().add_item(project_id, body.type, body.title, body.details, by="dashboard")


@app.patch("/api/projects/{project_id}/items/{item_id}")
def update_item(project_id: str, item_id: str, body: ItemPatch):
    return hub().update_item(project_id, item_id, **body.model_dump(exclude_none=True), by="dashboard")


@app.post("/api/messages")
def post_message(body: MessageIn):
    return hub().post_message(body.to_project, body.kind, body.title, body.body, body.from_project)


@app.patch("/api/messages/{message_id}")
def mark_message(message_id: str, body: MessagePatch):
    return hub().mark_message(message_id, body.status, by="dashboard")


class ReleaseIn(BaseModel):
    resource: str


@app.get("/api/resources")
def list_resources():
    now = hub_module._utcnow()
    return [{**l, "seconds_left": max(0, int((datetime.fromisoformat(l["expires_at"]) - now).total_seconds()))}
            for l in hub().list_resources()]


@app.post("/api/resources/release")
def force_release(body: ReleaseIn):
    return hub().force_release(body.resource)


class SeenIn(BaseModel):
    at: str | None = None


@app.get("/api/summary")
def get_summary(since: str | None = None, hours: int | None = None):
    return hub().summary(since=since, hours=hours)


@app.post("/api/summary/seen")
def summary_seen(body: SeenIn | None = None):
    return hub().mark_summary_seen(body.at if body else None)


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/favicon.svg")
def favicon_svg():
    return FileResponse(ICONS / "favicon.svg", media_type="image/svg+xml")


@app.get("/favicon.ico")
def favicon_ico():
    return FileResponse(ICONS / "icon-32.png", media_type="image/png")


@app.get("/manifest.webmanifest")
def manifest():
    return FileResponse(ICONS / "manifest.webmanifest", media_type="application/manifest+json")


app.mount("/icons", StaticFiles(directory=ICONS), name="icons")


def main():
    uvicorn.run(app, host="127.0.0.1", port=8765)
