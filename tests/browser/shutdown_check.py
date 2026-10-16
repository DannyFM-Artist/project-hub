"""Tray "Reiniciar servidor" shows "Reiniciando…" and reconnects; tray "Salir" shows "Dashboard detenido" and closes
the window where the browser allows it. Drives the real tray Server in this process, as the tray app does."""
import os, subprocess, sys, tempfile, threading
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
from hubserver import BASE, PORT, until

S = Path(__file__).resolve().parent
D = Path(tempfile.mkdtemp(prefix="hub-browser-"))  # never the real data folder
subprocess.check_call([sys.executable, str(S / "seed.py"), str(D)])
os.environ["PROJECT_HUB_DATA"] = str(D)
from project_hub import tray, web


class Icon:
    visible, stopped = True, False

    def stop(self):
        self.stopped = True


fails = []
def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name, extra); ok or fails.append(name)

server = tray.Server(PORT)
server.start()
until(lambda: tray.is_running(PORT), 30)
try:
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        pg = ctx.new_page()
        errors = []
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(BASE + "/#overview")
        pg.goto(BASE + "/#p/framegrade")  # two history entries: a normal tab that scripts may not close
        until(lambda: pg.locator("#phead").count())
        until(lambda: tray.time.monotonic() - web.STATUS["polled"] < 1, 8)  # a page is polling, so the tray waits for it

        t = threading.Thread(target=tray.restart_server, args=(server,)); t.start()
        until(lambda: pg.is_visible("#offline"), 8)
        check("restart: page shows Reiniciando", "Reiniciando" in pg.inner_text("#offline"), pg.inner_text("#offline"))
        t.join()
        until(lambda: not pg.is_visible("#offline"), 12)
        check("restart: page reconnects and the notice goes", not pg.is_visible("#offline") and pg.locator("#stopped").count() == 0)

        # an app-like window that the page may close itself (opened by script)
        with ctx.expect_page() as popup:
            pg.evaluate(f"window.open('{BASE}/#overview', 'app', 'popup')")
        app = popup.value
        app.wait_for_load_state()
        until(lambda: app.locator("#ov-body .card").count())

        icon = Icon()
        t = threading.Thread(target=tray.quit_app, args=(server, icon), kwargs={"confirm": lambda: True}); t.start()
        until(lambda: pg.locator("#stopped").count(), 12)
        check("quit: tab shows full-page Dashboard detenido", pg.is_visible("#stopped")
              and "Dashboard detenido" in pg.inner_text("#stopped") and "menú Inicio" in pg.inner_text("#stopped"))
        box = pg.locator("#stopped").bounding_box()
        check("quit: the notice covers the page", box and box["width"] >= 1440 and box["height"] >= 900, box)
        check("quit: a normal tab stays open", not pg.is_closed())
        until(lambda: app.is_closed() or pg.wait_for_timeout(100), 6)  # Playwright only sees the close while it runs a call
        check("quit: a script-opened window closes itself", app.is_closed())
        t.join()
        check("quit: server stopped and tray icon gone", not tray.is_running(PORT) and icon.stopped and not icon.visible)
        pg.wait_for_timeout(6000)  # one more poll period: polling has stopped, so no offline bar on top of the notice
        check("quit: polling stopped, no offline bar", not pg.is_visible("#offline") and pg.locator("#stopped").count() == 1)
        check("no console errors", not errors, errors)
        b.close()
finally:
    server.stop()
print("FAILED:", fails)
