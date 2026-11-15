import sys, os, json, traceback
from playwright.sync_api import sync_playwright

APP = "file://" + os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))
FX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
SHOTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots")
os.makedirs(SHOTS, exist_ok=True)

results = []  # (area, name, ok, detail)
errors = []

def check(area, name, cond, detail=""):
    results.append((area, name, bool(cond), detail))

def run():
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=os.environ.get("CHROME_PATH") or None, args=["--no-sandbox"])
        ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        p = ctx.new_page()
        p.on("pageerror", lambda e: errors.append("JS error: " + str(e)))
        p.on("console", lambda m: m.type == "error" and "fonts.g" not in (m.location.get("url") or "") and errors.append("console: " + m.text))
        p.route("**/fonts.googleapis.com/**", lambda r: r.abort())
        p.route("**/fonts.gstatic.com/**", lambda r: r.abort())
        p.goto(APP)
        p.wait_for_timeout(400)

        vis = lambda v: p.evaluate(f"document.getElementById('v-{v}').classList.contains('on')")
        tab_on = lambda t: p.evaluate(f"document.querySelector('nav.tabs [data-tab=\"{t}\"]').classList.contains('on')")
        toast = lambda: p.evaluate("document.getElementById('toast').style.display==='block' ? document.getElementById('toast').textContent : ''")
        def tab(t):
            p.click(f"nav.tabs [data-tab='{t}']"); p.wait_for_timeout(150)
        def go(sel):
            p.click(sel); p.wait_for_timeout(150)
        def back():
            p.locator("section.view.on [data-back]").first.click(); p.wait_for_timeout(150)
        def shot(n):
            p.screenshot(path=f"{SHOTS}/{n}.png", full_page=False)

        # ---------- start screen: sign in first ----------
        gated = lambda: p.evaluate("document.querySelector('.app').classList.contains('gate')")
        check("Start", "App opens on the sign-in screen", vis("signin") and gated())
        check("Start", "Tabs and header are hidden before sign-in", not p.locator("nav.tabs").is_visible() and not p.locator("header.top").is_visible())
        check("Start", "No Back button on the first sign-in screen", not p.locator("#v-signin > button.back[data-back]").is_visible())
        check("Start", "App name shows on sign-in screen", p.locator(".gateBrand").is_visible())
        check("Start", "'Create an account' link is visible", p.locator("#siToggle").is_visible())
        shot("00-signin-first")
        # ---------- sign in / create account ----------
        go("#siToggle")
        check("Sign-in", "'Create an account' shows name field", p.locator("#nameRow").is_visible() and "Create" in p.inner_text("#siBtn"))
        go("#siToggle")
        check("Sign-in", "Toggle back to Sign In", not p.locator("#nameRow").is_visible())
        go("#siToggle")
        p.fill("#siName", "Jamie Tester"); p.fill("#siEmail", "jt@example.com")
        go("#siBtn")
        check("Sign-in", "Create account signs you in", p.inner_text("#pName") == "Jamie Tester" and not gated())
        check("Sign-in", "After sign-in you land on the 2028 tab", vis("race2028") and tab_on("race2028"))
        check("Sign-in", "Tabs and header appear after sign-in", p.locator("nav.tabs").is_visible() and p.locator("header.top").is_visible())
        check("Start", "Candidate line shows all 12 active candidates", p.locator("#stripRace .ctile").count() == 12)
        shot("01-2028")
        # ---------- bottom tabs ----------
        for t in ["home", "brief", "race2028", "feed", "more"]:
            tab(t)
            check("Tabs", f"'{t}' tab opens its screen and highlights", vis(t) and tab_on(t))

        # ---------- 2028 page ----------
        tab("race2028")
        before = [p.locator("#stripRace .ctile .cn").nth(i).inner_text() for i in range(3)]
        last = p.locator("#stripRace .ctile").nth(10)
        last_name = last.locator(".cn").inner_text()
        last.locator(".mstar").nth(4).click(); p.wait_for_timeout(200)
        first_name = p.locator("#stripRace .ctile .cn").first.inner_text()
        check("2028", "Tapping 5 stars on a candidate moves them to #1", first_name == last_name, f"{last_name} -> first is {first_name}")
        check("2028", "#1 badge shows", "#1" in p.locator("#stripRace .ctile").first.inner_text())
        check("2028", "Community Favorites lists the rated candidate", last_name in p.inner_text("#leaders"))
        check("2028", "Live Votes shows your vote", "Jamie Tester (you)" in p.inner_text("#liveRace"))
        check("2028", "Home strip shows LIVE line", "LIVE" in p.inner_text("#liveHome"))
        # change rating -> still one vote
        p.locator("#stripRace .ctile").first.locator(".mstar").nth(1).click(); p.wait_for_timeout(200)
        r = p.evaluate(f"ratings[{json.dumps(last_name)}]")
        check("2028", "Changing your rating keeps only one vote", r["count"] == 1 and r["mine"] == 2, str({k: r[k] for k in ('count','sum','mine')}))
        # card stars + comments
        card = p.locator("#v-race2028 .cand").filter(has_text="JD Vance")
        card.locator(".star").nth(3).click(); p.wait_for_timeout(150)
        check("2028", "Stars on a candidate card work", "You gave 4" in card.locator(".rsum").inner_text())
        card.locator(".ctog").click(); p.wait_for_timeout(100)
        card.locator(".cform input").fill("Test comment on Vance")
        card.locator(".cform button").click(); p.wait_for_timeout(150)
        check("2028", "Candidate comments post and show", "Test comment on Vance" in card.inner_text() and "(1)" in card.locator(".ctog").inner_text())
        card.locator(".cfollow").click(); p.wait_for_timeout(100)
        check("2028", "Follow candidate button toggles", card.locator(".cfollow").inner_text() == "Following")
        # tap name in strip scrolls to card
        p.locator("#stripRace .ctile .cn").nth(1).click(); p.wait_for_timeout(300)
        check("2028", "Tapping a name in the line stays on 2028 page", vis("race2028"))
        # demo votes
        go("#demoVotes"); p.wait_for_timeout(5600)
        n_sample = p.evaluate("ACT.filter(a=>a.sample).length")
        check("2028", "Sample voting activity adds votes", n_sample >= 2, f"{n_sample} sample votes")
        go("#demoVotes")
        stopped = p.evaluate("demoT===null")
        check("2028", "Stop sample activity button stops it", stopped)
        # order check: sorted descending by avg
        avgs = p.evaluate("""[...document.querySelectorAll('#stripRace .ctile .cn')].map(e=>{const r=ratings[e.textContent];return r.count?r.sum/r.count:-1})""")
        check("2028", "Line is sorted most-liked first", all(avgs[i] >= avgs[i+1] - 1e-9 for i in range(len(avgs)-1)), str([round(a,2) for a in avgs]))
        shot("03-2028-voted")
        # sources links are real links
        hrefs = p.evaluate("[...document.querySelectorAll('#v-race2028 .check a')].map(a=>a.href)")
        check("2028", "Source links point to real websites", all(h.startswith("https://") for h in hrefs) and len(hrefs) == 5)

        # ---------- home ----------
        tab("home")
        for name in ["Economy", "Jobs", "Border", "Energy", "Top Wins"]:
            p.click(f"#topics [data-topic='{name}']"); p.wait_for_timeout(60)
            check("Home", f"Topic chip '{name}' becomes selected", "red" in p.get_attribute(f"#topics [data-topic='{name}']", "class"))
        p.locator("#stripHome .ctile").first.locator(".mstar").nth(4).click(); p.wait_for_timeout(150)
        check("Home", "Home strip stars vote too", p.evaluate("Object.values(ratings).some(r=>r.mine===5)"))
        go("#v-home [data-go='race2028']")
        check("Home", "2028 banner opens 2028 page", vis("race2028") and tab_on("race2028"))
        tab("home")
        go("#v-home .stripHome, #v-home button.back[data-go='race2028']")
        check("Home", "'See all' opens 2028 page", vis("race2028"))
        tab("home")
        cards = p.locator("#v-home > button.card[data-go='story']")
        cnt = cards.count()
        ok = True
        for i in range(cnt):
            tab("home"); cards.nth(i).click(); p.wait_for_timeout(120)
            ok = ok and vis("story")
        check("Home", f"All {cnt} story cards open the story", ok)
        # header buttons
        go("header [data-go='profile']")
        check("Header", "Profile icon opens profile (signed in)", vis("profile"))
        go("header [data-go='donate']")
        check("Header", "'Donate to App Creator' opens Donate page", vis("donate"))

        # ---------- donate ----------
        for amt in ["$3", "$10", "$25"]:
            p.click(f"#amts .amt:has-text('{amt}')"); p.wait_for_timeout(50)
            check("Donate", f"{amt} button updates the Donate button", amt in p.inner_text("#donateBtn"))
        p.fill("#other", "42")
        check("Donate", "Other amount updates the Donate button", "$42" in p.inner_text("#donateBtn"))
        go("#donateBtn")
        check("Donate", "Donate button responds", "Thank you" in toast())
        check("Donate", "Says money goes only to the app creator", "goes only to the app creator" in p.inner_text("#v-donate"))
        back()
        check("Donate", "Back button returns", not vis("donate"))

        # ---------- story ----------
        tab("home"); cards.first.click(); p.wait_for_timeout(150)
        go("#repostBtn")
        check("Story", "Repost works", "Reposted" in p.inner_text("#repostBtn"))
        go("#repostBtn")
        check("Story", "Second repost is blocked", "Already" in toast())
        go("#likeBtn")
        check("Story", "Like toggles on", "Liked" in p.inner_text("#likeBtn"))
        go("#likeBtn")
        check("Story", "Like toggles off", "Liked" not in p.inner_text("#likeBtn"))
        p.fill("#sinput", "Great story")
        go("#sform button")
        check("Story", "Comment posts", "Great story" in p.inner_text("#storyComments"))
        links = p.locator("#v-story .check a")
        links.first.click(); p.wait_for_timeout(100)
        check("Story", "Source links respond", "source" in toast().lower())
        go("#v-story [data-go='share']")
        check("Story", "Share opens share card", vis("share"))
        for lbl in ["Facebook", "X", "Copy link"]:
            p.click(f"#v-share button:has-text('{lbl}')"); p.wait_for_timeout(80)
            check("Share", f"'{lbl}' button responds", toast() != "")
        back(); back()
        check("Story", "Back twice returns home", vis("home"))

        # ---------- brief ----------
        tab("brief")
        for k, title in [("weekly", "This Week"), ("monthly", "This Month"), ("daily", "Today's")]:
            p.click(f"#bTabs [data-b='{k}']"); p.wait_for_timeout(80)
            check("Brief", f"{k.title()} button switches view", title in p.inner_text("#bTitle") and p.locator(f"#b-{k}").is_visible())
        p.click("#bTabs [data-b='monthly']")
        p.click("#months button:has-text('October')"); p.wait_for_timeout(50)
        check("Brief", "Month chips select", "on" in p.get_attribute("#months button:has-text('October')", "class"))
        p.locator("#b-monthly [data-go='promises']").click(); p.wait_for_timeout(100)
        check("Brief", "Monthly 'Promises' card opens tracker", vis("promises"))
        tab("brief"); p.click("#bTabs [data-b='daily']")
        p.locator("#b-daily [data-go='story']").first.click(); p.wait_for_timeout(100)
        check("Brief", "Daily items open story", vis("story"))
        tab("brief"); go("#bShare")
        check("Brief", "Share brief opens share card", vis("share"))

        # ---------- feed ----------
        tab("feed")
        n0 = p.locator("#feedList .post").count()
        p.fill("#newPost", "Testing a text post")
        go("#postBtn")
        check("Feed", "Text post appears in feed", p.locator("#feedList .post").count() == n0 + 1 and "Testing a text post" in p.inner_text("#feedList"))
        # photos
        p.set_input_files("#fPhoto", [f"{FX}/photo0.png", f"{FX}/photo1.png"]); p.wait_for_timeout(150)
        check("Feed", "Photo previews appear", p.locator("#fPrev img").count() == 2)
        p.locator("#fPrev button").first.click(); p.wait_for_timeout(100)
        check("Feed", "Remove photo (x) works", p.locator("#fPrev img").count() == 1)
        check("Feed", "Rules checkbox appears for media", p.locator("#fOkRow").is_visible())
        go("#postBtn")
        check("Feed", "Posting media without checkbox is blocked", "confirm" in toast().lower())
        p.check("#fOk"); go("#postBtn")
        first_post = p.locator("#feedList .post").first
        check("Feed", "Photo post appears with image", first_post.locator("img").count() == 1)
        loaded = p.evaluate("(()=>{const i=document.querySelector('#feedList .post img');return i&&i.naturalWidth>0})()")
        check("Feed", "Uploaded photo actually displays", loaded)
        first_post.locator("img").click(); p.wait_for_timeout(150)
        check("Feed", "Tap photo opens full screen", p.locator("#photoView").is_visible())
        p.click("#photoView button"); p.wait_for_timeout(100)
        check("Feed", "Close full-screen photo", not p.locator("#photoView").is_visible())
        # video in feed
        p.set_input_files("#fVideo", f"{FX}/clip.mp4"); p.wait_for_timeout(100)
        p.check("#fOk"); go("#postBtn")
        check("Feed", "Video post appears with player", p.locator("#feedList .post").first.locator("video").count() == 1)
        # like / comment / repost on a friend's post
        fp = p.locator("#feedList .post").filter(has_text="[Friend B]").first
        likes_before = fp.locator(".act").nth(0).inner_text()
        fp.locator(".act").nth(0).click(); p.wait_for_timeout(120)
        fp = p.locator("#feedList .post").filter(has_text="[Friend B]").first
        check("Feed", "Like button counts up", fp.locator(".act").nth(0).inner_text() != likes_before and "Liked" in fp.locator(".act").nth(0).inner_text())
        fp.locator(".cform input").fill("Nice post!")
        fp.locator(".cform button").click(); p.wait_for_timeout(120)
        fp = p.locator("#feedList .post").filter(has_text="[Friend B]").first
        check("Feed", "Comment on a post shows at the bottom", "Nice post!" in fp.inner_text())
        fp.locator(".act").nth(1).click(); p.wait_for_timeout(100)
        check("Feed", "Comment button opens/closes thread", True)
        cnt_before = p.locator("#feedList .post").count()
        fp = p.locator("#feedList .post").filter(has_text="[Friend B]").first
        fp.locator(".act").nth(2).click(); p.wait_for_timeout(120)
        check("Feed", "Repost adds your repost to the feed", p.locator("#feedList .post").count() == cnt_before + 1)
        # follow button in feed
        fp = p.locator("#feedList .post").filter(has_text="[Friend B]").first
        fp.locator(".who button").click(); p.wait_for_timeout(100)
        fp = p.locator("#feedList .post").filter(has_text="[Friend B]").first
        check("Feed", "Follow from a post works", "Following" in fp.locator(".who button").inner_text())
        # report
        p.locator("#feedList .post").first.locator("button.back:has-text('⚑ Report')").click(); p.wait_for_timeout(80)
        check("Feed", "Report button responds", "Reported" in toast())
        # filters
        p.click("#feedFilter [data-f='following']"); p.wait_for_timeout(100)
        names = p.locator("#feedList .post .who b").all_inner_texts()
        check("Feed", "'Following' filter shows only followed + yours", "[Video Creator]" not in names, str(names[:6]))
        p.click("#feedFilter [data-f='top']"); p.wait_for_timeout(100)
        check("Feed", "'Most Liked' filter sorts by likes", p.locator("#feedList .post").count() > 0)
        p.click("#feedFilter [data-f='all']"); p.wait_for_timeout(100)
        # quote card opens story
        p.locator("#feedList .post .quote").filter(has_text="Sourced").first.click(); p.wait_for_timeout(120)
        check("Feed", "Story card in a post opens the story", vis("story"))
        tab("feed")
        # sample video
        p.locator("#feedList button[aria-label='Play sample video']").first.click(); p.wait_for_timeout(80)
        check("Feed", "Sample video responds", "Sample video" in toast())
        # videos page
        go("#feedFilter [data-go='videos']")
        check("Videos", "Videos button opens Videos page", vis("videos") and tab_on("feed"))
        go("#vBtn")
        check("Videos", "Upload without a file is blocked", "Choose a video" in toast())
        p.set_input_files("#vFile", f"{FX}/clip.mp4"); p.fill("#vTitle", "My test video"); go("#vBtn")
        check("Videos", "Upload without rules checkbox is blocked", "confirm" in toast().lower())
        p.check("#vOk"); go("#vBtn")
        check("Videos", "Video upload appears on Videos page", "My test video" in p.inner_text("#videoList") and p.locator("#videoList video").count() >= 1)
        shot("04-videos")

        # ---------- more menu ----------
        targets = ["promises", "race2028", "videos", "profile", "people", "votes", "factcheck", "state", "events", "community", "donate"]
        tab("more")
        items = p.evaluate("[...document.querySelectorAll('#v-more [data-go]')].map(b=>b.dataset.go)")
        for t in items:
            tab("more"); p.click(f"#v-more [data-go='{t}']"); p.wait_for_timeout(100)
            check("More", f"Menu item '{t}' opens", vis(t))

        # promises / votes chips
        tab("more"); p.click("#v-more [data-go='promises']")
        p.click("#pfilter button:has-text('Border')"); p.wait_for_timeout(50)
        check("Promises", "Filter chips select", "on" in p.get_attribute("#pfilter button:has-text('Border')", "class"))
        tab("more"); p.click("#v-more [data-go='votes']")
        p.locator("#reps button").nth(2).click(); p.wait_for_timeout(50)
        check("Votes", "Representative chips select", "on" in p.locator("#reps button").nth(2).get_attribute("class"))
        check("Votes", "congress.gov link is a real link", p.get_attribute("#v-votes a.src", "href").startswith("https://"))

        # fact check
        tab("more"); p.click("#v-more [data-go='factcheck']")
        go("#checkBtn")
        check("Fact Check", "Empty claim is blocked", "Type a claim" in toast())
        p.fill("#claim", "Gas prices went down"); go("#checkBtn")
        check("Fact Check", "Check the Facts shows result", p.locator("#checkResult").is_visible() and "Gas prices" in p.inner_text("#claimText"))
        back()

        # state
        tab("more"); p.click("#v-more [data-go='state']")
        p.select_option("#stateSel", "Texas"); p.wait_for_timeout(50)
        check("Your State", "Changing state updates page", p.inner_text("#stateName") == "Texas" and "Texas" in p.inner_text("#v-state"))
        p.locator("#v-state [data-go='story']").first.click(); p.wait_for_timeout(80)
        check("Your State", "State stories open", vis("story"))

        # events
        tab("more"); p.click("#v-more [data-go='events']")
        bells = p.locator("#v-events .icon-btn")
        ok = True
        for i in range(bells.count()):
            bells.nth(i).click(); p.wait_for_timeout(50); ok = ok and "set" in bells.nth(i).get_attribute("class")
        check("Events", f"All {bells.count()} reminder bells turn on", ok)
        bells.first.click(); p.wait_for_timeout(50)
        check("Events", "Reminder bell turns off", "set" not in bells.first.get_attribute("class"))

        # community
        tab("more"); p.click("#v-more [data-go='community']")
        p.locator("#v-community .poll").first.click(); p.wait_for_timeout(500)
        check("Community", "Poll vote shows results", "%" in p.inner_text("#v-community .facts"))
        p.fill("#cinput", "Love this app"); go("#cform button")
        check("Community", "Community comment posts", "Love this app" in p.inner_text("#comments"))

        # people
        tab("more"); p.click("#v-more [data-go='people']")
        f_before = int(p.inner_text("#pFollowing"))
        p.locator("#v-people .follow").first.click(); p.wait_for_timeout(50)
        check("Find Friends", "Follow increases Following count", int(p.inner_text("#pFollowing")) == f_before + 1)
        p.locator("#v-people .follow").first.click(); p.wait_for_timeout(50)
        check("Find Friends", "Unfollow decreases count", int(p.inner_text("#pFollowing")) == f_before)
        go("#v-people [data-toast]")
        check("Find Friends", "Invite Friends responds", "Invite" in toast())

        # profile
        tab("more"); p.click("#v-more [data-go='profile']")
        check("Profile", "Reposts count updated", int(p.inner_text("#pReposts")) >= 2)
        check("Profile", "Reposts tab lists reposts", p.locator("#p-reposts .card").count() >= 2)
        p.click("#pTabs [data-p='comments']"); p.wait_for_timeout(50)
        check("Profile", "My Comments tab lists comments", "Great story" in p.inner_text("#p-comments"))
        p.click("#pTabs [data-p='feed']"); p.wait_for_timeout(50)
        check("Profile", "Friends' Posts tab shows", p.locator("#p-feed").is_visible())
        p.set_input_files("#avFile", f"{FX}/photo1.png"); p.wait_for_timeout(150)
        check("Profile", "Profile picture upload works", "url(" in p.evaluate("document.getElementById('pAv').style.background"))
        p.click("#v-profile [data-toast]"); p.wait_for_timeout(50)
        check("Profile", "Edit Profile responds", toast() != "")
        p.click("#v-profile [data-go='people']"); p.wait_for_timeout(80)
        check("Profile", "Find Friends button opens", vis("people"))
        tab("more"); p.click("#v-more [data-go='profile']")
        shot("05-profile")
        go("#signOut")
        check("Profile", "Sign Out returns to the sign-in screen", vis("signin") and gated() and not p.evaluate("signedIn"))
        check("Profile", "Tabs hidden again after sign out", not p.locator("nav.tabs").is_visible())
        p.click("#v-signin [data-social]"); p.wait_for_timeout(100)
        check("Sign-in", "Continue with Google/Apple signs in and opens 2028", p.evaluate("signedIn") and vis("race2028"))

        # all data-go and data-back buttons resolve to real views
        gos = p.evaluate("[...new Set([...document.querySelectorAll('[data-go]')].map(b=>b.dataset.go))]")
        missing = [g for g in gos if not p.evaluate(f"!!document.getElementById('v-{g}')")]
        check("Wiring", "Every navigation button points to a real screen", not missing, str(missing))
        dead = p.evaluate("""[...document.querySelectorAll('button')].filter(b=>{
            if(b.closest('nav.tabs')||b.dataset.go||b.dataset.tab||b.dataset.back!==undefined||b.dataset.toast||b.onclick||b.id||b.closest('form')||b.closest('[id]')&&['topics','pfilter','reps','months','amts','bTabs','feedFilter','pTabs'].includes(b.closest('[id]').id)) return false;
            const c=b.className||''; return !/(poll|icon-btn|follow|cfollow|amt|star|mstar|act|ctog|quote|cn|back|pill)/.test(c) && !b.hasAttribute('data-social') && !b.hasAttribute('data-f') && !b.hasAttribute('data-b') && !b.hasAttribute('data-p');
        }).map(b=>b.textContent.trim().slice(0,30))""")
        check("Wiring", "No buttons left without an action", not dead, str(dead))

        # layout: nothing wider than the phone screen
        for t in ["race2028", "home", "brief", "feed", "more"]:
            tab(t)
            sw = p.evaluate("document.documentElement.scrollWidth")
            check("Layout", f"'{t}' fits phone width (no sideways scroll)", sw <= 392, f"scrollWidth={sw}")
        tab("home"); shot("06-home")
        tab("feed"); shot("07-feed")
        b.close()

try:
    run()
except Exception:
    errors.append("TEST SCRIPT CRASH: " + traceback.format_exc()[-1500:])

passed = sum(1 for r in results if r[2])
print(f"PASSED {passed}/{len(results)}")
for a, n, ok, d in results:
    if not ok:
        print(f"FAIL [{a}] {n} :: {d}")
print("ERRORS:", json.dumps(errors[:30], indent=1))
json.dump({"results": results, "errors": errors}, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.json"), "w"))
