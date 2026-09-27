# Wealthy API

REST API for Wealthy, built with FastAPI, SQLAlchemy, Oracle Database and Firebase Authentication.

## Local development

Requirements: Python 3.12 or newer, below 3.15.

```powershell
py -3.14 -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
Copy-Item .env.example .env
Copy-Item .env.oracle.example .env.oracle
.venv\Scripts\python -m alembic upgrade head
.venv\Scripts\python -m uvicorn wealthy_api.main:app --reload
```

Oracle Autonomous Database is the only supported backend. Set the database username/password and extracted wallet directory in the ignored local `.env.oracle`; the TNS alias is prefilled in its example. Keep the wallet and both passwords outside Git. The machine must be allowed to connect to the database before running `.venv\Scripts\python -m alembic upgrade head`.

Set `WEALTHY_FIREBASE_PROJECT_ID` and `WEALTHY_FIREBASE_ALLOWED_UIDS` in `.env`. The allowlist accepts comma-separated Firebase UIDs; an empty allowlist denies access. For local token verification, set `WEALTHY_FIREBASE_CREDENTIALS_FILE` to the path of a Firebase Admin service-account JSON file, or configure Google Application Default Credentials through `GOOGLE_APPLICATION_CREDENTIALS`. Keep the credentials file outside the repository and never commit it.

The liveness endpoint is available at `/health`; interactive API documentation is at `/docs`. Business endpoints require a valid Firebase ID token and an allowed UID.

## Manual property import

Run the import from the project environment after the CSV is downloaded from Caixa:

```powershell
.venv\Scripts\wealthy-import-properties.exe "C:\Projetos\imoveis\public\Lista_imoveis_geral.csv"
```

The command stages the raw rows, validates and imports them in batches, then reports rejected, duplicate, and reactivated rows. The parser skips blank/metadata lines before the Caixa header and accepts aliases such as `N° do imóvel`, `Valor de avaliação`, `Modalidade de venda` and `Link de acesso`. Imports are not scheduled.

The same import is available to Firebase administrators through `POST /api/v1/admin/imoveis/importacoes` in Swagger using a multipart `file` field; `batch_size` is optional. Set `WEALTHY_FIREBASE_ADMIN_UIDS` to the comma-separated administrator UIDs. The endpoint limit defaults to 100 MiB and can be changed with `WEALTHY_IMPORT_MAX_BYTES`. The endpoint stores the upload temporarily, stages its raw rows in Oracle, and removes the temporary file after processing.

## Tests

Tests require Oracle credentials/wallet and use a rolled-back transaction for integration records. Apply migrations before running the suite.

```powershell
.venv\Scripts\python -m pytest
```