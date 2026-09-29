# PocketSmart AI — runnable VS Code project

Three budget planners with account registration, session login, saved plans, an optional outfit image and optional Gemini commentary. This follows the **FastAPI** implementation and endpoint list in the later milestones of the supplied PDF; the earlier Flask and IBM Watsonx mentions conflict with those milestones.

## Start in VS Code (Windows PowerShell)

1. Extract `pocketsmart.zip` and open the **pocketsmart** folder in VS Code (`File > Open Folder`). Install the Microsoft Python extension and Python 3.11+.
2. In the VS Code terminal:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   Copy-Item .env.example .env
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

3. Paste the generated value as `SECRET_KEY` in `.env`. Keep `.env` private.
4. Start the app:

   ```powershell
   python -m uvicorn app.main:app --reload
   ```

5. Open http://127.0.0.1:8000 . Register with your name and try each planner. You will see **Welcome, [your name]!** after sign-in. Existing accounts can enter and save a name on the dashboard. Interactive API docs: http://127.0.0.1:8000/docs . For the VS Code debugger, select the `.venv` interpreter and launch **PocketSmart FastAPI**.

macOS/Linux: use `python3 -m venv .venv`, `source .venv/bin/activate`, `cp .env.example .env`, then the same pip/uvicorn commands.

## Gemini and platform data

Set `GEMINI_API_KEY` in `.env` to enable AI commentary and image analysis. `GEMINI_MODEL` defaults to `gemini-2.5-flash` and can be changed to a model available to your key. Without a key, all three planners remain usable with deterministic estimates. Image bytes are sent to Google only if a key is set, and are not saved in the database. Failed AI requests fall back to the deterministic plan.

The PDF names Amazon, IKEA, Flipkart, Swiggy, Zomato and OYO but supplies no merchant credentials, contracts or catalog endpoints. This project uses an **illustrative catalog**, sample INR prices and outgoing platform **search** links. It does not fetch, scrape or verify live products, availability or vendor prices. The AI never controls the arithmetic or the links. To integrate a licensed product API, replace `app/planner.py` catalog lookups, check its returned prices and preserve the `total <= budget` invariant.

## Endpoints

- `POST /register`, `/login`, `/token`, `/logout`; `GET /session-info`, `/session-data`; `PATCH /profile` to save a name
- `POST /generate-home` and `/generate-party` accept JSON; `POST /generate-jewelry` accepts multipart form data with optional `image` (JPEG, PNG or WebP, up to 3 MB).
- `GET /history`, `GET /recommendations-details/{plan_id}`, `GET /health`

Session cookies are HTTP-only, SameSite=Lax. `/token` provides a Bearer JWT for API clients. Passwords use salted scrypt hashes. SQLite data goes to `DATABASE_PATH` (default `./pocketsmart.sqlite3`). For a deployed service, use HTTPS, set `COOKIE_SECURE=true`, add rate limiting and use a persistent database with backups. Run locally on `127.0.0.1`; no cross-origin access is configured.

## Verify

```powershell
python -m pytest -q
```

The tests cover registration/login, three planners, budget caps, saved history and image validation. Live Gemini calls require your API key and are intentionally outside the automated tests.

## Files

- `app/main.py`: routes and request handling
- `app/models.py`: validated request/response types
- `app/planner.py`: catalog and budget allocation
- `app/gemini.py`: optional image and text AI integration
- `app/auth.py`, `app/db.py`: authentication and SQLite persistence
- `static/`: responsive web interface
