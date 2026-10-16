"""Screenshot redesign mockups: python shots.py A [B C]. 1440x900 viewport (no scrolling) plus a stress full-page shot."""
import sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8")

M = Path(__file__).resolve().parents[1]
fails = []
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    for letter in sys.argv[1:] or ["A", "B", "C"]:
        url = (M / f"redesign-{letter}.html").as_uri()
        for name, q, h, full in [("overview", "#overview", "", False), ("project", "#p/framemorph", "", False),
                                 ("stagetrack", "#p/stagetrack", "", False), ("stress", "#p/stagetrack", "?stress=1", True)]:
            pg = b.new_page(viewport={"width": 1440, "height": 900})
            errors = []
            pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.goto(url + h + q); time.sleep(.6)
            wide = pg.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
            if wide: fails.append(f"{letter} {name}: horizontal page scroll")
            if errors: fails.append(f"{letter} {name}: console errors {errors}")
            pg.mouse.move(0, 0)
            pg.screenshot(path=str(M / f"redesign-{letter}-{name}.png"), full_page=full)
            pg.close()
        print(f"{letter}: shots written")
    b.close()
print("FAILED:" if fails else "ALL OK", *fails, sep="\n  ")
sys.exit(1 if fails else 0)
