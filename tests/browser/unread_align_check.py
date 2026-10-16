"""Check the two fixes in a real browser: unique top-bar unread count, phase labels aligned. Retakes the project screenshot."""
import os, shutil, subprocess, sys, time, urllib.request
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
from hubserver import BASE, PORT, SERVE

S = Path(__file__).resolve().parent
D = Path(tempfile.mkdtemp(prefix="hub-browser-"))  # never the real data folder
SHOT = S.parents[1] / "mockups" / "impl-B-project.png"
subprocess.check_call([sys.executable, str(S / "seed.py"), str(D)])
from project_hub.hub import Hub
hub = Hub(D)
ph = hub.get_project("framegrade")["phases"]
hub.set_phase_status("framegrade", ph[3]["id"], "in_progress")  # 03 has notes, 04 has none: two in_progress in a row

unique = len({m["id"] for p in hub.list_projects() for m in hub.read_inbox(p["id"])})
per_project_sum = sum(len(hub.read_inbox(p["id"])) for p in hub.list_projects())

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
        pg = b.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.goto(BASE + "/#p/framegrade"); pg.wait_for_selector("#phead h2"); time.sleep(.5)
        top = pg.text_content("#unread").strip()
        print(f"top bar: {top!r}; unique unread = {unique}; old per-project sum = {per_project_sum}")
        if top != f"{unique} unread": fails.append("top-bar unread")
        rows = pg.eval_on_selector_all(".cue", "els => els.map(e => [e.className, e.querySelector('h4').getBoundingClientRect().top, e.querySelector('.n').getBoundingClientRect().top])")
        for r in rows: print("phase", r)
        if len({round(r[1]) for r in rows}) != 1 or len({round(r[2]) for r in rows}) != 1: fails.append("phase label alignment")
        pg.goto(BASE + "/#overview"); pg.wait_for_selector("tr.row"); time.sleep(.3)
        badges = pg.eval_on_selector_all("td .inb", "els => els.map(e => e.textContent)")
        print("overview per-project badges:", badges)
        pg.goto(BASE + "/#p/framegrade"); pg.wait_for_selector("#phead h2"); time.sleep(.5)
        pg.mouse.move(0, 0)
        pg.screenshot(path=str(SHOT))
        if errors: fails.append(f"console errors {errors}")
        b.close()
finally:
    srv.terminate(); srv.wait()
print("FAILED:", fails)
