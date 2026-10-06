# HealthUp

**Balance your life. Build yourself up.** A premium local-first wellness PWA with bamboo/dark walnut surfaces, sage/aqua accents and the selected Organic Ascent logo.

Public app: https://tastythaicorp.github.io/healthapp/

React + TypeScript + Vite frontend; Python + FastAPI account/content service. Public source, no embedded API keys. Core tools remain usable offline after the first online visit. Online registration, staff and payments are implemented/tested but require real production configuration before activation.

## The experience

Today brings together hydration, mood, meals, optional calories/weight, intentions and reflection. Food includes 100 complete illustrated recipes, ingredient swaps with recalculated generic nutrition estimates, favorites, prep mode, category/search/pantry filters and optional USDA lookup. Calendar offers month/week/day, drag dates, repeat, edit, complete, snooze, occurrence deletion, ICS export and timed routine launch. Journey has 100 open days. Mind offers text guides, timers, comfortable breathing, optional sound/haptics, 70 rotating affirmations and an optional botanical puzzle.

The Studio release adds exact-duration adaptive activities, a popup timer, non-repeating suggestions, gentle return-day widgets, a journal/dream/gratitude book, search/tags/favorites, encrypted device storage and passphrase backups. Local check-ins suggest source-linked guides without diagnosis or sending emotions to an AI provider. Daily popups, personalization and quiet mode are user-controlled. Support provides national/global resources and immediate-danger guidance; no entries are remotely monitored and no automatic emergency calls are made.

See [30 upgrades](UPGRADES.md), [deployment](DEPLOYMENT.md), [regulatory research and remaining legal work](COMPLIANCE.md), and [2024–2026 wellness research](RESEARCH.md).

## Privacy and accounts

Device records use AES-GCM and a non-extractable browser-held key. Anyone controlling the unlocked browser or compromised origin code can still access records: this is not end-to-end encryption or a medical record system. Plain JSON exports contain personal information; encrypted exports use a separate passphrase that HealthUp cannot recover. Account namespaces prevent ordinary UI mixing between users.

The optional account service uses verified email, Argon2id passwords, hashed single-use reset tokens, secure HttpOnly sessions, Origin/CSRF checks, rate limits, encrypted identity/consent fields, role checks and staff TOTP. Fresh logins require viewing the check-in with a private “Prefer not to say” option. Essential terms/age/wellness acknowledgements are distinct from optional cloud backup consent. Withdrawing cloud consent deletes the primary backup. Staff cannot browse private wellness entries.

No analytics/advertising SDKs or health-data sales. Fonts and artwork are local. Optional external searches send query terms to USDA/NCBI. No clinical claims, fabricated citations, guaranteed results, or blanket liability promises. HIPAA applicability, regional obligations and operational compliance require review; no compliance certification is asserted.

## Development

```
npm ci
npm run dev
npm test
npm run build
```

Vite base defaults to `/healthapp/`. `VITE_BASE_PATH=/` and `VITE_API_URL=same-origin` build the unified Railway app. The service worker caches shell, bundled content, fonts, 100 recipes and artwork; API/session responses are never cached. User logs survive refresh in encrypted IndexedDB. Browser eviction/deletion still affects records; keep exported backups.

Health endpoint returns exactly `{"status":"ok","product":"HealthUp"}`. API adapters `/api/recipes`, `/api/foods/search`, `/api/research`, `/api/content`, `/api/events` preserve public content fallbacks. Personal events are device-local. Account/billing routes and production gates are documented in DEPLOYMENT.md.

Production deployment needs Railway access, a persistent account volume, actual operator/contact details, transactional email and reviewed notices. Paid activation also needs Stripe test/live setup and verified webhooks. These external connections are not simulated in the public app.
