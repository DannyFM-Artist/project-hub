"""Phase gates against the real backend: set / approve / mark done / remove, inline confirmations, "Para ti", bell, reports, selection."""
import os, re, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
from hubserver import BASE, SERVE, until

S = Path(__file__).resolve().parent
D = Path(tempfile.mkdtemp(prefix="hub-browser-"))  # never the real data folder
subprocess.check_call([sys.executable, str(S / "seed.py"), str(D)])
from project_hub.hub import Hub
from project_hub.biblia import blocking
hub = Hub(D)
hub.create_project("gatedemo", "gatedemo", "phase gate demo", phases=["Plan", "Build", "Field test", "Ship"])
ph = {p["name"]: p["id"] for p in hub.get_project("gatedemo")["phases"]}
hub.set_phase_status("gatedemo", ph["Plan"], "done")
to_user = hub.post_message("user", "message", "Which licence?", "MIT or proprietary", "gatedemo")
hub.post_message("gatedemo", "report", "Session report A", "+ ok", "gatedemo")
hub.post_message("gatedemo", "report", "Session report B", "+ ok", "gatedemo")
gate = lambda name: hub.get_project("gatedemo")["phases"][list(ph).index(name)]
INDEX = (S.parents[1] / "project_hub" / "static" / "index.html").read_text(encoding="utf-8")

srv = subprocess.Popen(SERVE, env=dict(os.environ, PROJECT_HUB_DATA=str(D)), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
fails = []
def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name, extra); ok or fails.append(name)
def expected_bell():
    ps = hub.list_projects()
    return sum(blocking(x) for p in ps for x in p["phases"]) + sum(
        1 for m in hub._messages() if m["to_project"] == "user" and m["status"] != "done")
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
        row = lambda name: f'#phases .row[data-id="{ph[name]}"]'
        pg.goto(BASE + "/#p/gatedemo"); pg.wait_for_selector("#phases .row")
        check("autonomy line shown", "Autonomous work allowed up to phase" in pg.inner_text("#pr-aut"), pg.inner_text("#pr-aut"))

        def set_gate(name, kind, reason, words):
            pg.click(f'[data-fk="ph{ph[name]}"]')
            pg.select_option(f"#gs{ph[name]}", kind)
            pg.fill(f"#gr{ph[name]}", reason)
            pg.click(f'[data-fk="gset{ph[name]}"]')
            # wait for the rendered state, not a fixed time: the row shows every word once the refresh has painted it
            pg.wait_for_function("([sel, words]) => { const r = document.querySelector(sel); return r && words.every(w => r.innerText.includes(w)); }", arg=[row(name), words])

        # half-typed reason survives a poll
        pg.click(f'[data-fk="ph{ph["Build"]}"]'); pg.fill(f"#gr{ph['Build']}", "half typ")
        pg.evaluate("refresh(true)"); time.sleep(.5)
        check("draft reason survives refresh", pg.input_value(f"#gr{ph['Build']}") == "half typ")

        set_gate("Build", "review", "Check the colour pipeline before Build ships", ["REVIEW", "sin aprobar", "colour pipeline"])
        g = gate("Build")
        check("review gate set via UI (by user)", g["gate"] == "review" and g["gate_set_by"] == "user" and not g["gate_approved"] and "colour pipeline" in g["gate_reason"], g)
        check("badge + reason on the phase row", all(w in pg.inner_text(row("Build")) for w in ("REVIEW", "sin aprobar", "colour pipeline")), pg.inner_text(row("Build")))
        set_gate("Field test", "manual_test", "Run the show file on the real LED wall", ["TEST MANUAL", "LED wall"])
        check("manual_test gate set via UI", gate("Field test")["gate"] == "manual_test")
        pg.click('[data-fk="done|gatedemo"]')  # Plan is done: unfold the done line, then select it
        pg.click(f'[data-fk="ph{ph["Plan"]}"]'); pg.wait_for_selector(row("Plan") + ".sel")
        check("gate buttons always visible on their rows, nothing selected first",
              pg.is_visible(f'[data-fk="b|ph|gatedemo:g:{ph["Build"]}"]') and pg.inner_text(f'[data-fk="b|ph|gatedemo:g:{ph["Build"]}"]') == "Aprobar"
              and pg.inner_text(f'[data-fk="b|ph|gatedemo:g:{ph["Field test"]}"]') == "Marcar como hecha"
              and pg.is_visible(f'[data-fk="b|pv|gatedemo:g:{ph["Build"]}"]') and pg.is_visible(f'[data-fk="b|pv|gatedemo:g:{ph["Field test"]}"]'))

        # selected row: tint + accent edge, and the edge never overlaps the row's content
        def sel_style(list_sel):
            return pg.evaluate("""(s) => { const sel = document.querySelector(s + ' .row.sel'), other = document.querySelector(s + ' .row:not(.sel)');
                const cs = getComputedStyle(sel), co = getComputedStyle(other), r = sel.getBoundingClientRect();
                const first = sel.firstElementChild, inner = first.querySelector('.dot') || first, c = inner.getBoundingClientRect();
                const edge = r.left + parseFloat(cs.borderLeftWidth);
                return { bg: cs.backgroundColor, other: co.backgroundColor, edge: cs.borderLeftColor, w: cs.borderLeftWidth, gap: c.left - edge }; }""", list_sel)
        s1 = sel_style("#phases")
        check("selected phase row is distinct (tint + accent left border)", s1["bg"] != s1["other"] and s1["edge"] == "rgb(136, 254, 0)" and s1["w"] == "2px", s1)
        check("selection marker does not overlap the phase row content", s1["gap"] >= 4, s1)
        hub.add_item("gatedemo", "bug", "A bug", "d"); hub.add_item("gatedemo", "idea", "An idea", "d")
        pg.evaluate("refresh(true)"); pg.wait_for_selector(".items .row >> text=An idea"); pg.locator(".items .row .t").first.click(); pg.wait_for_selector(".items .row.sel")
        s2 = sel_style(".items")
        check("selected item row distinct, marker clear of content", s2["bg"] != s2["other"] and s2["edge"] == "rgb(136, 254, 0)" and s2["gap"] >= 4, s2)
        hub.post_message("gatedemo", "task", "Plain task", "body")
        pg.evaluate("refresh(true)"); pg.wait_for_selector(".inbox .row >> text=Plain task")
        pg.locator(".inbox .row .t").first.click(); pg.wait_for_selector(".inbox .row.sel")
        s3 = sel_style(".inbox")
        check("selected inbox row distinct, marker clear of content", s3["bg"] != s3["other"] and s3["gap"] >= 4, s3)

        # Aprobar: cancel changes nothing, confirm approves
        ck = f'ph|gatedemo:g:{ph["Build"]}'
        pg.click(f'[data-fk="b|{ck}"]')
        q = pg.inner_text(f'.confirm[data-ck="{ck}"]')
        check("Aprobar opens an inline confirmation naming project and phase", "¿Aprobar el gate de «Build» en gatedemo?" in q, q)
        pg.click(f'[data-fk="n|{ck}"]'); time.sleep(.4)
        check("Aprobar + Cancelar: closes, nothing changes", pg.locator(f'.confirm[data-ck="{ck}"]').count() == 0 and gate("Build")["gate_approved"] is False)
        pg.click(f'[data-fk="b|{ck}"]'); pg.click(f'[data-fk="y|{ck}"]')
        check("Aprobar + Sí: gate approved", until(lambda: gate("Build")["gate_approved"] is True), gate("Build"))
        pg.wait_for_function("([sel]) => document.querySelector(sel).innerText.includes('REVIEW ✓')", arg=[row("Build")])
        hub.set_phase_status("gatedemo", ph["Build"], "done", by="user")

        # Marcar como hecha from the project's "Para ti": cancel, then confirm
        ck = f'pv|gatedemo:g:{ph["Field test"]}'
        pg.evaluate("refresh(true)"); pg.wait_for_selector(f'[data-fk="b|{ck}"]')
        pg.click(f'[data-fk="b|{ck}"]')
        q = pg.inner_text(f'.confirm[data-ck="{ck}"]')
        check("Marcar como hecha opens an inline confirmation naming project and phase", "¿Marcar como hecha la fase «Field test» en gatedemo?" in q, q)
        pg.click(f'[data-fk="n|{ck}"]'); time.sleep(.4)
        check("Marcar como hecha + Cancelar: nothing changes", pg.locator(f'.confirm[data-ck="{ck}"]').count() == 0 and gate("Field test")["status"] == "todo")

        # bell: blocking gates + messages to user, not reports
        pg.goto(BASE + "/#overview"); pg.wait_for_selector("#ov-body .row")
        n0 = int(pg.inner_text("#bell .c"))
        check("bell counts waiting gates + messages to user", n0 == expected_bell() == 2 and "hot" in pg.get_attribute("#bell", "class"), (n0, expected_bell()))
        rep0 = int(pg.inner_text("#repcount b"))
        hub.post_message("gatedemo", "report", "Session report C", "+ ok", "gatedemo")
        pg.evaluate("refresh(true)"); pg.wait_for_function(f"+document.querySelector('#repcount b').textContent === {rep0 + 1}")
        check("a new report moves the reports counter, not the bell", int(pg.inner_text("#bell .c")) == n0)
        t = pg.inner_text("#ov-act")
        check("overview 'Para ti' lists the gate and the message", "Field test" in t and "Which licence?" in t and "Run the show file" in t, t)
        check("'Para ti' is above the projects table", pg.evaluate("document.querySelector('#ov-act').compareDocumentPosition(document.querySelector('#ov-body')) & 4") != 0)
        check("overview headings are h2", pg.eval_on_selector_all("#overview .ph > :first-child", "e => e.every(x => x.tagName === 'H2')"))
        pg.evaluate("document.activeElement.blur()"); pg.keyboard.press("ArrowDown"); pg.wait_for_selector("#ov-body .row.sel")
        s4 = sel_style("#ov-body")
        check("selected overview row distinct, marker clear of the status dot", s4 and s4["bg"] != s4["other"] and s4["gap"] >= 4, s4)

        pg.click("#bell"); pg.wait_for_selector("#bellpanel:not([hidden])")
        groups = pg.eval_on_selector_all("#bellpanel .grp", "e => e.map(x => x.dataset.pid)")
        check("bell panel grouped by project with each action", groups == ["gatedemo"] and pg.locator("#bellpanel .row.act").count() == 2, groups)
        ckm = f'bell|gatedemo:m:{to_user["id"]}'
        pg.click(f'[data-fk="b|{ckm}"]'); pg.click(f'[data-fk="y|{ckm}"]')
        ok = until(lambda: next(m for m in hub._messages() if m["id"] == to_user["id"])["status"] == "done")
        pg.wait_for_function(f"+document.querySelector('#bell .c').textContent === {n0 - 1}")
        check("bell panel: message marked done, panel stays open, count drops", ok and pg.is_visible("#bellpanel"))
        ckg = f'bell|gatedemo:g:{ph["Field test"]}'
        pg.click(f'[data-fk="b|{ckg}"]'); pg.click(f'[data-fk="y|{ckg}"]')
        check("bell panel: Marcar como hecha + Sí marks the phase done", until(lambda: gate("Field test")["status"] == "done"), gate("Field test"))
        pg.wait_for_function("document.querySelector('#bell .c').textContent === '0'")
        check("bell neutral at zero", "hot" not in pg.get_attribute("#bell", "class") and "Nada espera tu acción" in pg.inner_text("#bellpanel"))
        pg.keyboard.press("Escape"); time.sleep(.2)
        check("Escape closes the bell panel", not pg.is_visible("#bellpanel"))
        pg.click("#bell"); pg.click("#ov-eyebrow"); time.sleep(.2)
        check("a click outside closes the bell panel", not pg.is_visible("#bellpanel"))

        # Marcar todos como leídos: each unread report of that project, nothing else
        pg.click('[data-fk="r|ov|gatedemo"]'); pg.wait_for_selector('#ov-rep-body .rl[data-pid="gatedemo"] .reps')
        check("reports line expands in place", pg.locator('#ov-rep-body .rl[data-pid="gatedemo"] .rep').count() == 3)
        pg.click('[data-fk="ra|ov|gatedemo"]')
        gd = lambda: [m["status"] for m in hub._messages() if m["to_project"] == "gatedemo" and m["kind"] == "report"]
        fg = [m["status"] for m in hub._messages() if m["to_project"] == "framegrade" and m["kind"] == "report"]
        check("Marcar todos como leídos marks every report of the project read", until(lambda: gd() == ["read"] * 3), gd())
        check("... and leaves other projects' reports alone", fg == ["unread"], fg)

        # status selector to done on a gated phase asks first
        hub.set_gate("gatedemo", ph["Ship"], "review", "temp", by="user")
        pg.goto(BASE + "/#p/gatedemo"); pg.wait_for_selector("#phases .row")
        pg.click(f'[data-fk="ph{ph["Ship"]}"]'); pg.select_option(f"#st-{ph['Ship']}", "done")
        ck = f'st|gatedemo:{ph["Ship"]}'
        pg.wait_for_selector(f'.confirm[data-ck="{ck}"]')
        check("selector to done on a gated phase asks for confirmation", gate("Ship")["status"] == "todo" and "¿Cambiar «Ship» a hecha en gatedemo?" in pg.inner_text(f'.confirm[data-ck="{ck}"]'))
        pg.click(f'[data-fk="n|{ck}"]'); time.sleep(.4)
        check("Cancelar reverts the selector and changes nothing", pg.input_value(f"#st-{ph['Ship']}") == "todo" and gate("Ship")["status"] == "todo")
        pg.select_option(f"#st-{ph['Ship']}", "done"); pg.click(f'[data-fk="y|{ck}"]')
        check("Sí, cambiar a hecha saves it", until(lambda: gate("Ship")["status"] == "done"))
        set_gate("Ship", "none", "", [])
        check("gate removed via UI", until(lambda: gate("Ship")["gate"] == "none"), gate("Ship"))

        check("no window.alert / confirm / prompt in the page", not re.search(r"\b(alert|confirm|prompt)\s*\(", INDEX.replace("toggleConfirm(", "").replace("gateConfirm(", "")))
        check("no browser dialog opened", not dialogs, dialogs)
        pg.set_viewport_size({"width": 1280, "height": 800})
        check("no horizontal scroll (project)", pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
        hub.set_gate("gatedemo", ph["Ship"], "manual_test", "x" * 160, by="user")
        hub.set_phase_status("gatedemo", ph["Ship"], "todo", by="user")
        pg.goto(BASE + "/#overview"); pg.wait_for_selector("#ov-act .row.act")
        check("no horizontal scroll (overview, long reason)", pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
        hub.create_project("chatdemo", "chatdemo", "chat approval", phases=["Rev", "Test"])
        cid, tid = [x["id"] for x in hub.get_project("chatdemo")["phases"]]
        hub.set_gate("chatdemo", cid, "review", "check it")
        hub.approve_gate_chat("chatdemo", cid, "sí, apruebo esta fase " + "y " * 50)
        hub.set_gate("chatdemo", tid, "manual_test", "try it")
        hub.complete_manual_phase("chatdemo", tid, "probado en el muro, va bien")
        pg.goto(BASE + "/#p/chatdemo"); pg.wait_for_selector("#phases .row")
        badge = pg.inner_text(f'#phases .row[data-id="{cid}"] .gc')
        check("review row: badge shows aprobado vía chat, shortened", "aprobado vía chat: «sí, apruebo esta fase" in badge and "…»" in badge, badge)
        check("full words in the tooltip", "y y y y" in (pg.get_attribute(f'#phases .row[data-id="{cid}"] .gc .chat', "title") or ""))
        check("selected row detail names the chat approval", "aprobado vía chat: «sí, apruebo" in pg.inner_text(f'#phases .row[data-id="{cid}"] .detail .gr'))
        t = pg.inner_text(f'#phases .row[data-id="{tid}"] .gc')
        check("manual_test completed via chat shows the same badge", "aprobado vía chat: «probado en el muro, va bien»" in t, t)
        check("no console errors", not errors, errors)
        b.close()
finally:
    srv.terminate(); srv.wait()
print("FAILED:", fails)
