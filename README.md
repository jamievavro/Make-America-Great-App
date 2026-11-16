# Make Republican Great Again

A free, ad-free news app for Republicans with a red, white and blue design. Every story links to its sources.

**Status:** working prototype. It runs in the browser with no build step. On this public site, your star ratings, comments and follows are saved on your own phone. When the app runs as a Claude artifact, ratings and comments are shared live between everyone who has access.

## What's in it

- **Sign-in first:** email, Google or Apple (demo), plus create an account
- **2028 (main tab):** President Trump, then the Republican 2028 field (declared, exploring, weighing it, said no), plus Democrats and other parties. Republicans get star ratings, a most-liked-first ranking, live votes and comments
- **Candidate profiles:** tap any name for background, where they stand, 2028 status and sources
- **Compare:** pick two candidates and see their positions on 8 issues side by side
- **Who Matches Me?:** an 8-question quiz that ranks candidates by how much they agree with you
- **2028 Polls:** Republican primary polls with dates and sources
- **Map:** 2026 midterm Senate and governor results by state, with a Republicans-only filter
- **Home and Brief:** sourced top stories, plus daily, weekly and monthly recaps
- **Feed and Videos:** repost, post photos and videos, like, comment, follow and report
- **Alerts:** the latest on every candidate you follow, with phone notifications
- **Election Calendar and How to Vote:** key dates and links to official .gov sites
- **Add to Home Screen:** installs like an app, and works offline once opened
- **Donate to the App Creator:** donations go to the app's developer, not to any campaign or party

## Run it

Open `index.html` in any browser, or visit the GitHub Pages site.

## Tests

```bash
pip install playwright && python -m playwright install chromium
python tests/test_app.py      # 214 functional checks
python tests/debug_sweep.py   # taps every button on every screen and looks for errors
```

Set `CHROME_PATH` to use an installed Chrome instead of Playwright's Chromium.
