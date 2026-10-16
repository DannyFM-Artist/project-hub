import os, sys, subprocess, time, shutil, urllib.request
import tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8"); sys.stderr.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
from hubserver import BASE, PORT, SERVE

S = Path(__file__).resolve().parent
D = Path(tempfile.mkdtemp(prefix="hub-browser-"))  # never the real data folder
subprocess.check_call([sys.executable, str(S / "seed.py"), str(D)])
from project_hub.hub import Hub
hub = Hub(D)
env = dict(os.environ, PROJECT_HUB_DATA=str(D))


def start():
    p = subprocess.Popen(SERVE, env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        try:
            urllib.request.urlopen(BASE + "/api/projects"); return p
        except Exception:
            time.sleep(.2)
    raise SystemExit("server did not start")


srv = start()
res = []


def check(name, cond, extra=""):
    res.append((name, bool(cond))); print(("PASS " if cond else "FAIL ") + name, extra, flush=True)


def items(): return {i["title"]: i for i in hub.get_project("framegrade")["items"]}
def msgs(): return {m["title"]: m for m in hub.read_inbox("framegrade", unread_only=False)}
errors = []
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_page(viewport={"width": 1440, "height": 1000})
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(BASE + "/"); pg.wait_for_selector("tr.row")
    # 1
    pg.click("#ov-filter >> text=paused"); n1 = pg.locator("tr.row").count()
    pg.click("#ov-filter >> text=all")
    names = pg.locator("tr.row td.name a").all_inner_texts()
    pg.keyboard.press("ArrowDown"); pg.keyboard.press("ArrowDown"); pg.keyboard.press("Enter")
    pg.wait_for_selector("#phead h2")
    sel_name = pg.inner_text("#phead h2")
    ok1 = n1 == 1 and sel_name == names[2] and "#p/" in pg.url
    pg.reload(); pg.wait_for_selector("#phead h2"); ok1 &= pg.inner_text("#phead h2") == sel_name
    pg.keyboard.press("1"); pg.wait_for_selector("tr.row")
    time.sleep(.3)
    focus_ov = pg.evaluate("!!(document.activeElement.closest('tr') && document.activeElement.closest('tr').classList.contains('sel'))")
    pg.click("tr.row >> nth=0"); pg.wait_for_selector("#phead h2")
    ok1 &= pg.inner_text("#phead h2") == names[0]
    check("1 overview filter / keys / click / hash reload", ok1, names)
    pg.goto(BASE + "/#p/framegrade"); pg.wait_for_selector("#phead h2"); time.sleep(.3)
    check("2a focus on h2 on project open", pg.evaluate("document.activeElement.tagName") == "H2")
    check("2b focus on selected row on return to overview", focus_ov)
    # 2 phases
    ph = hub.get_project("framegrade")["phases"]
    pg.click(f"[data-fk='ph{ph[3]['id']}']"); pg.click(".cue.sel .selst >> text=done")
    pg.wait_for_function("document.querySelectorAll('.cue.done').length==3")
    c = hub.get_project("framegrade")["phases"][3]["status"] == "done"
    pg.click(f"[data-fk='ph{ph[4]['id']}']"); pg.evaluate("document.activeElement.blur()")
    pg.keyboard.press(" "); pg.wait_for_function("document.querySelectorAll('.cue.in_progress').length==1")
    c &= hub.get_project("framegrade")["phases"][4]["status"] == "in_progress"
    check("2 phase status by click and by space", c)
    # 3
    pg.click("text=[a]dd"); pg.wait_for_selector("#f-item:not([hidden])")
    pg.click("#f-item button[type=submit]")
    err = pg.inner_text("#f-item .ferr"); still = pg.is_visible("#f-item")
    foc = pg.evaluate("document.activeElement.name") == "title"
    pg.fill("#f-item [name=title]", "Btn item"); pg.fill("#f-item [name=details]", "keep me")
    pg.route("**/api/projects/framegrade/items", lambda r: (time.sleep(1), r.continue_()))
    pg.click("#f-item button[type=submit]")
    dis = pg.is_disabled("#f-item button[type=submit]")
    pg.wait_for_selector("#f-item", state="hidden"); pg.unroute("**/api/projects/framegrade/items")
    ok = "required" in err.lower() and still and foc and dis and "Btn item" in items() and items()["Btn item"]["details"] == "keep me"
    pg.evaluate("document.activeElement.blur()"); pg.keyboard.press("a"); pg.wait_for_selector("#f-item:not([hidden])")
    typed_a = pg.input_value("#f-item [name=title]") == ""
    pg.select_option("#f-item [name=type]", "idea"); pg.fill("#f-item [name=title]", "Key item")
    pg.click("#f-item button[type=submit]"); pg.wait_for_selector("#f-item", state="hidden")
    check("3 add item (button, a key, inline error, focus, in-flight disabled)", ok and typed_a and items()["Key item"]["type"] == "idea", (err, still, foc, dis))
    pg.click("text=[a]dd"); pg.fill("#f-item [name=title]", "xxxxx")
    pg.evaluate("document.querySelector('#f-item [name=type]').insertAdjacentHTML('beforeend','<option value=zzz>zzz</option>')")
    pg.select_option("#f-item [name=type]", "zzz")
    pg.click("#f-item button[type=submit]"); pg.wait_for_selector("#f-item .ferr:not(:empty)")
    e2 = pg.inner_text("#f-item .ferr")
    check("3b API error: inline + toast, form open, text kept, focus on type",
          pg.is_visible("#f-item") and pg.input_value("#f-item [name=title]") == "xxxxx" and "invalid item type" in e2
          and pg.evaluate("document.activeElement.name") == "type" and pg.locator(".toast.err").count() >= 1, (e2, pg.is_visible("#f-item"), pg.input_value("#f-item [name=title]"), pg.evaluate("document.activeElement.name+document.activeElement.tagName"), pg.locator(".toast.err").count()))
    pg.click("#f-item [data-cancel]"); pg.evaluate("document.querySelector('#f-item').reset()")
    # 4
    def row(t): return pg.locator(".it", has_text=t)
    row("Key item").locator(".itbtn").click()
    row("Key item").get_by_label("Move to planned: Key item").click()
    time.sleep(.6); a = items()["Key item"]["status"] == "planned"
    pg.keyboard.press("ArrowRight"); time.sleep(.6); a &= items()["Key item"]["status"] == "done"
    pg.keyboard.press("ArrowLeft"); time.sleep(.6); a &= items()["Key item"]["status"] == "planned"
    row("Key item").get_by_label("Discard item: Key item").click(); time.sleep(.6); a &= items()["Key item"]["status"] == "discarded"
    gone = pg.locator(".it", has_text="Key item").count() == 0
    pg.evaluate("document.activeElement.blur()")
    pg.keyboard.press("x"); pg.wait_for_selector(".kc.dc"); shown = pg.locator(".kc.dc .it", has_text="Key item").count() == 1
    pg.locator(".kc.dc .it", has_text="Key item").get_by_label("Restore to open: Key item").click(); time.sleep(.6); a &= items()["Key item"]["status"] == "open"
    pg.locator(".it", has_text="Key item").locator(".itbtn").click()
    pg.keyboard.press("ArrowRight"); time.sleep(.6); a &= items()["Key item"]["status"] == "planned"
    pg.click("#chips >> text=discarded"); pg.wait_for_selector(".kc.dc", state="detached")
    check("4 move by button/keys, discard, restore, show-discarded toggle", a and gone and shown)
    # 5
    pg.click("#msg-open"); pg.wait_for_selector("#f-msg:not([hidden])")
    pg.select_option("#f-msg [name=kind]", "task"); pg.fill("#f-msg [name=title]", "Btn msg"); pg.fill("#f-msg [name=body]", "b1")
    pg.click("#f-msg button[type=submit]"); pg.wait_for_selector("#f-msg", state="hidden")
    pg.evaluate("document.activeElement.blur()"); pg.keyboard.press("m"); pg.wait_for_selector("#f-msg:not([hidden])")
    pg.select_option("#f-msg [name=to]", "all"); pg.fill("#f-msg [name=title]", "All msg"); pg.fill("#f-msg [name=body]", "b2")
    pg.click("#f-msg button[type=submit]"); pg.wait_for_selector("#f-msg", state="hidden")
    allm = [m for m in hub.read_inbox("cuedeck", unread_only=False) if m["title"] == "All msg"]
    mm = msgs()
    check("5 post message (button task to project, m key to all)", mm["Btn msg"]["kind"] == "task" and mm["Btn msg"]["to_project"] == "framegrade" and allm and allm[0]["to_project"] == "all")
    # 6
    pg.locator(".m", has_text="Btn msg").get_by_role("button", name="Mark read").click(); time.sleep(.6)
    ok6 = msgs()["Btn msg"]["status"] == "read"
    pg.locator(".m", has_text="Btn msg").get_by_role("button", name="Mark done").click(); time.sleep(.6)
    ok6 &= msgs()["Btn msg"]["status"] == "done"
    pg.locator(".m", has_text="All msg").locator(".k").click(); pg.evaluate("document.activeElement.blur()")
    pg.keyboard.press("r"); time.sleep(.6); ok6 &= msgs()["All msg"]["status"] == "read"
    pg.keyboard.press("d"); time.sleep(.6); ok6 &= msgs()["All msg"]["status"] == "done"
    check("6 mark read/done by button and r/d", ok6)
    # 7
    pg.click("#chips >> text=bug"); pg.evaluate("document.activeElement.blur()"); pg.keyboard.press("a")
    pg.fill("#f-item [name=title]", "typing across poll"); pg.locator("#f-item [name=title]").focus()
    t0 = pg.inner_text("#sync"); time.sleep(6.5); t1 = pg.inner_text("#sync")
    ok7 = (t0 != t1) and pg.input_value("#f-item [name=title]") == "typing across poll" and pg.evaluate("document.activeElement.name") == "title" \
        and pg.locator("#chips button.on").inner_text() == "bug" and pg.is_visible("#f-item")
    pg.click("#f-item [data-cancel]")
    pg.locator(".it").first.locator(".itbtn").click(); sid = pg.locator(".it.sel").get_attribute("data-id")
    hub.add_item("framegrade", "bug", "external", ""); time.sleep(6.5)
    ok7 &= pg.locator(".it.sel").get_attribute("data-id") == sid and pg.locator(".it", has_text="external").count() == 1 \
        and pg.evaluate("document.activeElement.className") == "itbtn"
    check("7 poll keeps form text, focus, selection, filter; picks up external change", ok7, (t0, t1))
    pg.click("#chips >> text=all")
    # 8
    pg.evaluate("document.activeElement.blur()"); pg.keyboard.press("a"); pg.locator("#f-item [name=title]").focus()
    pg.fill("#f-item [name=title]", ""); pg.locator("#f-item [name=title]").focus(); pg.keyboard.type("1m xrd2")
    v = pg.input_value("#f-item [name=title]")
    check("8 shortcuts ignored while typing", v == "1m xrd2" and pg.is_visible("#f-item") and "#p/framegrade" in pg.url and not pg.is_visible("#f-msg"), v)
    pg.click("#f-item [data-cancel]")
    # target sizes and headings
    small = pg.evaluate("""()=>[...document.querySelectorAll('button:not(.itbtn):not(.main):not(#msg-open):not(.k):not(.ia button),.tab')].filter(e=>e.offsetParent).map(e=>{const r=e.getBoundingClientRect();return [e.textContent.trim().slice(0,20),Math.round(r.width),Math.round(r.height)]}).filter(x=>x[1]<24||x[2]<24)""")
    pg.locator(".it").first.locator(".itbtn").click()
    small += pg.evaluate("""()=>[...document.querySelectorAll('.it.sel .ia button')].map(e=>{const r=e.getBoundingClientRect();return [e.title,Math.round(r.width),Math.round(r.height)]}).filter(x=>x[1]<24||x[2]<24)""")
    check("A target size >=24px (.k message labels use a ::after overlay)", not small, small)
    heads = pg.evaluate("[...document.querySelectorAll('h1,#phead h2,#project h3')].map(e=>e.tagName+':'+e.firstChild.textContent.trim())")
    check("B headings h1/h2/h3", heads[:2] == ["H1:project-hub", "H2:framegrade"] and sum(x.startswith("H3") for x in heads) == 4, heads)
    # 9
    n_before = len(errors)
    srv.terminate(); srv.wait(); time.sleep(6.5)
    off = pg.inner_text("#sync")
    srv = start(); time.sleep(6.5)
    on = pg.inner_text("#sync")
    check("9 offline line shown, then cleared", f"Can't reach the hub at 127.0.0.1:{PORT}. Retrying every 5 s." in off and "poll 5s" in on and "Can't" not in on, (off, on))
    real = errors[:n_before] + [e for e in errors[n_before:] if "Failed to load resource" not in e and "ERR_CONNECTION" not in e and "Failed to fetch" not in e]
    # the invalid-type 400 of check 3b is a deliberate error response
    real = [e for e in real if "400" not in e]
    check("10 no console errors", not real, real)
    b.close()
srv.terminate()
print("FAILED:", [n for n, ok in res if not ok])
