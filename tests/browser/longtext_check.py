"""Long-text layout check: no horizontal scroll, clamps, phase selection shows full notes, selector inside the row, no console errors."""
import json, os, shutil, subprocess, sys, time, urllib.request
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
from hubserver import BASE, SERVE, serve

S = Path(__file__).resolve().parent
D = Path(tempfile.mkdtemp(prefix="hub-browser-"))  # never the real data folder
subprocess.check_call([sys.executable, str(S / "seed.py"), str(D)])
from project_hub.hub import Hub
hub = Hub(D)

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

srv = serve(D)
fails = []
def check(name, cond):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond: fails.append(name)
try:
    with sync_playwright() as pw:
        b = pw.chromium.launch(channel="chrome")
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        errors = []
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errors.append(str(e)))
        def noscroll(tag):
            check(tag + " no page h-scroll", pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
            check(tag + " panels fit", pg.evaluate("[...document.querySelectorAll('.panel')].filter(e => e.offsetParent).every(e => e.scrollWidth <= e.clientWidth + 1)"))
        nlines = lambda sel: pg.evaluate("([s]) => { const e = document.querySelector(s); return Math.round(e.getBoundingClientRect().height / parseFloat(getComputedStyle(e).lineHeight)); }", [sel])
        ph = {x["name"].split()[0]: x["id"] for x in hub.get_project("longtext")["phases"]}
        for w in (1280, 1440, 1920):
            pg.set_viewport_size({"width": w, "height": 900})
            pg.goto(BASE + "/#overview"); pg.wait_for_selector("#ov-body .row"); time.sleep(.4)
            noscroll(f"{w} overview")
            n = pg.evaluate("() => { const s = [...document.querySelectorAll('.ptab .sub')].find(e => e.textContent.length > 500); return Math.round(s.getBoundingClientRect().height / parseFloat(getComputedStyle(s).lineHeight)); }")
            check(f"{w} overview description is one line ({n})", n <= 1)
            check(f"{w} description has title tooltip", pg.evaluate("[...document.querySelectorAll('.ptab .sub')].some(e => e.title.length > 500)"))
            pg.goto(BASE + "/#p/longtext"); pg.wait_for_selector("#phases .row"); time.sleep(.4)
            noscroll(f"{w} project")
            check(f"{w} full description in header", pg.evaluate("document.querySelector('#pr-desc').textContent.length >= 590"))
            other = f'#phases .row[data-id="{ph["Second"]}"]'
            n0 = nlines(other + " .nt"); check(f"{w} unselected notes clamp to 1 line ({n0})", n0 <= 1)
            pg.click(f'[data-fk="ph{ph["Second"]}"]'); pg.wait_for_selector(other + ".sel")
            n1 = nlines(other + " .detail .notes"); check(f"{w} selecting shows the full notes ({n1})", n1 > 1)
            noscroll(f"{w} project selected")
            sel = pg.evaluate("([s]) => { const c = document.querySelector(s), x = c.querySelector('select'); const a = c.getBoundingClientRect(), r = x.getBoundingClientRect(); return r.left >= a.left && r.right <= a.right && r.bottom <= a.bottom; }", [other])
            check(f"{w} status selector inside the row", sel)
            time.sleep(5.5)  # survives the poll
            check(f"{w} selection survives poll", pg.locator(other + ".sel .detail").count() == 1)
            third = f'[data-fk="ph{ph["Third"]}"]'
            pg.locator(third).focus(); pg.keyboard.press("Enter"); time.sleep(.2)
            check(f"{w} Enter on a phase selects it", pg.locator(f'#phases .row.sel[data-id="{ph["Third"]}"]').count() == 1 and pg.locator(other + ".sel").count() == 0)
            if w == 1440:
                pg.mouse.move(0, 0); pg.screenshot(path=str(D / "project-longtext.png"), full_page=True)
                pg.goto(BASE + "/#overview"); pg.wait_for_selector("#ov-body .row"); time.sleep(.4)
                pg.mouse.move(0, 0); pg.screenshot(path=str(D / "overview-longtext.png"), full_page=True)
                print("screenshots in", D)
        pg.set_viewport_size({"width": 800, "height": 900}); pg.goto(BASE + "/#p/longtext"); time.sleep(.5)
        check("800 project no page h-scroll", pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
        pg.goto(BASE + "/#overview"); time.sleep(.5)
        check("800 overview no page h-scroll", pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
        check("status bar title", pg.evaluate("document.querySelector('#sync').title.includes(location.host + ' · poll 5s')"))
        check(f"no console errors {errors}", not errors)
        b.close()
finally:
    srv.terminate(); srv.wait()
print("FAILED:", fails)
