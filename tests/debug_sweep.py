"""Debug sweep: taps every visible button on every screen, and checks the page for common bugs.
Run: CHROME_PATH=/path/to/chrome python3 tests/debug_sweep.py
"""
import os, json
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
APP = "file://" + os.path.abspath(os.path.join(HERE, "..", "index.html"))
problems, info = [], []

with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path=os.environ.get("CHROME_PATH") or None, args=["--no-sandbox"])
    p = b.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True).new_page()
    p.on("pageerror", lambda e: problems.append(f"JS error: {e}"))
    p.on("console", lambda m: m.type == "error" and "fonts.g" not in (m.location.get("url") or "") and problems.append("console: " + m.text))
    p.on("dialog", lambda d: (problems.append("unexpected popup dialog: " + d.message), d.dismiss()))
    p.on("popup", lambda pg: pg.close())
    p.route("**/fonts.g*/**", lambda r: r.abort())
    p.route("http*://**", lambda r: r.abort() if "file://" not in r.request.url else r.continue_())
    p.goto(APP); p.wait_for_timeout(300)

    # static checks
    dup = p.evaluate("""(()=>{const c={};document.querySelectorAll('[id]').forEach(e=>c[e.id]=(c[e.id]||0)+1);return Object.entries(c).filter(([k,v])=>v>1)})()""")
    if dup: problems.append(f"duplicate element ids: {dup}")
    noname = p.evaluate("""[...document.querySelectorAll('button')].filter(b=>!(b.textContent.trim()||b.getAttribute('aria-label'))).length""")
    if noname: problems.append(f"{noname} buttons have no label for screen readers")
    noalt = p.evaluate("""[...document.querySelectorAll('img')].filter(i=>!i.hasAttribute('alt')).length""")
    if noalt: problems.append(f"{noalt} images missing alt text")
    unlabeled = p.evaluate("""[...document.querySelectorAll('input:not([type=checkbox]):not([type=file]),textarea,select')].filter(i=>!i.closest('label')&&!i.getAttribute('aria-label')).map(i=>i.id||i.placeholder)""")
    if unlabeled: problems.append(f"inputs without labels: {unlabeled}")
    deadhash = p.evaluate("""[...document.querySelectorAll('a[href]')].filter(a=>!a.getAttribute('href')||a.getAttribute('href')==='').length""")
    if deadhash: problems.append(f"{deadhash} links with empty href")

    # sign in, then tap everything on every screen
    p.click("[data-social]"); p.wait_for_timeout(200)
    views = p.evaluate("[...document.querySelectorAll('section.view')].map(s=>s.id.slice(2))")
    tapped = 0
    for v in views:
        if v == "signin":
            continue
        p.evaluate(f"show('{v}',false)"); p.wait_for_timeout(100)
        n = p.locator(f"#v-{v} button:visible").count()
        for i in range(n):
            p.evaluate(f"show('{v}',false)"); p.wait_for_timeout(30)
            if p.locator("#photoView").count() and p.locator("#photoView").is_visible():
                p.evaluate("document.getElementById('photoView').style.display='none'")
            btns = p.locator(f"#v-{v} button:visible")
            if i >= btns.count():
                break
            try:
                btns.nth(i).click(timeout=1500); tapped += 1
            except Exception as e:
                problems.append(f"[{v}] button #{i} could not be tapped: {str(e).splitlines()[0][:120]}")
            p.wait_for_timeout(40)
            if not p.evaluate("signedIn"):
                p.locator("#v-signin [data-social]").first.click(); p.wait_for_timeout(80)
        # small tap targets
        small = p.evaluate(f"""[...document.querySelectorAll('#v-{v} button')].filter(b=>b.offsetParent).map(b=>{{const r=b.getBoundingClientRect();return [b.textContent.trim().slice(0,20)||b.getAttribute('aria-label'),Math.round(r.width),Math.round(r.height)]}}).filter(([n,w,h])=>w<24||h<24)""")
        if small: info.append(f"[{v}] small tap targets: {small[:5]}")
    # header + tabs
    if not p.evaluate("signedIn"):
        p.locator("#v-signin [data-social]").first.click(); p.wait_for_timeout(80)
    for sel in ["header [data-go]", "nav.tabs button"]:
        for i in range(p.locator(sel).count()):
            p.locator(sel).nth(i).click(); tapped += 1; p.wait_for_timeout(60)
    # demo voting running long + stress
    p.evaluate("show('race2028',false)"); p.click("#partyFilter2028 [data-p28='all']"); p.click("#demoVotes"); p.wait_for_timeout(9000); p.click("#demoVotes")
    stats = p.evaluate("({votes:ACT.length, leaders:document.querySelectorAll('#leaders .lead').length, tiles:document.querySelectorAll('#stripRace .ctile').length})")
    info.append(f"after 9s of sample voting: {stats}")
    # memory/blob leak check is out of scope; check page still responsive
    p.click("nav.tabs [data-tab='feed']"); p.wait_for_timeout(100)
    if not p.evaluate("document.getElementById('v-feed').classList.contains('on')"):
        problems.append("app stopped responding after sweep")
    info.append(f"buttons tapped: {tapped}")
    b.close()

print("PROBLEMS:", json.dumps(problems, indent=1))
print("INFO:", json.dumps(info, indent=1))
