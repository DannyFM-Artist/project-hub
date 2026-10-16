"""Gates are read-only in the dashboard: waiting / resolved lines, no gate controls, waiting panel links to the chat project."""
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
hub.create_project("gatedemo", "gatedemo", "phase gate demo", phases=["Plan", "Build", "Field test", "Ship"])
ph = {p["name"]: p["id"] for p in hub.get_project("gatedemo")["phases"]}
hub.set_gate("gatedemo", ph["Build"], "Check the colour pipeline before Build ships", by="agent")
hub.set_gate("gatedemo", ph["Field test"], "Run the show file", by="agent")
hub.resolve_gate("gatedemo", ph["Field test"], "sigue", "sí, sigue con eso " + "y " * 50)
hub.set_gate("gatedemo", ph["Ship"], "Final check", by="agent")
hub.resolve_gate("gatedemo", ph["Ship"], "hecho", "ya está, hecho")

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
        pg.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        card = lambda n: pg.locator(f'#cues .cue:has([data-fk="ph{ph[n]}"])')

        pg.goto(BASE + "/#overview"); pg.wait_for_selector("#wt-pane:not([hidden])")
        t = pg.inner_text("#wt-pane")
        check("waiting panel line", "gatedemo" in t and "Build" in t and "colour pipeline" in t and "Resuélvelo en el chat de gatedemo" in t, t)
        check("waiting panel lists only the waiting gate", "Field test" not in t and "Ship" not in t, t)
        check("waiting panel link goes to the project", pg.get_attribute("#wt-body a", "href") == "#p/gatedemo")
        check("waiting panel has no buttons", pg.locator("#wt-pane button").count() == 0)

        pg.goto(BASE + "/#p/gatedemo"); pg.wait_for_selector("#cues .cue")
        check("waiting line on card", "Espera a Danny: Check the colour pipeline" in card("Build").inner_text(), card("Build").inner_text())
        ft = card("Field test")
        check("resolved line with words and action", "Resuelto vía chat: «sí, sigue con eso" in ft.inner_text() and "…»" in ft.inner_text() and "(sigue)" in ft.inner_text(), ft.inner_text())
        tip = ft.locator(".gt").get_attribute("title")
        check("tooltip has full words, action and time", "y y y y y y y y y y y y y y y y y y y y y y y y y y" in tip and "sigue" in tip and "20" in tip, tip)
        check("hecho resolution shown", "ya está, hecho" in card("Ship").inner_text() and "(hecho)" in card("Ship").inner_text(), card("Ship").inner_text())

        card("Plan").locator("button.main").click()
        check("status control still on a non-gated phase", card("Plan").locator(".selst").count() == 1)
        card("Build").locator("button.main").click()
        check("no status control on the waiting phase", card("Build").locator(".selst").count() == 0 and pg.locator("#cues .selst").count() == 0)
        check("no gate controls anywhere", pg.locator("#cues .gf, #cues select, #cues input, #cues form").count() == 0
              and not any(w in pg.inner_text("main") for w in ("Guardar gate", "Set gate", "Quitar aprobación", "Approve", "Mark done")))
        pg.keyboard.press(" "); time.sleep(.5)
        check("space does not change the waiting phase", hub.get_project("gatedemo")["phases"][1]["status"] == "todo")

        pg.goto(BASE + "/#resumen"); pg.wait_for_selector("#su-body .su-proj")
        sec = pg.inner_text("#su-body")
        check("Resumen waiting line", "Build" in sec and "Resuélvelo en el chat de gatedemo" in sec, sec)
        check("Resumen has no gate buttons", pg.locator("#su-body .su-l button").count() == 0)
        check("no alert or confirm", not dialogs, dialogs)
        check("no console errors", not errors, errors)
        b.close()
finally:
    srv.terminate(); srv.wait()
print("FAILED:", fails)
