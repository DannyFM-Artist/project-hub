"""A stopped (paused/parked/done) project shows a grey "Parado" state linking its "Parado: estado para retomar" report."""
import subprocess, sys, tempfile, time
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
from hubserver import BASE, serve, until

S = Path(__file__).resolve().parent
D = Path(tempfile.mkdtemp(prefix="hub-browser-"))  # never the real data folder
subprocess.check_call([sys.executable, str(S / "seed.py"), str(D)])
from project_hub.hub import Hub
hub = Hub(D)
hub.create_project("stopme", "Stop me", "stop demo", phases=["One"])
rid = hub.post_message("stopme", "report", "Parado: estado para retomar",
                       "Hecho: x\nSiguientes pasos: retomar la fase One", "stopme")["id"]
hub.update_project("stopme", status="paused")

srv = serve(D)
fails = []
def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name, extra); ok or fails.append(name)
try:
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        errors = []
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(BASE + "/#overview")
        row = '#ov-body .card[data-pid="stopme"]'
        until(lambda: pg.locator(row).count())
        badge = pg.locator(row + " .pstate[data-kind=stopped]")
        check("overview row shows grey Parado", badge.count() == 1 and "Parado" in badge.inner_text(), badge.count())
        link = pg.locator(row + " a.stop-l")
        check("overview row links the Parado report", link.count() == 1 and link.get_attribute("href").endswith(f"/m/{rid}"),
              link.get_attribute("href") if link.count() else None)
        link.click()
        until(lambda: pg.locator("text=retomar la fase One").count())
        check("link opens the project with the report selected", "#p/stopme/m/" in pg.url
              and pg.locator("text=retomar la fase One").first.is_visible(), pg.url)
        check("the folded Bandeja opens itself for the linked report", pg.is_visible("#in-body")
              and pg.get_attribute('[data-fk="fold-inbox"]', "aria-expanded") == "true" and pg.locator(f'#pr-rep .rep[data-mid="{rid}"]').count() == 1)
        hub.mark_message(rid, "read")  # a read report lives in the message list, still inside the folded Bandeja
        pg.goto(BASE + "/#overview"); until(lambda: pg.locator(row).count())
        pg.goto(BASE + f"/#p/stopme/m/{rid}")
        until(lambda: pg.locator(f'#msgs .row.sel[data-id="{rid}"]').count())
        check("a read report: Bandeja opens and the message is selected with its body", pg.is_visible("#in-body")
              and pg.locator(f'#msgs .row.sel[data-id="{rid}"] .body').is_visible(), pg.url)
        head = pg.locator("#phead .pstate[data-kind=stopped]")
        check("project header shows Parado with the link", head.count() == 1 and head.locator("a.stop-l").count() == 1)
        pg.goto(BASE + "/#resumen")
        box = '.su-proj[data-id="stopme"]'
        until(lambda: pg.locator(box).count())
        check("Resumen box shows Parado with the link", pg.locator(box + " .pstate[data-kind=stopped] a.stop-l").count() == 1)
        check("no console errors", not errors, errors)
        b.close()
finally:
    srv.terminate(); srv.wait()
print("FAILED:", fails)
