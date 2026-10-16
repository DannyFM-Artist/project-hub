"""Phase gates against the real backend, by mouse: set / remove, Aprobar and Marcar como hecha with inline confirm and cancel,
status selector to done on a gated phase, selected card distinct, no window.alert/confirm."""
import os, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
from hubserver import BASE, SERVE

S = Path(__file__).resolve().parent
D = Path(tempfile.mkdtemp(prefix="hub-browser-"))  # never the real data folder
subprocess.check_call([sys.executable, str(S / "seed.py"), str(D)])
from project_hub.hub import Hub
hub = Hub(D)
hub.create_project("gatedemo", "gatedemo", "phase gate demo", phases=["Plan", "Build", "Field test", "Ship", "Release"])
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
        errors, dialogs = [], []
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))  # alert/confirm must never be used
        pg.goto(BASE + "/#p/gatedemo"); pg.wait_for_selector("#tl .tl")
        check("autonomy line shown", "Autonomous work allowed up to phase" in pg.inner_text("#phead"))
        entry = lambda name: pg.locator(f'.pe:has([data-fk="ph{ph[name]}"])')
        btn = lambda scope, label: scope.get_by_role("button", name=label, exact=True)

        def set_gate(name, kind, reason):
            if not pg.locator(f'.pe.sel:has([data-fk="ph{ph[name]}"])').count(): pg.click(f'[data-fk="ph{ph[name]}"]')  # selection survives a same-page goto
            pg.select_option(f"#gs{ph[name]}", kind)
            pg.fill(f"#gr{ph[name]}", reason)
            pg.click(f'[data-fk="gset{ph[name]}"]'); time.sleep(.8)
            if pg.locator(f'.pe.sel:has([data-fk="ph{ph[name]}"])').count(): pg.click(f'[data-fk="ph{ph[name]}"]')  # deselect

        # half-typed reason survives a poll
        pg.click(f'[data-fk="ph{ph["Build"]}"]'); pg.fill(f"#gr{ph['Build']}", "half typ")
        pg.evaluate("refresh(true)"); time.sleep(.5)
        check("draft reason survives refresh", pg.input_value(f"#gr{ph['Build']}") == "half typ")
        pg.click(f'[data-fk="ph{ph["Build"]}"]')

        # selected card is clearly distinct from the others
        pg.click(f'[data-fk="ph{ph["Field test"]}"]')
        style = lambda sel: pg.evaluate("s => { const e = document.querySelector(s), c = getComputedStyle(e); return [c.borderTopColor, c.borderTopWidth, c.backgroundColor, c.boxShadow] }", sel)
        s_sel, s_other = style(".pe.sel"), style(".pe.up:not(.sel)")
        check("selected card differs from the others (border, background, shadow)", all(a != b for a, b in zip(s_sel, s_other)), (s_sel, s_other))
        check("selected card says Selected and is aria-pressed", entry("Field test").locator(".selb").inner_text().lower() == "selected"
              and pg.get_attribute(f'[data-fk="ph{ph["Field test"]}"]', "aria-pressed") == "true" and pg.locator(".pe.sel").count() == 1)
        pg.click(f'[data-fk="ph{ph["Field test"]}"]')
        check("clicking the selected card again unselects it", pg.locator(".pe.sel").count() == 0)

        set_gate("Build", "review", "Check the colour pipeline before Build ships")
        g = gate("Build")
        check("review gate set via UI (by user)", g["gate"] == "review" and g["gate_set_by"] == "user" and not g["gate_approved"] and "colour pipeline" in g["gate_reason"], g)
        t = entry("Build").inner_text().lower()  # headings are upper-cased by CSS
        check("badge + reason on the phase entry", "review" in t and "waiting for you" in t and "colour pipeline" in t, t)
        check("Aprobar visible on the entry and in the alert without selecting anything", btn(entry("Build"), "Aprobar").is_visible() and btn(pg.locator("#att"), "Aprobar").is_visible()
              and pg.locator(".pe.sel").count() == 0)
        pg.goto(BASE + "/#overview"); pg.wait_for_selector(".proj")
        blk = pg.locator(".proj", has_text="gatedemo")
        check("overview block shows the waiting review gate and its summary", "review gate" in blk.inner_text().lower() and "colour pipeline" in blk.inner_text() and "Phase 2 of 5" in blk.inner_text(), blk.inner_text())
        check("overview summary sentence counts the gate", "gate" in pg.inner_text("#ov-lead") and "gatedemo" in pg.inner_text("#ov-lead"), pg.inner_text("#ov-lead"))
        check("most urgent project first", pg.locator(".proj h2 a").first.inner_text() in ("framegrade", "gatedemo"), pg.locator(".proj h2 a").all_inner_texts())
        pg.click("#ov-body .proj:has-text('gatedemo') h2 a"); pg.wait_for_selector("#phead h2")

        # Aprobar: cancel leaves everything unchanged, confirm approves
        btn(entry("Build"), "Aprobar").click()
        q = "¿Aprobar el gate de «Build» en gatedemo?"
        check("Aprobar opens an inline confirmation naming phase and project", entry("Build").locator(".cf").inner_text().startswith(q), entry("Build").locator(".cf").inner_text())
        btn(entry("Build"), "Cancelar").click(); time.sleep(.5)
        check("Cancelar closes the dialog and changes nothing", pg.locator(".cf").count() == 0 and gate("Build")["gate_approved"] is False and gate("Build")["status"] == "todo")
        btn(pg.locator("#att"), "Aprobar").click()
        check("the alert's Aprobar asks too (and only there)", pg.locator("#att .cf").count() == 1 and pg.locator(".pe .cf").count() == 0 and q in pg.inner_text("#att .cf"))
        btn(pg.locator("#att"), "Cancelar").click(); time.sleep(.3)
        check("cancel in the alert changes nothing", gate("Build")["gate_approved"] is False)
        btn(pg.locator("#att"), "Aprobar").click(); btn(pg.locator("#att"), "Sí, aprobar").click(); time.sleep(.8)
        check("confirm approves the gate", gate("Build")["gate_approved"] is True and pg.locator("#att").count() == 1 and not pg.is_visible("#att"), gate("Build"))
        check("approved entry says approved and has no Aprobar", "approved" in entry("Build").inner_text().lower() and btn(entry("Build"), "Aprobar").count() == 0)

        # manual_test: Marcar como hecha
        set_gate("Field test", "manual_test", "Run the show file on the real LED wall")
        check("manual_test gate set via UI", gate("Field test")["gate"] == "manual_test")
        check("Marcar como hecha visible without selecting", btn(entry("Field test"), "Marcar como hecha").is_visible() and btn(pg.locator("#att"), "Marcar como hecha").is_visible())
        btn(entry("Field test"), "Marcar como hecha").click()
        check("Marcar como hecha opens an inline confirmation naming phase and project", entry("Field test").locator(".cf").inner_text().startswith("¿Marcar «Field test» como hecha en gatedemo?"))
        btn(entry("Field test"), "Cancelar").click(); time.sleep(.5)
        check("cancel leaves the phase as it was", gate("Field test")["status"] == "todo" and pg.locator(".cf").count() == 0)
        btn(entry("Field test"), "Marcar como hecha").click(); btn(entry("Field test"), "Sí, marcar como hecha").click(); time.sleep(.8)
        check("confirm marks the manual_test phase done", gate("Field test")["status"] == "done", gate("Field test"))
        pg.goto(BASE + "/#overview"); time.sleep(.5)
        check("overview says nothing is waiting", "Nothing is waiting for you" in pg.inner_text("#ov-lead") or "gatedemo" not in pg.inner_text("#ov-lead"), pg.inner_text("#ov-lead"))

        # status selector to done on a gated phase asks first; an ungated phase does not
        hub.set_gate("gatedemo", ph["Ship"], "review", "Sign-off", by="user"); hub.approve_gate("gatedemo", ph["Ship"])
        pg.goto(BASE + "/#p/gatedemo"); pg.wait_for_selector("#tl .tl")
        pg.click(f'[data-fk="ph{ph["Ship"]}"]'); pg.click(f'[data-fk="psdone{ph["Ship"]}"]')
        check("selector to done on a gated phase opens the confirmation", entry("Ship").locator(".cf").count() == 1 and gate("Ship")["status"] == "todo")
        btn(entry("Ship"), "Cancelar").click(); time.sleep(.5)
        check("cancel keeps the phase as it was", gate("Ship")["status"] == "todo" and pg.locator(".cf").count() == 0)
        pg.click(f'[data-fk="psdone{ph["Ship"]}"]'); btn(entry("Ship"), "Sí, marcar como hecha").click(); time.sleep(.8)
        check("confirm sets the gated phase to done", gate("Ship")["status"] == "done", gate("Ship"))
        pg.click(f'[data-fk="ph{ph["Release"]}"]'); pg.click(f'[data-fk="psdone{ph["Release"]}"]'); time.sleep(.8)
        check("an ungated phase goes to done without asking", gate("Release")["status"] == "done" and pg.locator(".cf").count() == 0)

        # remove a gate
        hub.set_phase_status("gatedemo", ph["Release"], "todo", by="user")
        hub.set_gate("gatedemo", ph["Release"], "review", "temp", by="user")
        pg.goto(BASE + "/#p/gatedemo"); pg.wait_for_selector("#tl .tl")
        set_gate("Release", "none", "")
        check("gate removed via UI", gate("Release")["gate"] == "none", gate("Release"))

        hub.set_gate("gatedemo", ph["Release"], "manual_test", "x" * 160, by="user")
        for w in (1280, 800):
            pg.set_viewport_size({"width": w, "height": 800})
            pg.goto(BASE + "/#p/gatedemo"); pg.wait_for_selector("#tl .tl"); btn(pg.locator("#att"), "Marcar como hecha").click()
            check(f"no horizontal scroll ({w}, project, long reason, dialog open)", pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
            pg.goto(BASE + "/#overview"); pg.wait_for_selector(".proj")
            check(f"no horizontal scroll ({w}, overview, long reason)", pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
        check("no console errors", not errors, errors)
        check("no window.alert/confirm/prompt", not dialogs, dialogs)
        b.close()
finally:
    srv.terminate(); srv.wait()
print("FAILED:", fails)
