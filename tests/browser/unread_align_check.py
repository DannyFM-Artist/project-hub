"""Top-bar reports counter counts each unread report once (a report to "all" too); phase rows stay aligned."""
import os, shutil, subprocess, sys, time, urllib.request
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
from hubserver import BASE, PORT, SERVE

S = Path(__file__).resolve().parent
D = Path(tempfile.mkdtemp(prefix="hub-browser-"))  # never the real data folder
subprocess.check_call([sys.executable, str(S / "seed.py"), str(D)])
from project_hub.hub import Hub
hub = Hub(D)
ph = hub.get_project("framegrade")["phases"]
hub.set_phase_status("framegrade", ph[3]["id"], "in_progress")  # 03 has notes, 04 has none: two in_progress in a row
hub.post_message("all", "report", "Report to all", "+ ok", "cuedeck")

reps = lambda pid: [m["id"] for m in hub.read_inbox(pid) if m["kind"] == "report"]
unique = len({i for p in hub.list_projects() for i in reps(p["id"])})
per_project_sum = sum(len(reps(p["id"])) for p in hub.list_projects())

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
        pg.goto(BASE + "/#p/framegrade"); pg.wait_for_selector("#phead h1"); time.sleep(.5)
        top = pg.text_content("#repcount b").strip()
        print(f"top bar: {top!r}; unique unread reports = {unique}; per-project sum = {per_project_sum}")
        if top != str(unique) or unique == per_project_sum: fails.append("top-bar reports counter")
        pg.click('[data-fk="done|framegrade"]'); time.sleep(.3)
        rows = pg.eval_on_selector_all("#phases .row", "els => els.map(e => [e.dataset.id, e.querySelector('.n').getBoundingClientRect().left, e.querySelector('.nm').getBoundingClientRect().left])")
        for r in rows: print("phase", r)
        if len({round(r[1]) for r in rows}) != 1 or len({round(r[2]) for r in rows}) != 1: fails.append("phase row alignment")
        pg.goto(BASE + "/#overview"); pg.wait_for_selector("#ov-body .row"); time.sleep(.3)
        counts = pg.eval_on_selector_all("#ov-body .row", "els => els.map(e => e.querySelector('.nm a').textContent + ':' + e.children[6].textContent)")
        print("overview per-project report counts:", counts)
        if "framegrade:2" not in counts or "cuedeck:1" not in counts: fails.append("per-project report counts")
        if errors: fails.append(f"console errors {errors}")
        b.close()
finally:
    srv.terminate(); srv.wait()
print("FAILED:", fails)
