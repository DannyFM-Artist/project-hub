"""Gates are read-only in the dashboard (Danny resolves them in each project's chat): display, "Para ti", bell, reports, selection."""
import json, os, re, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
from hubserver import BASE, SERVE, until, serve

S = Path(__file__).resolve().parent
D = Path(tempfile.mkdtemp(prefix="hub-browser-"))  # never the real data folder
subprocess.check_call([sys.executable, str(S / "seed.py"), str(D)])
from project_hub.hub import Hub
hub = Hub(D)
hub.create_project("gatedemo", "gatedemo", "phase gate demo", phases=["Plan", "Build", "Field test", "Ship"])
ph = {p["name"]: p["id"] for p in hub.get_project("gatedemo")["phases"]}
hub.set_phase_status("gatedemo", ph["Plan"], "done")
hub.set_gate("gatedemo", ph["Build"], "Check the colour pipeline before Build ships")
hub.set_gate("gatedemo", ph["Field test"], "Run the show file on the real LED wall")
hub.set_gate("gatedemo", ph["Ship"], "temp")
hub.resolve_gate("gatedemo", ph["Ship"], "sigue", "sí, sigue con el envío " + "y " * 50)
to_user = hub.post_message("user", "message", "Which licence?", "MIT or proprietary", "gatedemo")
hub.post_message("gatedemo", "report", "Session report A", "+ ok", "gatedemo")
hub.post_message("gatedemo", "report", "Session report B", "+ ok", "gatedemo")
hub.add_item("gatedemo", "bug", "A bug", "d"); hub.add_item("gatedemo", "idea", "An idea", "d")
hub.post_message("gatedemo", "task", "Plain task", "body"); hub.post_message("gatedemo", "message", "Plain note", "body")
hub.log_decision("gatedemo", "Ship by USB", "no network at the venue")
hub.update_project("gatedemo", repo_path=r"C:\dev\gatedemo")
gate = lambda name: hub.get_project("gatedemo")["phases"][list(ph).index(name)]
INDEX = (S.parents[1] / "project_hub" / "static" / "index.html").read_text(encoding="utf-8")

srv = serve(D)
fails = []
def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name, extra); ok or fails.append(name)
def expected_bell():
    waiting = sum(1 for p in hub.list_projects() for x in p["phases"] if x.get("gate_state") == "waiting" and x["status"] != "done")
    with hub._read_lock():  # the server may be rewriting messages.jsonl
        return waiting + sum(1 for m in hub._messages() if m["to_project"] == "user" and m["status"] != "done")
try:
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        errors, dialogs = [], []
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
        row = lambda name: f'#phases .row[data-id="{ph[name]}"]'
        pg.goto(BASE + "/#p/gatedemo"); pg.wait_for_selector("#phases .row")
        check("no 'Autonomous work allowed' text in the page", "Autonomous work allowed" not in pg.inner_text("body") and "Autonomous" not in INDEX)
        # header: two lines, the rest in a folded "Detalles"
        check("Detalles folded by default in the project header", pg.get_attribute('[data-fk="fold-det"]', "aria-expanded") == "false"
              and pg.locator("#phead .pdet").count() == 0 and "C:\\dev\\gatedemo" not in pg.inner_text("#phead") and "phase gate demo" not in pg.inner_text("#phead"))
        pg.click('[data-fk="fold-det"]'); pg.wait_for_selector("#phead .pdet")
        check("Detalles opens with path and description", "C:\\dev\\gatedemo" in pg.inner_text("#phead .pdet") and "phase gate demo" in pg.inner_text("#phead .pdet"), pg.inner_text("#phead .pdet"))
        pg.click('[data-fk="fold-det"]')
        check("decisions and inbox folded, with their counts",
              pg.is_hidden("#decs") and pg.is_hidden("#in-body") and pg.inner_text("#dec-h").lower() == "decisiones · 1" and pg.inner_text("#in-h").lower() == f"bandeja · {len(hub.read_inbox('gatedemo', unread_only=False))}",
              (pg.inner_text("#dec-h"), pg.inner_text("#in-h")))
        pg.click('[data-fk="fold-dec"]'); pg.wait_for_selector("#decs .row")
        check("Decisiones opens from its title", "Ship by USB" in pg.inner_text("#decs"))
        pg.click('[data-fk="fold-inbox"]'); pg.wait_for_selector("#in-body .inbox .row, #in-body #msgs .row")
        check("Bandeja opens from its title: reports line and messages", "2 reports sin leer" in pg.inner_text("#pr-rep") and "Plain task" in pg.inner_text("#msgs"))
        pg.evaluate("refresh(true)"); time.sleep(.3)
        check("folds survive a refresh", pg.is_visible("#decs") and pg.is_visible("#in-body"))

        # read-only gate display
        t = pg.inner_text(row("Build") + " .gc")
        check("waiting gate reads 'espera a Danny' on its row", t.lower() == "espera a danny", t)
        pg.click(f'[data-fk="ph{ph["Build"]}"]'); pg.wait_for_selector(row("Build") + ".sel")
        d = pg.inner_text(row("Build") + " .detail")
        check("selected waiting phase does not repeat the reason (it is in Para ti)",
              "Check the colour pipeline" not in pg.inner_text("#phases") and "Check the colour pipeline before Build ships" in pg.inner_text("#pr-act"), d)
        check("no status control on a phase whose gate waits", pg.locator(row("Build") + " select").count() == 0 and "no se cambia aquí" in d)
        pg.evaluate("document.activeElement.blur()"); pg.keyboard.press(" "); time.sleep(.6)
        check("space key does not change a waiting phase", gate("Build")["status"] == "todo")
        t = pg.inner_text(row("Ship") + " .gc")
        check("resolved gate reads 'Resuelto vía chat: «…»', shortened", t.startswith("Resuelto vía chat: «sí, sigue con el envío") and t.endswith("…»"), t)
        check("full words in the tooltip", "y y y y" in (pg.get_attribute(row("Ship") + " .gc .chat", "title") or ""))
        check("no gate buttons, editors or confirmations on the page",
              pg.locator("text=Aprobar").count() == 0 and pg.locator("text=Marcar como hecha").count() == 0 and pg.locator("text=Guardar gate").count() == 0
              and pg.locator(".confirm").count() == 0 and "/gate" not in INDEX)
        # an old dashboard approval, migrated: resolved "sigue" without Danny's words
        f = D / "projects" / "gatedemo.json"; j = json.loads(f.read_text(encoding="utf-8"))
        j["phases"][0].update(gate_state="continue", gate_reason="old", gate_set_by="agent", gate_resolved_action="sigue", gate_resolved_words=None, gate_resolved_at=None)
        f.write_text(json.dumps(j, indent=2), encoding="utf-8")
        pg.evaluate("refresh(true)"); pg.click('[data-fk="done|gatedemo"]'); pg.wait_for_selector(row("Plan"))
        check("a gate resolved without words reads 'Resuelto (sigue)'", pg.inner_text(row("Plan") + " .gc") == "Resuelto (sigue)", pg.inner_text(row("Plan") + " .gc"))

        # "Para ti" on the project: read-only lines pointing to the chat
        t = pg.inner_text("#pr-act")
        check("project 'Para ti' lists both waiting gates and the message, no buttons",
              "Build" in t and "Field test" in t and "Which licence?" in t and pg.locator("#pr-act .row.act .btn").count() == 0, t)
        check("each line says 'Resuélvelo en el chat de gatedemo' and links to the project",
              pg.locator('#pr-act a.where:has-text("Resuélvelo en el chat de gatedemo")').count() == 3 and pg.get_attribute("#pr-act a.where", "href") == "#p/gatedemo")

        # selected row: tint + accent edge, and the edge never overlaps the row's content
        def sel_style(list_sel, row="row"):
            return pg.evaluate("""([s, row]) => { const sel = document.querySelector(s + ' .' + row + '.sel'), other = document.querySelector(s + ' .' + row + ':not(.sel)');
                const cs = getComputedStyle(sel), co = getComputedStyle(other), r = sel.getBoundingClientRect();
                const first = sel.firstElementChild, inner = first.querySelector('.dot') || first, c = inner.getBoundingClientRect();
                const edge = r.left + parseFloat(cs.borderLeftWidth);
                return { bg: cs.backgroundColor, other: co.backgroundColor, edge: cs.borderLeftColor, w: cs.borderLeftWidth, gap: c.left - edge }; }""", [list_sel, row])
        s1 = sel_style("#phases")
        check("selected phase row is distinct (tint + accent left border)", s1["bg"] != s1["other"] and s1["edge"] == "rgb(136, 254, 0)" and s1["w"] == "2px", s1)
        check("selection marker does not overlap the phase row content", s1["gap"] >= 4, s1)
        pg.locator(".items .row .t").first.click(); pg.wait_for_selector(".items .row.sel")
        s2 = sel_style(".items")
        check("selected item row distinct, marker clear of content", s2["bg"] != s2["other"] and s2["edge"] == "rgb(136, 254, 0)" and s2["gap"] >= 4, s2)
        pg.locator(".inbox .row .t").first.click(); pg.wait_for_selector(".inbox .row.sel")
        s3 = sel_style(".inbox")
        check("selected inbox row distinct, marker clear of content", s3["bg"] != s3["other"] and s3["gap"] >= 4, s3)

        # bell: waiting gates + messages to user, not reports
        pg.goto(BASE + "/#p/framegrade"); pg.wait_for_function("document.querySelector('#phead h1') && document.querySelector('#phead h1').textContent === 'framegrade'")
        check("project 'Para ti' hidden when nothing waits", pg.is_hidden("#pr-act"))
        pg.goto(BASE + "/#overview")
        # wait for the cards checked below to be fully rendered (state and badges), not just the first card
        pg.wait_for_selector('#ov-body .card[data-pid="gatedemo"] .pstate[data-kind="waiting"]')
        pg.wait_for_selector('#ov-body .card[data-pid="gatedemo"] .ctop .badge >> nth=1')
        pg.wait_for_selector('#ov-body .card[data-pid="framegrade"] .badges')
        # one card per project: state, name, phase with its track, next step, badges; nothing repeated from "Para ti"
        card = '#ov-body .card[data-pid="gatedemo"]'
        parts = pg.eval_on_selector(card, "c => [...c.children].map(e => e.className)")
        ct = pg.inner_text(card)
        check("overview card: state, name + badges, phase with its track, next step; nothing else",
              parts[:3] == ["pstate", "ctop", "cph"] and len(parts) <= 4 and pg.locator(card + " .ctop a.cn").inner_text() == "gatedemo"
              and pg.locator(card + " .cph .track").count() == 1 and "1/4" in ct and pg.locator(card + " .ctop .badge").count() == 2
              and "2 reports" in pg.inner_text(card + " .badges").replace("\n", " ") and "phase gate demo" not in ct and pg.locator(card + " .btn").count() == 0, (parts, ct))
        check("a project in Para ti: the card shows the red label only, no waiting reason",
              pg.get_attribute(card + " .pstate", "data-kind") == "waiting" and pg.inner_text(card + " .pstate").strip() == "Te espera"
              and "Check the colour" not in ct and "Which licence" not in ct, ct)
        fg = pg.inner_text('#ov-body .card[data-pid="framegrade"]')
        check("card badges: unread reports and open items", "1 report" in fg.replace("\n", " ") and "4 ítems" in fg.replace("\n", " "), fg)
        check("reports and resources at the bottom, folded, with counts",
              pg.evaluate("document.querySelector('#ov-body').compareDocumentPosition(document.querySelector('#ov-rep')) & 4") != 0
              and pg.is_hidden("#ov-rep-body") and pg.is_hidden("#rs-wrap") and pg.inner_text("#ov-rep-h").lower().startswith("reports sin leer · ")
              and pg.inner_text("#rs-h").lower() == "recursos en uso · 0")
        check("no summary sentence at the top, the date line stays", pg.locator("#ov-lead").count() == 0 and pg.inner_text("#ov-eyebrow").lower().startswith("proyectos · "))
        n0 = int(pg.inner_text("#bell .c"))
        check("bell counts waiting gates + messages to user", n0 == expected_bell() == 3 and "hot" in pg.get_attribute("#bell", "class"), (n0, expected_bell()))
        rep0 = int(pg.inner_text("#repcount b"))
        hub.post_message("gatedemo", "report", "Session report C", "+ ok", "gatedemo")
        pg.evaluate("refresh(true)"); pg.wait_for_function(f"+document.querySelector('#repcount b').textContent === {rep0 + 1}")
        check("a new report moves the reports counter, not the bell", int(pg.inner_text("#bell .c")) == n0)
        t = pg.inner_text("#ov-act")
        check("overview 'Para ti' lists the gates and the message", "Field test" in t and "Which licence?" in t and "Run the show file" in t and pg.locator("#ov-act .row.act .btn").count() == 0, t)
        check("'Para ti' is above the projects table", pg.evaluate("document.querySelector('#ov-act').compareDocumentPosition(document.querySelector('#ov-body')) & 4") != 0)
        check("overview headings are h2", pg.eval_on_selector_all("#overview .ph > :first-child", "e => e.every(x => x.tagName === 'H2')"))
        pg.evaluate("document.activeElement.blur()"); pg.keyboard.press("ArrowDown"); pg.wait_for_selector("#ov-body .card.sel")
        s4 = sel_style("#ov-body", "card")
        check("selected overview row distinct, marker clear of the state dot", s4["bg"] != s4["other"] and s4["gap"] >= 4, s4)

        pg.click("#bell"); pg.wait_for_selector("#bellpanel:not([hidden])")
        groups = pg.eval_on_selector_all("#bellpanel .grp", "e => e.map(x => x.dataset.pid)")
        check("bell panel grouped by project, one read-only line each, with the project state",
              groups == ["gatedemo"] and pg.locator("#bellpanel .row.act").count() == 3 and pg.locator("#bellpanel .btn").count() == 0
              and pg.get_attribute("#bellpanel .gh .pstate", "data-kind") == "waiting", groups)
        pg.click('#bellpanel a.where >> nth=0'); pg.wait_for_selector("#phead h1")
        check("a bell line links to the project and closes the panel", pg.url.endswith("#p/gatedemo") and not pg.is_visible("#bellpanel"))
        hub.mark_message(to_user["id"], "done")
        pg.goto(BASE + "/#overview"); pg.wait_for_function(f"+document.querySelector('#bell .c').textContent === {n0 - 1}")
        check("a message done in the chat leaves the bell", True)
        pg.click("#bell"); pg.wait_for_selector("#bellpanel:not([hidden])")
        pg.keyboard.press("Escape"); time.sleep(.2)
        check("Escape closes the bell panel", not pg.is_visible("#bellpanel"))
        pg.click("#bell"); pg.click("#ov-eyebrow"); time.sleep(.2)
        check("a click outside closes the bell panel", not pg.is_visible("#bellpanel"))

        # Marcar todos como leídos: each unread report of that project, nothing else
        pg.click('[data-fk="fold-ovRep"]'); pg.wait_for_selector('[data-fk="r|ov|gatedemo"]')
        pg.click('[data-fk="r|ov|gatedemo"]'); pg.wait_for_selector('#ov-rep-body .rl[data-pid="gatedemo"] .reps')
        check("reports line expands in place", pg.locator('#ov-rep-body .rl[data-pid="gatedemo"] .rep').count() == 3)
        pg.click('[data-fk="ra|ov|gatedemo"]')
        with hub._read_lock():
            fg = [m["status"] for m in hub._messages() if m["to_project"] == "framegrade" and m["kind"] == "report"]
        def gd():
            with hub._read_lock():
                return [m["status"] for m in hub._messages() if m["to_project"] == "gatedemo" and m["kind"] == "report"]
        check("Marcar todos como leídos marks every report of the project read", until(lambda: gd() == ["read"] * 3), gd())
        check("... and leaves other projects' reports alone", fg == ["unread"], fg)

        check("no window.alert / confirm / prompt in the page", not re.search(r"\b(alert|confirm|prompt)\s*\(", INDEX.replace("toggleConfirm(", "")))
        check("no browser dialog opened", not dialogs, dialogs)
        pg.set_viewport_size({"width": 1280, "height": 800})
        pg.goto(BASE + "/#p/gatedemo"); pg.wait_for_selector("#phases .row")
        check("no horizontal scroll (project)", pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
        hub.set_gate("gatedemo", ph["Build"], "x" * 160)
        pg.goto(BASE + "/#overview"); pg.wait_for_selector("#ov-act .row.act")
        check("no horizontal scroll (overview, long reason)", pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
        check("no console errors", not errors, errors)
        b.close()
finally:
    srv.terminate(); srv.wait()
print("FAILED:", fails)
