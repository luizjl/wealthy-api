# Wealthy API

REST API for Wealthy, built with FastAPI, SQLAlchemy, Oracle Database and Firebase Authentication.

## Local development

Requirements: Python 3.12 or newer, below 3.15.

```powershell
py -3.14 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
Copy-Item .env.example .env
.venv\Scripts\python -m alembic upgrade head
.venv\Scripts\python -m uvicorn wealthy_api.main:app --reload
```

The local default database is SQLite. Set `WEALTHY_DATABASE_URL` to a SQLAlchemy Oracle URL when an Oracle environment is ready. Oracle wallet and deployment configuration will be completed with the OCI deployment setup.

Set `WEALTHY_FIREBASE_PROJECT_ID` and `WEALTHY_FIREBASE_ALLOWED_UIDS` in `.env`. The allowlist accepts comma-separated Firebase UIDs; an empty allowlist denies access. For local token verification, configure Google Application Default Credentials outside the repository, for example with `GOOGLE_APPLICATION_CREDENTIALS` pointing to a service-account file. Never commit credentials.

The liveness endpoint is available at `/health`; interactive API documentation is at `/docs`. Business endpoints require a valid Firebase ID token and an allowed UID.

## Tests

```powershell
.venv\Scripts\python -m pytest
```