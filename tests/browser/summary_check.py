"""Resumen view: folded boxes per project, fold/expand, per-project copy marker, "nothing new" state, period, mark as seen."""
import json, os, subprocess, sys, tempfile, time, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")
from hubserver import BASE, SERVE, serve

S = Path(__file__).resolve().parent
D = Path(tempfile.mkdtemp(prefix="hub-browser-"))  # never the real data folder
subprocess.check_call([sys.executable, str(S / "seed.py"), str(D)])
from project_hub.hub import Hub
hub = Hub(D)
hub.log_decision("cuedeck", "Use OSC over UDP", "Companion speaks it natively")
hub.post_message("cuedeck", "report", "Report: macros " + "long " * 80, "+ done\n" + "wrapme " * 60, "cuedeck")

# one project per state: working (a read task), waiting (a message to Danny), ready (only news)
for pid in ("st-work", "st-wait", "st-ready"):
    hub.create_project(pid, pid, "state demo", phases=["One"])
    hub.log_decision(pid, "A decision", "so there is something new to copy")
for pid in ("st-work", "st-wait"):
    hub.mark_message(hub.post_message(pid, "task", f"Build the {pid} thing", "do it")["id"], "read")
hub.post_message("user", "message", "Need your call on the licence", "MIT?", "st-wait")

def api(method, path, body=None):
    r = urllib.request.Request(BASE + path, method=method, data=json.dumps(body).encode() if body else None, headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r))
def proj(pid): return next(p for p in api("GET", "/api/summary")["projects"] if p["id"] == pid)

srv = serve(D)
fails = []
def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name, extra); ok or fails.append(name)
try:
    two_h = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    api("POST", "/api/summary/seen", {"at": two_h})
    seen0 = api("GET", "/api/summary")["last_seen"]
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        ctx = b.new_context(viewport={"width": 1440, "height": 900}, permissions=["clipboard-read", "clipboard-write"])
        pg = ctx.new_page()
        errors = []
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errors.append(str(e)))
        clip = lambda: pg.evaluate("navigator.clipboard.readText()").replace(chr(13) + chr(10), chr(10))  # Windows clipboard turns LF into CRLF
        box = lambda pid: f'.su-proj[data-id="{pid}"]'
        pg.goto(BASE + "/"); pg.wait_for_selector("#ov-body .row")
        pg.click("#tab-su"); pg.wait_for_selector(".su-proj")
        check("button opens the view", pg.url.endswith("#resumen") and pg.is_visible("#summary"), pg.url)
        api_d = api("GET", "/api/summary")
        want = [x["id"] for x in api_d["projects"] if x["has_activity"] and x["copy"]["new"]]
        quiet = [x["name"] for x in api_d["projects"] if x["id"] not in want]
        got = pg.eval_on_selector_all(".su-proj", "e => e.map(x => x.dataset.id)")
        line = pg.inner_text(".su-quiet") if pg.query_selector(".su-quiet") else ""
        check("one box per project with news, in order; the rest in one 'Sin novedades' line", got == want and want and line.endswith("Sin novedades: " + ", ".join(quiet)), (got, want, line))
        check("boxes start folded, copy button always visible",
              pg.locator(".su-in").count() == 0 and pg.locator(".su-proj [data-copy]:visible").count() == len(want))
        check("folded line shows phase and counts", "decisi" in pg.inner_text(box("cuedeck") + " .su-head") and "/5" in pg.inner_text(box("cuedeck") + " .su-head"), pg.inner_text(box("cuedeck") + " .su-head"))
        # one state per project: Resumen box, overview row, project header
        badge = lambda pid: pg.locator(box(pid) + " .pstate")
        sts = {pid: (badge(pid).get_attribute("data-kind"), badge(pid).inner_text(), pg.inner_text(box(pid) + " [data-copy]")) for pid in ("st-work", "st-wait", "st-ready")}
        check("state 'waiting': red Te espera + the reason", sts["st-wait"][0] == "waiting" and "Te espera" in sts["st-wait"][1]
              and "Need your call on the licence" in sts["st-wait"][1] and sts["st-wait"][2] == "Copiar para el chat", sts["st-wait"])
        check("state 'working': amber Trabajando + task, button says Copiar igualmente",
              sts["st-work"][0] == "working" and "Trabajando en: Build the st-work thing" in sts["st-work"][1] and sts["st-work"][2] == "Copiar igualmente", sts["st-work"])
        check("state 'ready': green Novedades para copiar", sts["st-ready"][0] == "ready" and sts["st-ready"][1].strip() == "Novedades para copiar" and sts["st-ready"][2] == "Copiar para el chat", sts["st-ready"])
        colour = lambda pid: pg.eval_on_selector(box(pid) + " .pstate .dot", "e => getComputedStyle(e).backgroundColor")
        check("state colours: waiting red, working amber, ready green", (colour("st-wait"), colour("st-work"), colour("st-ready")) == ("rgb(255, 92, 114)", "rgb(234, 127, 42)", "rgb(63, 199, 139)"),
              (colour("st-wait"), colour("st-work"), colour("st-ready")))
        # in-place update by polling: expansion and focus survive
        pg.click('[data-fk="su|st-ready"]'); pg.wait_for_selector(box("st-ready") + " .su-in")
        pg.focus('[data-fk="su|st-ready"]')
        hub.mark_message(hub.post_message("st-ready", "task", "Late task", "x")["id"], "read")
        pg.wait_for_function("document.querySelector('.su-proj[data-id=\"st-ready\"] .pstate').dataset.kind === 'working'", timeout=12000)
        check("polling updates the badge and button in place; box stays open, focus kept",
              pg.inner_text(box("st-ready") + " [data-copy]") == "Copiar igualmente" and pg.locator(box("st-ready") + " .su-in").count() == 1
              and pg.evaluate("document.activeElement.dataset.fk") == "su|st-ready")
        pg.click('[data-fk="su|st-ready"]')
        pg.click("#tab-ov"); pg.wait_for_selector("#ov-body .row")
        row = lambda pid: f'#ov-body .row[data-pid="{pid}"]'
        kinds = {pid: pg.get_attribute(row(pid) + " .stc .pstate", "data-kind") for pid in ("st-work", "st-wait", "led-mapper")}
        check("overview: the state replaces the status column, lifecycle as a small label",
              kinds == {"st-work": "working", "st-wait": "waiting", "led-mapper": "stopped"} and pg.inner_text(row("led-mapper") + " .stc .life") == "TERMINADO", kinds)
        check("overview: red and amber show their text in the row", "Need your call on the licence" in pg.inner_text(row("st-wait") + " .why-st")
              and "Build the st-work thing" in pg.inner_text(row("st-work") + " .why-st") and pg.locator(row("led-mapper") + " .why-st").count() == 0)
        order = pg.eval_on_selector_all("#ov-body .row", "e => e.map(x => x.querySelector('.stc .pstate').dataset.kind)")
        check("red rows sort first", order[0] == "waiting" and "waiting" not in order[order.count("waiting"):], order)
        pg.goto(BASE + "/#p/st-wait"); pg.wait_for_selector("#phead h1")
        check("project header shows the same state", pg.get_attribute("#phead .pstate", "data-kind") == "waiting" and "Need your call" in pg.inner_text("#phead .pstate"))
        pg.click("#tab-su"); pg.wait_for_selector(".su-proj")
        # fold / expand
        pg.click(f'[data-fk="su|cuedeck"]'); pg.wait_for_selector(box("cuedeck") + " .su-in")
        secs = pg.eval_on_selector_all(box("cuedeck") + " .su-sec", "e => e.map(x => x.dataset.sec)")
        check("expanding shows the sections, each folded with its count", "reports" in secs and "dec" in secs and pg.locator(box("cuedeck") + " .su-rows").count() == 0
              and "Reports · 1" in pg.inner_text(box("cuedeck") + ' [data-sec="reports"]'), secs)
        pg.click('[data-fk="su|cuedeck|reports"]'); pg.wait_for_selector(box("cuedeck") + " .su-rows details")
        check("report body wraps, no horizontal scroll", pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"))
        pg.click(box("cuedeck") + " .su-rows details summary"); time.sleep(.2)
        pg.evaluate("refresh(true)"); time.sleep(.5)
        check("expanded report survives refresh", pg.evaluate(f"document.querySelector('{box('cuedeck')} .su-rows details').open"))
        pg.click(f'[data-fk="su|cuedeck"]'); time.sleep(.2)
        check("folding the box hides the sections", pg.locator(box("cuedeck") + " .su-in").count() == 0)
        # per-project copy marker
        exp = pg.evaluate("S.sumD.projects.find(p => p.id === 'cuedeck').copy.chat_text")
        until = pg.evaluate("S.sumD.until")
        pg.click('[data-copy="cuedeck"]')
        pg.wait_for_function("S.sumD.projects.find(p => p.id === 'cuedeck').copied_at")
        c1 = proj("cuedeck")
        check("copy puts the project's chat text on the clipboard", clip() == exp and len(exp) > 20, (clip(), exp))
        check("copy stores the project's marker at the until on screen", c1["copied_at"] and c1["copied_at"].startswith(until[:19]) and c1["copy"]["new"] == 0, c1["copied_at"])
        check("copy confirmed in aria-live", "Copiado" in pg.inner_text("#toasts"))
        st = pg.inner_text(box("cuedeck") + " .su-cs"); btn = pg.locator(box("cuedeck") + " [data-copy]")
        check("after copying: 'copiado', button says nothing new and is disabled", st.startswith("copiado") and btn.inner_text() == "Nada nuevo desde la última copia" and btn.is_disabled(), (st, btn.inner_text()))
        check("state 'quiet' after the copy: Sin novedades", badge("cuedeck").get_attribute("data-kind") == "quiet" and "Sin novedades" in badge("cuedeck").inner_text()
              and pg.eval_on_selector(box("cuedeck") + " .pstate .dot", "e => getComputedStyle(e).backgroundColor") == "rgb(108, 113, 115)", badge("cuedeck").inner_text())
        pg.evaluate("navigator.clipboard.writeText('untouched')")
        btn.click(force=True); time.sleep(.3)
        check("nothing new copies nothing", clip() == "untouched" and proj("cuedeck")["copied_at"] == c1["copied_at"])
        others = [x for x in want if x != "cuedeck"]
        check("other projects keep their own marker", all(proj(x)["copied_at"] is None for x in others), others)
        hub.log_decision("cuedeck", "Second decision", "new after the copy")
        time.sleep(1.1)  # markers and timestamps have 1 s resolution and the copy window starts inclusive at the marker
        pg.click('[data-p="24"]'); pg.click('[data-p="0"]'); pg.wait_for_function("S.sumD.projects.find(p => p.id === 'cuedeck').copy.new === 1")
        st = pg.inner_text(box("cuedeck") + " .su-cs")
        check("new activity shows 'N novedades desde la última copia'", st == "1 novedad desde la última copia" and not pg.is_disabled(box("cuedeck") + " [data-copy]"), st)
        exp2 = pg.evaluate("S.sumD.projects.find(p => p.id === 'cuedeck').copy.chat_text")
        pg.click('[data-copy="cuedeck"]'); pg.wait_for_function("S.sumD.projects.find(p => p.id === 'cuedeck').copy.new === 0")
        check("second copy holds only what is new since the first", clip() == exp2 and exp2 != exp and "1 decisión" in exp2, exp2)
        pg.click("#tab-ov"); pg.wait_for_selector("#ov-body .row")
        check("closing without marking leaves last_seen", api("GET", "/api/summary")["last_seen"] == seen0)
        pg.goto(BASE + "/#resumen"); pg.wait_for_function("S.sumD")
        check("a copied project with nothing new folds into 'Sin novedades'", pg.locator(box("cuedeck")).count() == 0 and "cuedeck" in pg.inner_text(".su-quiet"))
        since1 = pg.inner_text("#su-since")
        pg.click('[data-p="24"]'); pg.wait_for_function("S.sumHours === 24 && S.sumD && document.querySelector('.su-proj[data-id=cuedeck]')")
        check("últimas 24 h shows every active project again, without touching markers", pg.inner_text("#su-since") != since1 and proj("cuedeck")["copied_at"] != c1["copied_at"]
              and all(proj(x)["copied_at"] is None for x in others))
        pg.click('[data-p="0"]'); pg.wait_for_function("S.sumHours === 0 && S.sumD")
        until = pg.evaluate("S.sumD.until")
        pg.click("#su-seen"); time.sleep(.7)
        seen1 = api("GET", "/api/summary")["last_seen"]
        check("mark as seen (secondary) persists the until of the view", seen1 != seen0 and seen1.startswith(until[:19]), (seen0, seen1, until))
        pg.reload(); pg.wait_for_function("document.querySelector('#su-since').textContent")
        shown = pg.text_content("#su-since")  # not inner_text: the eyebrow is uppercased by CSS
        check("after reload, desde moves to the marked time", shown == "desde " + pg.evaluate(f"new Date('{seen1}').toLocaleString()"), shown)
        check("no window.alert / confirm dialogs and no console errors", not errors, errors)
        b.close()
finally:
    srv.terminate(); srv.wait()
print("FAILED:", fails)
