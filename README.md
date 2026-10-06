# HealthUp
**Balance your life. Build yourself up.**

A React + TypeScript wellness PWA with the original bamboo, dark walnut, ivory, black, and elegant italic theme. The supplied heart/up-arrow logo is reused unchanged; square install icons are raster derivatives of a padded source wrapper.

## What works without an account or backend
- Personal dashboard and customizable, non-medical Balance Score.
- Water, meals, mood, optional weight, movement, rest, intention, and reflection logging.
- 100 complete, distinct recipes with illustrations, search, tags, favorites, serving scaling, prep checklists, and equal-weight ingredient swaps that recalculate generic estimates.
- 100 open journey tiles, guided/My Pace/Surprise modes, and persistent completion.
- Month/week/day calendar, mobile agenda, one-off/daily/weekly events, editing, drag-to-date, completion, per-occurrence deletion, snooze, and ICS export.
- Text-guided meditation timers, elapsed-clock accuracy across refresh, comfortable visual breathing, optional synthetic soundscape and vibration, 70 affirmations, favorites, and scheduling.
- Optional matching puzzle and original preference-based pause quiz.
- Weight history and rolling average of up to seven weigh-ins, mood counts, weekly snapshots, and descriptive overlapping habit observations.
- Eight source-linked guides and curated research notes from 2024, 2025, and 2026.
- IndexedDB storage, data export/import/deletion, optional weight/play visibility, reminder controls, crisis resources by region, and medical disclosures.

## Local development
`npm ci` then `npm run dev`. Vite's default base is `/healthapp/`. Open the URL with that path. `npm run build` produces `dist`. `npm test` runs the unit/content checks. `python3 tests/browser.py` runs E2E tests with Python Playwright and Chromium at `/usr/bin/chromium`; build first. Browser screenshots are internal QA artifacts.

## GitHub Pages
Repository: https://github.com/TastyThaiCorp/healthapp . The workflow runs unit tests and builds/publishes `dist` after pushes to `main`. Pages must use GitHub Actions. Public repo hosting is enabled. The deployed frontend is https://tastythaicorp.github.io/healthapp/ . Hash routes do not require rewrites.

Set the repository Actions variable `HEALTHUP_API_URL` to the generated Railway API HTTPS origin to enable live USDA/PubMed enhancements. It is a public URL, not a secret. Without it, cached results and bundled content keep the app useful. Keys never enter client JavaScript.

## Railway
Two supported deployment options:
1. **Hybrid, lowest frontend hosting overhead:** service root `/backend`. The backend Dockerfile serves only public content/adapters. GitHub Pages serves the frontend.
2. **Unified Railway PWA:** service root `/`. The root Dockerfile builds the frontend with base `/` and same-origin API connections, then starts FastAPI/Uvicorn. This hosts the entire app on Railway.

Health check: `/api/health`, returning `{"status":"ok","product":"HealthUp"}`. Both railway.json files use this endpoint. One Uvicorn worker conservatively paces NCBI requests; cached results expire after an hour and query cache is bounded.

Server variables:
- `ALLOWED_ORIGINS=https://tastythaicorp.github.io` (comma-separated explicit additional origins)
- `USDA_API_KEY` from data.gov for production nutrient lookup. Local development can use the documented DEMO_KEY, which has stricter limits.
- `NCBI_EMAIL` recommended for the Entrez tool registration/contact; `NCBI_API_KEY` optional.
- `PORT` provided by Railway.

No database or persistent volume is required for the core release: personal health data stays browser-local. `backend/schema.sql` is a future PostgreSQL sync foundation, not an implemented cloud account or sync feature. `/api/events` returns public event types; it does not store personal events. `/api/recipes`, `/api/foods/search`, `/api/research`, `/api/content`, and `/api/health` are implemented.

Railway Serverless is a platform setting, not a FastAPI feature. Enable and redeploy if desired; cold starts can add latency. No polling or keep-alive traffic is sent by the frontend to prevent sleep. Budget/costs depend on platform plans and usage.

## Offline, privacy, and limits
The service worker pre-caches the shell, generated bundle, 100 recipes, local content, original logo, icons, and nature art. Open the app online once before using it offline. Local logs survive refresh and offline use in IndexedDB. Browser storage can be cleared or evicted; export backups. Local data is not an encrypted medical record system.

Browser-native notifications require permission and a supported device. Reminders reliably run only while the app is open; closed-app scheduling is not promised. The app offers in-app reminders if native notifications are unavailable. App installation depends on browser support. Optional external fonts may fall back offline.

No clinical assessments, treatment claims, AI therapy, fabricated testimonials, guaranteed weight loss, or remote emergency monitoring. The mood quiz is a personal reflection; the pause quiz is preference-based. Research design choices and limitations are documented in RESEARCH.md. Research is not evidence that HealthUp itself is clinically effective.

## Verification
`npm test`, `npm run build`, and `python backend/test_api.py` (with backend requirements installed) cover content, calculations, reminders/recurrence, health routes, metadata mapping, and failure handling. Browser E2E covers actual logging, recipe search/swaps/favorites/prep, journey, calendar CRUD, timers, notifications, local persistence, puzzles/quizzes, keyboard dialogs, mobile layouts, reduced motion, and offline startup.
