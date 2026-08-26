# Local development quickstart

These commands are for local development. Flask's built-in server is not the
production deployment server.

## Setup

From the repository root on PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```

Replace the placeholder `FLASK_SECRET_KEY` in `.env` with that generated value.
The file is local and ignored by Git. Keep the value persistent between starts;
changing it invalidates browser sessions but does not remove reviewer identity or
review history.

The default local database is `src/database/dmv_bus_stops.db`. Prefer setting an
absolute `DMV_BUS_STOPS_DB` path to a copy when testing migrations or rebuilds.

## Start and verify

```powershell
python -m src.api.app
```

Open `http://localhost:8000/`. Local HTTP normally uses
`SESSION_COOKIE_SECURE=0`. Do not expose this development server publicly.

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
python -m compileall -q src scripts/active tests
git diff --check
```

`REVIEWER_AUTH_DEV_MODE=1` captures magic links locally and must never be enabled
in production. Anonymous review works without SMTP. For a production deployment,
configure real SMTP and remove the development-mode setting.
