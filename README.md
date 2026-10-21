# BudgetFlow application handoff

This folder contains only the application a developer would build and maintain: a FastAPI backend, a static HTML frontend served by NGINX, and a PostgreSQL schema migration.

## What the app does

- Record income and expense transactions with amount, currency, category, description, and date.
- List transactions and calculate totals grouped by currency.
- Expose health endpoints and Prometheus metrics for the platform to monitor.

## Structure

- `backend/app/`: API code and database connection handling.
- `backend/tests/`: API unit tests.
- `backend/migrations/`: database schema changes, applied by the migration command.
- `backend/requirements.txt`: runtime Python dependencies.
- `frontend/`: static user interface, NGINX configuration, and container build file.

## Run the API locally

The API needs a reachable PostgreSQL database. Create an empty database and set these environment variables in your terminal before starting it:

- `PGHOST`
- `PGPORT` (optional; defaults to `5432`)
- `PGDATABASE`
- `PGUSER`
- `PGPASSWORD`

Do not commit database passwords or `.env` files. In VS Code, open a terminal at `backend/`, create a virtual environment, and install the dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

After setting the database variables for that terminal session, apply the schema and start the API:

```powershell
python -m app.migrate
python -m uvicorn app.main:app --reload
```

The API listens on `http://127.0.0.1:8000`; interactive API docs are at `/docs`. The frontend NGINX config proxies `/api/` and `/health/` to a service named `budgetflow-api`. Local frontend hosting and proxy wiring are application setup tasks.

## Run the unit tests

From `backend/`:

```powershell
python -m pip install -r requirements-test.txt
python -m pytest -q
```

The tests mock the database, so they do not replace integration checks against a real PostgreSQL instance.

## Developer and platform responsibilities

This is the application handoff only. It contains no GitHub Actions, Kubernetes manifests, Terraform, Ansible, monitoring stack deployment, or server configuration. Those are platform engineering work for you to design and operate.

The starter currently has **no authentication or per-user data isolation**. Use a private lab and synthetic data only. Before handling real financial data or exposing the app beyond the lab, authentication, authorization, and ownership checks need to be implemented and verified with the developer.
