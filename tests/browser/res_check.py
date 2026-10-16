"""Resources pane against the real backend: leases claimed via Hub, rendering, force release with an inline confirmation."""
import os, shutil, subprocess, sys, time, urllib.request
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
from hubserver import BASE, SERVE, until, serve

S = Path(__file__).resolve().parent
D = Path(tempfile.mkdtemp(prefix="hub-browser-"))  # never the real data folder
subprocess.check_call([sys.executable, str(S / "seed.py"), str(D)])
from project_hub.hub import Hub
hub = Hub(D)
assert hub.claim_resource("GPU ", "framegrade", "NVDEC batch encode", 45)["status"] == "granted"
assert hub.claim_resource("device:orbbec-femto-mega", "cuedeck", "depth calibration", 10)["status"] == "granted"
assert hub.claim_resource("repo:dannyfm-ui", "project-hub", "theme tokens", 125)["status"] == "granted"
assert hub.claim_resource("gpu", "cuedeck", "x")["status"] == "busy"

srv = serve(D)
fails = []
def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name, extra); ok or fails.append(name)
try:
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        errors, dialogs = [], []
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        pg.goto(BASE + "/#overview"); pg.wait_for_selector("#rs-body .row"); time.sleep(.5)
        rows = pg.eval_on_selector_all("#rs-body .row", "rs => rs.map(r => [...r.children].slice(0, 4).map(c => c.textContent.trim()))")
        for r in rows: print("  row", r)
        check("3 leases listed, sorted, project names", [r[0] for r in rows] == ["device:orbbec-femto-mega", "gpu", "repo:dannyfm-ui"]
              and [r[1] for r in rows] == ["cuedeck", "framegrade", "project-hub"], rows)
        check("time left format", rows[0][3] in ("10m", "9m") and rows[1][3] in ("45m", "44m") and rows[2][3] in ("2h 05m", "2h 04m"), [r[3] for r in rows])
        ck = "rs|device:orbbec-femto-mega"
        pg.click(f'[data-fk="b|{ck}"]'); pg.wait_for_selector(f'.confirm[data-ck="{ck}"]')
        q = pg.inner_text(f'.confirm[data-ck="{ck}"]')
        check("Liberar asks inline, naming resource and project", "device:orbbec-femto-mega" in q and "cuedeck" in q, q)
        pg.click(f'[data-fk="n|{ck}"]'); time.sleep(.4)
        check("Cancelar keeps the lease", len(hub.list_resources()) == 3 and pg.locator(".confirm").count() == 0)
        pg.click(f'[data-fk="b|{ck}"]'); pg.click(f'[data-fk="y|{ck}"]')
        left = until(lambda: [l["resource"] for l in hub.list_resources()] == ["gpu", "repo:dannyfm-ui"])
        check("force release via dashboard", left, [l["resource"] for l in hub.list_resources()])
        check("pane updated", until(lambda: pg.eval_on_selector_all("#rs-body .row", "rs => rs.length") == 2))
        check("no browser dialog", not dialogs, dialogs)
        check("no horizontal scroll", pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
        check("no console errors", not errors, errors)
        b.close()
finally:
    srv.terminate(); srv.wait()
print("FAILED:", fails)
