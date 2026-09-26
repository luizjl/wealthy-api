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

The local default database is SQLite. Oracle Autonomous Database uses python-oracledb Thin mode with the extracted wallet directory. The ignored local `.env.oracle` is ready with the TNS alias prefilled. Set the database username/password and wallet directory there. Keep the wallet and both passwords outside Git.

After filling the required Oracle values, set `WEALTHY_DATABASE_BACKEND=oracle` in `.env.oracle` to use Oracle. The current local setting remains SQLite until then. Run migrations with `.venv\Scripts\python -m alembic upgrade head` after confirming the local machine is allowed to connect to the database.

Set `WEALTHY_FIREBASE_PROJECT_ID` and `WEALTHY_FIREBASE_ALLOWED_UIDS` in `.env`. The allowlist accepts comma-separated Firebase UIDs; an empty allowlist denies access. For local token verification, set `WEALTHY_FIREBASE_CREDENTIALS_FILE` to the path of a Firebase Admin service-account JSON file, or configure Google Application Default Credentials through `GOOGLE_APPLICATION_CREDENTIALS`. Keep the credentials file outside the repository and never commit it.

The liveness endpoint is available at `/health`; interactive API documentation is at `/docs`. Business endpoints require a valid Firebase ID token and an allowed UID.

## Manual property import

Run the import from the project environment after the CSV is downloaded from Caixa:

```powershell
.venv\Scripts\wealthy-import-properties.exe "C:\Projetos\imoveis\public\Lista_imoveis_geral.csv"
```

The command stages the raw rows, validates and imports them in batches, then reports rejected, duplicate, and reactivated rows. Imports are not scheduled.

The same import is available to Firebase administrators through `POST /api/v1/admin/imoveis/importacoes` in Swagger using a multipart `file` field; `batch_size` is optional. Set `WEALTHY_FIREBASE_ADMIN_UIDS` to the comma-separated administrator UIDs. The endpoint limit defaults to 100 MiB and can be changed with `WEALTHY_IMPORT_MAX_BYTES`. The endpoint stores the upload temporarily, stages its raw rows in Oracle, and removes the temporary file after processing.

## Tests

```powershell
.venv\Scripts\python -m pytest
```