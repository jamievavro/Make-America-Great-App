# Make America Great

A free, ad-free news app with a red, white and blue design. Every story links to its sources.

**Status:** clickable prototype. Everything runs in the browser. Accounts, posts, votes and uploads are not saved yet and reset when the page is closed.

## What's in it

- **Sign-in first:** email, Google or Apple (demo), plus create an account
- **2028 (main tab):** the Republican 2028 field (declared, exploring, weighing it, said no), with star ratings, a most-liked-first ranking, live votes, candidate comments and sources
- **Home:** top stories with sources, and a strip for rating the 2028 field
- **Brief:** daily, weekly and monthly recaps
- **Feed:** repost what you read, post photos (up to 4) and videos, like, comment, follow and report
- **Videos:** community video uploads with anti-fake-news rules
- **More:** Promises Kept, Vote Tracker, Fact Check, Your State, Events, Poll + Comments, Find Friends, Profile and Donate
- **Donate to the App Creator:** donations go to the app's developer, not to any campaign or party

## Run it

Open `index.html` in any browser. No build step is needed.

## Tests

```bash
pip install playwright && python -m playwright install chromium
python tests/test_app.py      # 131 functional checks
python tests/debug_sweep.py   # taps every button on every screen and looks for errors
```

Set `CHROME_PATH` to use an installed Chrome instead of Playwright's Chromium.

## Next steps to go live

1. Live news feeds (RSS or news APIs) for real headlines and photos
2. Real login and a database (Firebase or Supabase) for accounts, posts, votes and comments
3. Photo and video storage (Firebase Storage or Cloudflare Stream)
4. Payments for donations (Stripe or PayPal)
5. Moderation tools for reported posts
6. Install as a PWA (manifest and service worker)
