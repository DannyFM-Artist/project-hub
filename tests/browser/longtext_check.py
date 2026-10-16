"""Long-text layout check: no horizontal scroll, clamps, phase expand, selector inside card, no console errors."""
import json, os, shutil, subprocess, sys, time, urllib.request
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
from hubserver import BASE, SERVE

S = Path(__file__).resolve().parent
D = Path(tempfile.mkdtemp(prefix="hub-browser-"))  # never the real data folder
subprocess.check_call([sys.executable, str(S / "seed.py"), str(D)])
from project_hub.hub import Hub
hub = Hub(D)
M = S.parents[1] / "mockups"

PATH = "C:\\" + "\\".join(["very_long_folder_name_segment"] * 4)[:118]
URL = "https://example.com/" + "a1b2c3d4" * 14
HASH = "deadbeef" * 16
words = lambda n, w: (w + " ") * (n // (len(w) + 1))
hub.create_project("longtext", "longtext project", "x", phases=["P1", "Second", "Third", "Fourth"])
hub.add_item("longtext", "bug", "t", "d"); hub.log_decision("longtext", "d", "r")
hub.post_message("longtext", "report", "t", "b"); hub.post_message("longtext", "message", "t", "b")
hub.claim_resource("long-resource", "longtext", "p")
f = D / "projects" / "longtext.json"
p = json.loads(f.read_text(encoding="utf-8"))
p["description"] = words(600, "description")[:600]
p["next_step"] = words(300, "next")[:300]
p["repo_path"] = PATH
p["phases"][0]["name"] = "Phase with a rather long name " + "word " * 12
for ph in p["phases"]: ph["notes"] = words(300, "notes")[:300]
p["items"][0]["title"] = "Item " + PATH + " " + URL
p["items"][0]["details"] = HASH + " " + URL
p["decisions"][0]["decision"] = "Use " + URL
p["decisions"][0]["reason"] = "because " + PATH + HASH
f.write_text(json.dumps(p, indent=2), encoding="utf-8")
inbox = D / "inbox" / "messages.jsonl"
ms = [json.loads(l) for l in inbox.read_text(encoding="utf-8").split("\n") if l.strip()]
for m in ms:
    if m["to_project"] == "longtext":
        m["title"] = "Title " + URL; m["body"] = "body " + PATH + " " + HASH + "\n+ " + URL
inbox.write_text("".join(json.dumps(m) + "\n" for m in ms), encoding="utf-8")
lf = D / "resources" / "leases.json"
ls = json.loads(lf.read_text(encoding="utf-8"))
ls[0]["resource"] = "res-" + HASH; ls[0]["purpose"] = "purpose " + PATH + URL
lf.write_text(json.dumps(ls), encoding="utf-8")

srv = subprocess.Popen(SERVE, env=dict(os.environ, PROJECT_HUB_DATA=str(D)), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
fails = []
def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name)
try:
    for _ in range(50):
        try: urllib.request.urlopen(BASE + "/api/projects"); break
        except Exception: time.sleep(.2)
    with sync_playwright() as pw:
        b = pw.chromium.launch(channel="chrome")
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        errors = []
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errors.append(str(e)))
        lines = lambda sel, i=0: pg.evaluate("([s]) => { const e = document.querySelectorAll(s)[0]; return Math.round(e.getBoundingClientRect().height / parseFloat(getComputedStyle(e).lineHeight)); }", [sel])
        def noscroll(tag):
            check(tag + " no page h-scroll", pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
            check(tag + " panes fit", pg.evaluate("[...document.querySelectorAll('.pane')].filter(e => e.offsetParent).every(e => e.scrollWidth <= e.clientWidth + 1)"))
            check(tag + " tables fit", pg.evaluate("[...document.querySelectorAll('.tw')].every(e => e.scrollWidth <= e.clientWidth + 1)"))
        for w in (1280, 1440, 1920):
            pg.set_viewport_size({"width": w, "height": 900})
            pg.goto(BASE + "/#overview"); pg.wait_for_selector("tr.row"); time.sleep(.4)
            noscroll(f"{w} overview")
            row = pg.locator("tr.row", has_text="longtext project")
            n = pg.evaluate("() => { const s = [...document.querySelectorAll('td.name small')].find(e => e.textContent.length > 500); return Math.round(s.getBoundingClientRect().height / parseFloat(getComputedStyle(s).lineHeight)); }")
            check(f"{w} overview description <= 2 lines ({n})", n <= 2)
            check(f"{w} description has title tooltip", pg.evaluate("[...document.querySelectorAll('td.name small')].some(e => e.title.length > 500)"))
            pg.goto(BASE + "/#p/longtext"); pg.wait_for_selector(".cue"); time.sleep(.4)
            noscroll(f"{w} project")
            check(f"{w} full description in header", pg.evaluate("(document.querySelector('#phead .desc')||{textContent:''}).textContent.length >= 590"))
            ln = lambda: pg.evaluate("() => { const e = document.querySelector('.cue p'); return Math.round(e.getBoundingClientRect().height / parseFloat(getComputedStyle(e).lineHeight)); }")
            n0 = ln(); check(f"{w} notes clamp <= 4 lines ({n0})", n0 <= 4)
            card = pg.locator(".cue").first
            card.locator("button.main").click(); time.sleep(.2)
            n1 = ln(); check(f"{w} click expands ({n1})", n1 > 4)
            noscroll(f"{w} project expanded")
            sel = pg.evaluate("() => { const c = document.querySelector('.cue.sel'), s = c.querySelector('.selst'); const a = c.getBoundingClientRect(), r = s.getBoundingClientRect(); return r.left >= a.left && r.right <= a.right && r.bottom <= a.bottom; }")
            check(f"{w} status selector inside card", sel)
            time.sleep(5.5)  # survives the poll
            check(f"{w} expanded survives poll", ln() > 4)
            pg.locator(".cue").first.locator("button.main").focus(); pg.keyboard.press("Enter"); time.sleep(.2)
            check(f"{w} Enter collapses", ln() <= 4)
            pg.keyboard.press("Enter"); time.sleep(.2)
            check(f"{w} Enter expands", ln() > 4)
            if w == 1440:
                pg.mouse.move(0, 0); pg.screenshot(path=str(M / "impl-B-project-longtext.png"), full_page=True)
                pg.goto(BASE + "/#overview"); pg.wait_for_selector("tr.row"); time.sleep(.4)
                pg.mouse.move(0, 0); pg.screenshot(path=str(M / "impl-B-overview-longtext.png"), full_page=True)
        pg.set_viewport_size({"width": 800, "height": 900}); pg.goto(BASE + "/#p/longtext"); time.sleep(.5)
        check("800 project no page h-scroll", pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
        pg.goto(BASE + "/#overview"); time.sleep(.5)
        check("800 overview no page h-scroll", pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
        check("status bar text", pg.evaluate("document.querySelector('#sync').textContent.includes(location.host + ' · poll 5s · ')"))
        check(f"no console errors {errors}", not errors)
        b.close()
finally:
    srv.terminate(); srv.wait()
print("FAILED:", fails)
