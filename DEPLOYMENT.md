# Deploying the HealthUp Studio release

## Public frontend

GitHub Pages continues to serve the functioning local-first app. `npm ci && npm test && npm run build` builds `/healthapp/`. The Pages workflow publishes `dist`. Core wellness functions, encrypted device records, local journals, resources and legal-source summaries do not need a backend.

`HEALTHUP_API_URL` repository variable can point to the optional public API for nutrition/research. Accounts deliberately avoid cross-site cookies: when the account API points to another origin, Account offers the configured secure app URL instead of pretending Safari third-party cookies will work.

## Unified Railway app and API

Use the repository-root Dockerfile and railway.json. The image builds Vite with `VITE_BASE_PATH=/` and `VITE_API_URL=same-origin`, then serves the app and FastAPI together. Health check: `/api/health`. One Uvicorn worker, non-root UID/GID 10001, no access logs. Configure a persistent volume for the account DB and grant this UID write permission. Do not run multiple replicas against this SQLite account store; migrate transactions/rate limits/session storage to PostgreSQL/shared infrastructure first if scaling.

The public-content API can be run without accounts. The separate backend Dockerfile supports API-only serving. USDA production access requires `USDA_API_KEY`; NCBI contact/key are optional server variables.

## Account activation configuration

Required before `AUTH_ENABLED=true` becomes effective:

| Variable | Value / handling |
| --- | --- |
| `HEALTHUP_COMPANY_NAME` | Actual legal operator. |
| `HEALTHUP_PRIVACY_EMAIL` | Working privacy contact. |
| `APP_URL` | Canonical HTTPS unified-app origin/path, not a Pages frontend pointing to cross-site cookies. |
| `ACCOUNT_DB_PATH` | Persistent volume path, for example `/data/healthup.sqlite3`. |
| `ACCOUNT_ENCRYPTION_KEYS` | Secret comma-separated Fernet keys, newest first. Generate securely, keep out of GitHub and logs. Retain old keys until stored rows are re-encrypted. |
| `ACCOUNT_HASH_KEY` | Independent random secret of at least 32 bytes for identity/rate-limit HMACs. Do not rotate without a planned email-index migration. |
| `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | Real transactional mail credentials and verified sender; STARTTLS. `SMTP_PORT` defaults to 587. |
| `HEALTHUP_LEGAL_REVIEWED` | `true` only after the actual operator reviews notices, applicability and required operating processes. |
| `HEALTHUP_ALLOWED_COUNTRIES` | Defaults to `US`; expand only after jurisdiction review. Country is a self-attestation. |
| `ALLOWED_ORIGINS` | Exact approved origins; use the unified app origin for account operations. |

Do not set `HEALTHUP_ENV=test` in a real deployment. The test-only HTTP cookie mode is explicitly refused when Railway's environment marker is present. Accounts use Secure, HttpOnly, SameSite=Strict host cookies; same-origin TLS hosting is required. Registration accepts no client-controlled staff role or paid plan.

Use your secret manager to generate/store keys. No deployment credentials, production keys or customer data are included in this repository. Railway authorization is still needed to create/connect the actual service.

## Staff enrollment and operations

Create and verify an ordinary account first. On the server, supply a private Base32 authenticator seed through `STAFF_ENROLLMENT_SECRET`, then run `python -m backend.manage enroll-staff --email <verified staff email>`. The tool never prints the seed. Enroll it privately in the staff authenticator and remove the temporary environment variable. Staff access uses TOTP replay protection and a 30-minute authorization window. Offboard with `python -m backend.manage revoke-staff --email <staff email>`; sessions are revoked.

The dashboard shows aggregate account counts, request status and audit action names. It has no API for browsing user mood, weight, journal or dream entries. The privacy queue is an operating aid; staff must perform and communicate the actual rights resolution.

Run `python -m backend.manage cleanup` as a daily scheduled maintenance task. It purges expired sessions/tokens, hour-old rate records and 90-day closed operational records. Schedule/monitor this job and determine infrastructure backup retention before activation. Configure trusted proxy addresses carefully for rate limiting; do not trust arbitrary client-supplied forwarded headers. Independent security review and operational incident procedures remain required.

## Subscription activation

Free core includes all local wellness, local journals/dreams, emergency links and privacy access. Plus adds encrypted backup/upload and restore convenience. A pilot monthly price is a business decision; no charge amount is hardcoded as a live offer.

Set `STRIPE_SECRET_KEY`, `STRIPE_PRICE_ID` (active monthly recurring price), `STRIPE_WEBHOOK_SECRET` and `BILLING_TERMS_REVIEWED=true`. Configure the Stripe customer portal for cancellation, tax/refund policy and legally required receipt/renewal notices. Route signed events to `/api/billing/webhook` for checkout completion and subscription created/updated/deleted. The webhook retrieves canonical subscription status, validates the configured price and sets the server entitlement. A success redirect never unlocks Plus. Stripe Checkout handles cards; HealthUp never takes card input.

Start with Stripe test mode and verify purchase/cancel/failure/duplicate/out-of-order events before a live launch. Do not include health information in Stripe metadata. Privacy export/deletion/support are not paid features. Cancel an active subscription before account deletion to avoid leaving recurring billing orphaned.

## Verification

```
npm test
npm run build
python3 tests/browser.py
python3 tests/upgrades.py
python3 tests/accessibility.py
python3 tests/branding.py
python3 backend/test_api.py
python3 backend/test_accounts.py
```

Python browser checks use Playwright and system Chromium; install test dependencies in a separate environment. To test real account UI with ephemeral fixtures:

```
VITE_BASE_PATH=/ VITE_API_URL=same-origin npm run build -- --outDir /tmp/healthup-account-dist
python3 tests/account_browser.py
```

The account test uses a temporary database and mocked transactional email/payment boundaries, not production accounts or charges. The image can be tested without activating accounts using `/api/health` and `/api/auth/config`. Never describe these tests as a HIPAA audit, a worldwide legal approval or a penetration-test certificate.
