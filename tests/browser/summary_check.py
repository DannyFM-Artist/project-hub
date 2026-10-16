"""Resumen view: button, order, period, copy to clipboard, mark as seen, close without marking."""
import json, os, subprocess, sys, tempfile, time, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
from hubserver import BASE, SERVE

S = Path(__file__).resolve().parent
D = Path(tempfile.mkdtemp(prefix="hub-browser-"))  # never the real data folder
subprocess.check_call([sys.executable, str(S / "seed.py"), str(D)])
from project_hub.hub import Hub
hub = Hub(D)
hub.log_decision("cuedeck", "Use OSC over UDP", "Companion speaks it natively")
hub.post_message("cuedeck", "report", "Report: macros " + "long " * 80, "+ done\n" + "wrapme " * 60, "cuedeck")

def api(method, path, body=None):
    r = urllib.request.Request(BASE + path, method=method, data=json.dumps(body).encode() if body else None, headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r))

srv = subprocess.Popen(SERVE, env=dict(os.environ, PROJECT_HUB_DATA=str(D)), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
fails = []
def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name, extra); ok or fails.append(name)
try:
    for _ in range(50):
        try:
            urllib.request.urlopen(BASE + "/api/waiting"); break
        except Exception:
            time.sleep(.2)
    two_h = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    api("POST", "/api/summary/seen", {"at": two_h})
    seen0 = api("GET", "/api/summary")["last_seen"]
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        ctx = b.new_context(viewport={"width": 1440, "height": 900}, permissions=["clipboard-read", "clipboard-write"])
        pg = ctx.new_page()
        errors = []
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(BASE + "/"); pg.wait_for_selector("#ov-body tr")
        pg.click("#tab-su"); pg.wait_for_selector(".su-proj")
        check("button opens the view", pg.url.endswith("#resumen") and pg.is_visible("#summary"), pg.url)
        api_d = api("GET", "/api/summary")
        want = [x["name"] for x in api_d["projects"]]
        got = pg.eval_on_selector_all(".su-proj .lbl, .su-idle", "e => e.map(x => x.firstChild.textContent.trim().replace(/: sin actividad$/, ''))")
        check("projects listed, activity first, idle after", got == want and want[0] and api_d["projects"][0]["has_activity"], (got, want))
        check("report body wraps, no horizontal scroll", pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
        pg.click(".su-proj details summary"); time.sleep(.2)
        pg.evaluate("refresh(true)"); time.sleep(.5)
        check("expanded report survives refresh", pg.evaluate("document.querySelector('.su-proj details').open"))
        since1 = pg.inner_text("#su-since")
        pg.click('[data-p="24"]'); time.sleep(.7)
        since2 = pg.inner_text("#su-since")
        check("last 24 h changes the period", since1 != since2 and pg.evaluate("S.sumHours") == 24, (since1, since2))
        name = pg.eval_on_selector(".su-proj", "e => e.dataset.id")
        pg.click(f'[data-copy="{name}"]'); time.sleep(.4)
        clip = pg.evaluate("navigator.clipboard.readText()").replace(chr(13) + chr(10), chr(10))  # Windows clipboard turns LF into CRLF
        exp = pg.evaluate(f"S.sumD.projects.find(p => p.id === '{name}').chat_text")
        check("copy puts exact chat_text on the clipboard", clip == exp and len(exp) > 20, (clip, exp))
        check("copy confirmed in aria-live", "Copiado" in pg.inner_text("#toasts"))
        pg.click("#tab-ov"); pg.wait_for_selector("#ov-body tr")
        check("closing without marking leaves last_seen", api("GET", "/api/summary")["last_seen"] == seen0)
        pg.goto(BASE + "/#resumen"); pg.wait_for_function("S.sumD")
        until = pg.evaluate("S.sumD.until")
        pg.click("#su-seen"); time.sleep(.7)
        seen1 = api("GET", "/api/summary")["last_seen"]
        check("mark as seen persists the until of the view", seen1 != seen0 and seen1.startswith(until[:19]), (seen0, seen1, until))
        pg.reload(); pg.wait_for_selector(".su-proj, .su-idle")
        pg.wait_for_function("document.querySelector('#su-since').textContent")
        shown = pg.inner_text("#su-since")
        check("after reload, desde moves to the marked time", shown == "desde " + pg.evaluate(f"new Date('{seen1}').toLocaleString()"), shown)
        check("no console errors", not errors, errors)
        b.close()
finally:
    srv.terminate(); srv.wait()
print("FAILED:", fails)
