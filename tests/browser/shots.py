"""Browser checks for overview order, phase position, repo header, phase-row alignment, reports counter; screenshots go to the temp data folder."""
import os, shutil, subprocess, sys, time, urllib.request
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
from hubserver import BASE, PORT, SERVE, serve

S = Path(__file__).resolve().parent
D = Path(tempfile.mkdtemp(prefix="hub-browser-"))  # never the real data folder
subprocess.check_call([sys.executable, str(S / "seed.py"), str(D)])
from project_hub.hub import Hub
hub = Hub(D)

repos = {"framegrade": r"C:\dev\framegrade", "cuedeck": r"C:\dev\cuedeck", "moyad-studio": r"C:\dev\moyad.studio",
         "stagetimer": r"C:\dev\stagetimer-ios", "project-hub": r"C:\dev\project-hub"}
for pid, path in repos.items():  # led-mapper keeps no repo_path
    hub.update_project(pid, repo_path=path)
ph = hub.get_project("framegrade")["phases"]
notes = ["Watch folders + EDL import", "ACES 1.3, OCIO v2 configs", None, "Queue survives restart", None, None]
for p, n in zip(ph, notes):
    if n:
        hub.set_phase_status("framegrade", p["id"], p["status"], n)
hub.set_phase_status("framegrade", ph[3]["id"], "in_progress")  # 03 and 04 both in progress
cd = hub.get_project("cuedeck")["phases"]
hub.set_phase_status("cuedeck", cd[0]["id"], "done", "OSC listener on 8000")
hub.set_phase_status("cuedeck", cd[1]["id"], "done")
hub.set_phase_status("cuedeck", cd[2]["id"], "in_progress", "Tessera presets mapped")
hub.post_message("all", "report", "Weekly report to all", "+ ok", "cuedeck")  # one record, counted once in the top bar
time.sleep(1.1); hub.update_project("cuedeck", next_step="Map Brompton presets to OSC macro buttons")
time.sleep(1.1); hub.update_project("project-hub", next_step="Concurrent-write test with two processes")

order = ("active", "paused", "parked", "done")
server = sorted(sorted(hub.list_projects(), key=lambda p: p["updated_at"], reverse=True), key=lambda p: order.index(p["status"]))
reports = lambda pid: [m for m in hub._messages() if m["to_project"] in (pid, "all") and m["kind"] == "report" and m["status"] == "unread"]
expected = [p["name"] for p in sorted(server, key=lambda p: -len(reports(p["id"])))]  # most unread reports first (no gates here), then the server order
def pos(p):
    from project_hub.biblia import current_phase
    c = current_phase(p)
    return f"{p['phases'].index(c) + 1:02d}" if c and c["status"] != "done" else None
expected_pos = {p["name"]: pos(p) for p in hub.list_projects()}
unique = len({m["id"] for p in hub.list_projects() for m in reports(p["id"])})

srv = serve(D)
fails = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        pg = b.new_page(viewport={"width": 1440, "height": 800})
        errors = []
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.goto(BASE + "/#overview"); pg.wait_for_selector("#ov-body .row"); time.sleep(.5)
        rows = pg.eval_on_selector_all("#ov-body .row", "els => els.map(r => [r.querySelector('.nm a').textContent.trim(), (r.querySelector('.cp .n') || {textContent: ''}).textContent.trim() || null])")
        names = [r[0] for r in rows]
        print("overview order:", names, "\nexpected:      ", expected)
        if names != expected: fails.append("overview order")
        for name, shown in rows:
            print(f"  {name}: phase col {shown!r}, expected {expected_pos[name]!r}")
            if shown != expected_pos[name]: fails.append(f"phase position {name}")
        top = pg.text_content("#repcount b").strip()
        print("top-bar reports:", top, "expected", unique)
        if top != str(unique): fails.append(f"top-bar reports {top!r} != {unique}")
        pg.mouse.move(0, 0); pg.screenshot(path=str(D / "overview.png"))

        pg.set_viewport_size({"width": 1440, "height": 1000})
        pg.goto(BASE + "/#p/framegrade"); pg.wait_for_selector("#phead h1"); time.sleep(.5)
        head = pg.text_content("#phead")
        print("header:", " ".join(head.split()))
        if pg.text_content("#phead .repo") != repos["framegrade"]: fails.append("repo in header")
        pg.click('[data-fk="done|framegrade"]'); time.sleep(.3)
        lefts = pg.eval_on_selector_all("#phases .row", "els => els.map(e => [Math.round(e.querySelector('.n').getBoundingClientRect().left), Math.round(e.querySelector('.nm').getBoundingClientRect().left)])")
        print("phase number / name lefts:", lefts)
        if len({tuple(x) for x in lefts}) != 1: fails.append("phase row alignment")
        pg.mouse.move(0, 0); pg.screenshot(path=str(D / "project.png"))
        pg.goto(BASE + "/#p/led-mapper"); pg.wait_for_selector("#phead h1"); time.sleep(.4)
        if pg.query_selector("#phead .repo"): fails.append("repo shown for project without repo_path")
        if errors: fails.append(f"console errors {errors}")
        print("screenshots in", D)
        b.close()
finally:
    srv.terminate(); srv.wait()
print("FAILED:", fails)
