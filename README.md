# HealthUp — hybrid foundation
GitHub Pages hosts the static website and ten generated product concept visuals. Railway hosts only the FastAPI contact API. No checkout or released developer tools are represented as available.

## Local frontend
Run `python3 build.py`, then `python3 -m http.server 8000 --directory dist`. Open http://localhost:8000. Without an API URL the form explicitly saves local drafts.

## GitHub Pages
Push these files to `TastyThaiCorp/healthapp` on `main`. Make that repository public for free GitHub Pages. In Settings → Pages select **GitHub Actions**. The included workflow builds and publishes `dist/`, excluding the backend. Relative asset paths work under the repository URL and hash routes support direct links. GitHub Pages availability depends on repository visibility and account plan.

## Railway API
1. Connect the repository to the intended Railway project and name the service HealthUp API.
2. Set the service root directory to `/backend`. Railway will use `backend/Dockerfile` and `backend/railway.json`.
3. Attach a persistent volume mounted at `/data`. The API refuses Railway startup without an attached volume. Set `DATABASE_PATH=/data/inquiries.sqlite3` (also the Docker default).
4. Set `ALLOWED_ORIGINS=https://tastythaicorp.github.io` for this repository’s GitHub Pages deployment. An origin has no repository path. Add the exact custom frontend origin if one is later used. Multiple origins are comma-separated. Credentials/cookies are not used.
5. Generate a public Railway HTTPS domain. In the frontend's `config.js`, set `apiBaseUrl` to that real origin without `/api/integrate`. Push this change to rebuild GitHub Pages. Never use `https://railway.app` as your API address.
6. Verify `/health` and submit an inquiry from the published frontend.
7. For lower idle compute costs, enable Railway Serverless and redeploy. Use a single service instance and one Uvicorn worker. Set an account usage limit. Serverless availability and wake-up behavior are platform settings, not a FastAPI feature; cold starts can add latency. Storage continues to incur charges while compute sleeps.

## Local API
Create a Python virtual environment and install `backend/requirements.txt`. From `backend/`, run `ALLOWED_ORIGINS=http://localhost:8000 DATABASE_PATH=./data/inquiries.sqlite3 uvicorn main:app --port 8080`. Configure `apiBaseUrl` as `http://localhost:8080` for local testing only.

## Inquiry behavior
Online submissions use JSON at `/api/integrate`. Name, email, brief, and request UUID are validated. Success means the transaction committed to SQLite; it does not mean an email was delivered. A request UUID prevents duplicate saves after a timeout. Changed form contents create a new UUID. Fields are preserved on failures. There is a 60-second timeout for cold starts, no silent automatic retry, and no background polling.

SQLite is stored on the required volume. Never scale this setup to multiple instances. Server records are removed after 30 days on the next accepted submission; if there is no traffic, expired records remain until maintenance or another submission. SQLite files and backups contain personal information. Access is through the Railway volume/CLI; there is intentionally no public listing endpoint. For a review workflow, query the volume database from the authenticated Railway environment. To delete a record, use a parameterized SQL command in that environment. Browser deletion affects local drafts only.

The API logs no names, emails, or briefs. It limits payloads to 16 KiB, rejects a honeypot value, and permits five new inquiries per email per hour. CORS and these basic checks are not comprehensive abuse protection; monitor the public contact endpoint and add platform-level rate limits if necessary.

## Checks
`node --check script.js` and `python3 build.py` validate the frontend build. With the backend dependencies and `httpx==0.28.1` installed, run `python backend/test_api.py`. Browser checks cover navigation, filters, draft handling, success/failure delivery, duplicate-prevention IDs, and mobile layouts.

## Stack and assets
The requested browser files remain buildless HTML/CSS/JavaScript. `types/catalog.ts` supplies TypeScript contracts for future integrations. Python runs the contact service and static build. `assets/product-atlas.png` contains ten original generated conceptual photographs; each product displays a separate tile. Tools remain product concepts. No customer testimonials or performance statistics have been fabricated.
