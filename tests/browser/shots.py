"""Browser checks for overview order, phase position, repo header, label alignment, unread count; retakes both screenshots."""
import os, shutil, subprocess, sys, time, urllib.request
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
from hubserver import BASE, PORT, SERVE

S = Path(__file__).resolve().parent
D = Path(tempfile.mkdtemp(prefix="hub-browser-"))  # never the real data folder
M = S.parents[1] / "mockups"
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
time.sleep(1.1); hub.update_project("cuedeck", next_step="Map Brompton presets to OSC macro buttons")
time.sleep(1.1); hub.update_project("project-hub", next_step="Concurrent-write test with two processes")

order = ("active", "paused", "parked", "done")
expected = [p["name"] for p in sorted(sorted(hub.list_projects(), key=lambda p: p["updated_at"], reverse=True),
                                      key=lambda p: order.index(p["status"]))]
def pos(p):
    from project_hub.biblia import current_phase
    c = current_phase(p)
    return f"{p['phases'].index(c) + 1}/{len(p['phases'])}" if c else None
expected_pos = {p["name"]: pos(p) for p in hub.list_projects()}
unique = len({m["id"] for p in hub.list_projects() for m in hub.read_inbox(p["id"])})

srv = subprocess.Popen(SERVE,
                       env=dict(os.environ, PROJECT_HUB_DATA=str(D)), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
fails = []
try:
    for _ in range(50):
        try:
            urllib.request.urlopen(BASE + "/api/projects"); break
        except Exception:
            time.sleep(.2)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        pg = b.new_page(viewport={"width": 1440, "height": 800})
        errors = []
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.goto(BASE + "/#overview"); pg.wait_for_selector("tr.row"); time.sleep(.5)
        rows = pg.eval_on_selector_all("tr.row", "els => els.map(r => [r.querySelector('td.name a, td.name').firstChild.textContent.trim(), (r.querySelector('td.ph small') || {}).textContent || null])")
        names = [r[0] for r in rows]
        print("overview order:", names, "\nexpected:      ", expected)
        if names != expected: fails.append("overview order")
        for name, shown in rows:
            print(f"  {name}: phase col {shown!r}, expected {expected_pos[name]!r}")
            if shown != expected_pos[name]: fails.append(f"phase position {name}")
        top = pg.text_content("#unread").strip()
        if top != f"{unique} unread": fails.append(f"top-bar unread {top!r} != {unique}")
        pg.mouse.move(0, 0); pg.screenshot(path=str(M / "impl-B-overview.png"))

        pg.set_viewport_size({"width": 1440, "height": 1000})
        pg.goto(BASE + "/#p/framegrade"); pg.wait_for_selector("#phead h2"); time.sleep(.5)
        head = pg.text_content("#phead")
        print("header:", " ".join(head.split()))
        if not ("repo " + repos["framegrade"] in head and head.index("repo ") < head.index("next")): fails.append("repo in header before next")
        tops = pg.eval_on_selector_all(".cue", "els => els.map(e => [e.className, Math.round(e.querySelector('h4').getBoundingClientRect().top)])")
        print("phase label tops:", tops)
        if len({t[1] for t in tops}) != 1: fails.append("phase label alignment")
        pg.mouse.move(0, 0); pg.screenshot(path=str(M / "impl-B-project.png"))
        pg.goto(BASE + "/#p/led-mapper"); pg.wait_for_selector("#phead h2"); time.sleep(.4)
        if "repo " in pg.text_content("#phead"): fails.append("repo label shown for project without repo_path")
        if errors: fails.append(f"console errors {errors}")
        b.close()
finally:
    srv.terminate(); srv.wait()
print("FAILED:", fails)
