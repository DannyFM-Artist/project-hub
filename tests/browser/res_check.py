"""Resources pane against the real backend: leases claimed via Hub, rendering, force release, screenshot."""
import os, shutil, subprocess, sys, time, urllib.request
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
from hubserver import BASE, SERVE

S = Path(__file__).resolve().parent
D = Path(tempfile.mkdtemp(prefix="hub-browser-"))  # never the real data folder
SHOT = S.parents[1] / "mockups" / "impl-B-overview-resources.png"
subprocess.check_call([sys.executable, str(S / "seed.py"), str(D)])
from project_hub.hub import Hub
hub = Hub(D)
assert hub.claim_resource("GPU ", "framegrade", "NVDEC batch encode", 45)["status"] == "granted"
assert hub.claim_resource("device:orbbec-femto-mega", "cuedeck", "depth calibration", 10)["status"] == "granted"
assert hub.claim_resource("repo:dannyfm-ui", "project-hub", "theme tokens", 125)["status"] == "granted"
assert hub.claim_resource("gpu", "cuedeck", "x")["status"] == "busy"

srv = subprocess.Popen(SERVE, env=dict(os.environ, PROJECT_HUB_DATA=str(D)), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
fails = []
def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name, extra); ok or fails.append(name)
try:
    for _ in range(50):
        try:
            urllib.request.urlopen(BASE + "/api/resources"); break
        except Exception:
            time.sleep(.2)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        errors = []
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.goto(BASE + "/#overview"); pg.wait_for_selector("#rs-body tr"); time.sleep(.5)
        rows = pg.eval_on_selector_all("#rs-body tr", "rs => rs.map(r => [...r.cells].slice(0, 4).map(c => c.textContent.trim()))")
        for r in rows: print("  row", r)
        check("3 leases listed, sorted, project names", [r[0] for r in rows] == ["device:orbbec-femto-mega", "gpu", "repo:dannyfm-ui"]
              and [r[1] for r in rows] == ["cuedeck", "framegrade", "project-hub"], rows)
        check("time left format", rows[0][3] in ("10m", "9m") and rows[1][3] in ("45m", "44m") and rows[2][3] in ("2h 05m", "2h 04m"), [r[3] for r in rows])
        pg.mouse.move(0, 0); pg.screenshot(path=str(SHOT), full_page=True)
        pg.once("dialog", lambda d: (print("  dialog:", d.message), d.accept()))
        pg.click("#rs-body tr:nth-child(1) button"); time.sleep(1.2)
        left = [l["resource"] for l in hub.list_resources()]
        check("force release via dashboard", left == ["gpu", "repo:dannyfm-ui"], left)
        check("pane updated", pg.eval_on_selector_all("#rs-body tr", "rs => rs.length") == 2)
        check("no horizontal scroll", pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
        check("no console errors", not errors, errors)
        b.close()
finally:
    srv.terminate(); srv.wait()
print("FAILED:", fails)
