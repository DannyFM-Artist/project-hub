"""Phase gates against the real backend: set / approve / mark done / remove through the dashboard UI, waiting pane, screenshots."""
import os, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
from hubserver import BASE, SERVE

S = Path(__file__).resolve().parent
D = Path(tempfile.mkdtemp(prefix="hub-browser-"))  # never the real data folder
SHOTS = S.parents[1] / "mockups"
subprocess.check_call([sys.executable, str(S / "seed.py"), str(D)])
from project_hub.hub import Hub
hub = Hub(D)
hub.create_project("gatedemo", "gatedemo", "phase gate demo", phases=["Plan", "Build", "Field test", "Ship"])
ph = {p["name"]: p["id"] for p in hub.get_project("gatedemo")["phases"]}
hub.set_phase_status("gatedemo", ph["Plan"], "done")
gate = lambda name: hub.get_project("gatedemo")["phases"][list(ph).index(name)]

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
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        errors = []
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(BASE + "/#p/gatedemo"); pg.wait_for_selector("#cues .cue")
        check("autonomy line shown", "Autonomous work allowed up to phase" in pg.inner_text("#phead"), pg.inner_text(".aut") if pg.query_selector(".aut") else "missing")

        def set_gate(name, kind, reason):
            pg.click(f'[data-fk="ph{ph[name]}"]')
            pg.select_option(f"#gs{ph[name]}", kind)
            pg.fill(f"#gr{ph[name]}", reason)
            pg.click(f'[data-fk="gset{ph[name]}"]'); time.sleep(.8)
        def wait_text():
            return pg.inner_text("#wt-pane") if pg.is_visible("#wt-pane") else ""

        # half-typed reason survives a poll
        pg.click(f'[data-fk="ph{ph["Build"]}"]'); pg.fill(f"#gr{ph['Build']}", "half typ")
        pg.evaluate("refresh(true)"); time.sleep(.5)
        check("draft reason survives refresh", pg.input_value(f"#gr{ph['Build']}") == "half typ")

        set_gate("Build", "review", "Check the colour pipeline before Build ships")
        g = gate("Build")
        check("review gate set via UI (by user)", g["gate"] == "review" and g["gate_set_by"] == "user" and not g["gate_approved"] and "colour pipeline" in g["gate_reason"], g)
        card = pg.inner_text(f'#cues .cue:has([data-fk="ph{ph["Build"]}"])')
        check("badge + reason on card", "REVIEW" in card and "not approved" in card and "colour pipeline" in card, card)
        pg.goto(BASE + "/#overview"); pg.wait_for_selector("#wt-pane:not([hidden])")
        t = wait_text()
        check("waiting pane lists review gate", "gatedemo" in t and "Build" in t and "REVIEW" in t and "colour pipeline" in t, t)
        check("waiting pane is above projects pane", pg.evaluate("document.querySelector('#wt-pane').compareDocumentPosition(document.querySelector('#ov-table')) & 4") != 0)
        check("overview headings are h2", pg.eval_on_selector_all("#overview .lbl", "e => e.every(x => x.tagName === 'H2')"))
        pg.mouse.move(0, 0); pg.screenshot(path=str(SHOTS / "impl-B-overview-gates.png"), full_page=True)
        pg.click("#wt-body tr:first-child td:nth-child(2)")
        pg.wait_for_selector("#phead h2")
        check("clicking a waiting row opens the project", pg.url.endswith("#p/gatedemo"), pg.url)

        pg.wait_for_selector("#cues .cue")
        set_gate("Field test", "manual_test", "Run the show file on the real LED wall")
        check("manual_test gate set via UI", gate("Field test")["gate"] == "manual_test")
        pg.click(f'[data-fk="ph{ph["Build"]}"]'); pg.click(f'[data-fk="ph{ph["Field test"]}"]'); time.sleep(.3)
        pg.mouse.move(0, 0); pg.screenshot(path=str(SHOTS / "impl-B-project-gates.png"), full_page=True)

        pg.click(f'[data-fk="ph{ph["Build"]}"]')  # select Build (card toggles; ensure it is selected)
        if not pg.query_selector(f'[data-fk="gap{ph["Build"]}"]'): pg.click(f'[data-fk="ph{ph["Build"]}"]')
        pg.click(f'[data-fk="gap{ph["Build"]}"]'); time.sleep(.8)
        check("approve via UI", gate("Build")["gate_approved"] is True, gate("Build"))
        hub.set_phase_status("gatedemo", ph["Build"], "done", by="user")
        pg.goto(BASE + "/#overview"); pg.wait_for_selector("#wt-pane:not([hidden])")
        t = wait_text()
        check("approved review leaves waiting; manual test now waits", "REVIEW" not in t and "MANUAL TEST" in t, t)

        pg.goto(BASE + "/#p/gatedemo"); pg.wait_for_selector("#cues .cue")
        pg.click(f'[data-fk="ph{ph["Field test"]}"]')
        if not pg.query_selector(f'[data-fk="gdone{ph["Field test"]}"]'): pg.click(f'[data-fk="ph{ph["Field test"]}"]')
        pg.click(f'[data-fk="gdone{ph["Field test"]}"]'); time.sleep(.8)
        check("manual_test marked done via UI", gate("Field test")["status"] == "done", gate("Field test"))
        pg.goto(BASE + "/#overview"); time.sleep(.5)
        check("waiting pane hidden when empty", not pg.is_visible("#wt-pane"))

        hub.set_gate("gatedemo", ph["Ship"], "review", "temp", by="user")
        pg.goto(BASE + "/#p/gatedemo"); pg.wait_for_selector("#cues .cue")
        set_gate("Ship", "none", "")
        check("gate removed via UI", gate("Ship")["gate"] == "none", gate("Ship"))
        pg.set_viewport_size({"width": 1280, "height": 800})
        check("no horizontal scroll (project)", pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
        hub.set_gate("gatedemo", ph["Ship"], "manual_test", "x" * 160, by="user")
        pg.goto(BASE + "/#overview"); pg.wait_for_selector("#wt-pane:not([hidden])")
        check("no horizontal scroll (overview, long reason)", pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
        check("no console errors", not errors, errors)
        b.close()
finally:
    srv.terminate(); srv.wait()
print("FAILED:", fails)
