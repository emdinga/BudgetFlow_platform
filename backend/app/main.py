from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, datetime
from decimal import Decimal
from time import perf_counter
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field
import psycopg
from psycopg_pool import PoolTimeout
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from app.database import create_pool


HTTP_REQUESTS_TOTAL = Counter(
    "budgetflow_http_requests_total",
    "HTTP requests handled by the BudgetFlow API.",
    ("method", "route", "status_code"),
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "budgetflow_http_request_duration_seconds",
    "HTTP request duration in seconds.",
    ("method", "route"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)


class TransactionCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    direction: Literal["income", "expense"]
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    category: str = Field(min_length=1, max_length=50)
    description: str = Field(min_length=1, max_length=200)
    occurred_on: date


class Transaction(TransactionCreate):
    id: int
    created_at: datetime


class CurrencySummary(BaseModel):
    currency: str
    income: Decimal
    expenses: Decimal
    net: Decimal


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = create_pool()
    pool.open(wait=False)
    app.state.db_pool = pool
    try:
        yield
    finally:
        pool.close()


app = FastAPI(
    title="BudgetFlow API",
    version="0.1.0",
    description="A small internal budgeting API for the BudgetFlow platform lab.",
    lifespan=lifespan,
)


@app.middleware("http")
async def collect_http_metrics(request: Request, call_next):
    if request.url.path == "/metrics":
        return await call_next(request)

    started = perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        route = request.scope.get("route")
        route_name = getattr(route, "path", "unmatched")
        HTTP_REQUESTS_TOTAL.labels(
            request.method, route_name, str(status_code)
        ).inc()
        HTTP_REQUEST_DURATION_SECONDS.labels(
            request.method, route_name
        ).observe(perf_counter() - started)


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health/live", tags=["health"])
def live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready", tags=["health"])
def ready(request: Request) -> dict[str, str]:
    try:
        with request.app.state.db_pool.connection() as conn:
            row = conn.execute(
                "SELECT to_regclass('public.transactions') AS table_name"
            ).fetchone()
    except (PoolTimeout, psycopg.Error, OSError) as exc:
        raise HTTPException(status_code=503, detail="database unavailable") from exc

    if not row or row["table_name"] is None:
        raise HTTPException(status_code=503, detail="database schema not initialized")
    return {"status": "ready"}


@app.get("/api/transactions", response_model=list[Transaction], tags=["transactions"])
def list_transactions(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[dict]:
    with request.app.state.db_pool.connection() as conn:
        rows = conn.execute(
            """
            SELECT id, direction, amount, currency, category, description,
                   occurred_on, created_at
            FROM transactions
            ORDER BY occurred_on DESC, id DESC
            LIMIT %s OFFSET %s
            """,
            (limit, offset),
        ).fetchall()
    return rows


@app.post(
    "/api/transactions",
    response_model=Transaction,
    status_code=status.HTTP_201_CREATED,
    tags=["transactions"],
)
def create_transaction(payload: TransactionCreate, request: Request) -> dict:
    with request.app.state.db_pool.connection() as conn:
        row = conn.execute(
            """
            INSERT INTO transactions
                (direction, amount, currency, category, description, occurred_on)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, direction, amount, currency, category, description,
                      occurred_on, created_at
            """,
            (
                payload.direction,
                payload.amount,
                payload.currency,
                payload.category,
                payload.description,
                payload.occurred_on,
            ),
        ).fetchone()
    return row


@app.get("/api/summary", response_model=list[CurrencySummary], tags=["summary"])
def get_summary(request: Request) -> list[dict]:
    with request.app.state.db_pool.connection() as conn:
        rows = conn.execute(
            """
            SELECT currency,
                   COALESCE(SUM(amount) FILTER (WHERE direction = 'income'), 0) AS income,
                   COALESCE(SUM(amount) FILTER (WHERE direction = 'expense'), 0) AS expenses,
                   COALESCE(SUM(amount) FILTER (WHERE direction = 'income'), 0)
                     - COALESCE(SUM(amount) FILTER (WHERE direction = 'expense'), 0) AS net
            FROM transactions
            GROUP BY currency
            ORDER BY currency
            """
        ).fetchall()
    return rows
