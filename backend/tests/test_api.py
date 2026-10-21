from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app import main


class FakeConnection:
    def __init__(self) -> None:
        self.last_query = ""
        self.last_params = None

    def __enter__(self) -> FakeConnection:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def execute(self, query: str, params: tuple | None = None) -> FakeConnection:
        self.last_query = query
        self.last_params = params
        return self

    def fetchone(self) -> dict:
        if "to_regclass" in self.last_query:
            return {"table_name": "transactions"}
        return {
            "id": 1,
            "direction": "expense",
            "amount": Decimal("12.50"),
            "currency": "ZAR",
            "category": "food",
            "description": "Lunch",
            "occurred_on": date(2026, 10, 20),
            "created_at": datetime(2026, 10, 20, tzinfo=timezone.utc),
        }

    def fetchall(self) -> list[dict]:
        if "FROM transactions\n            GROUP BY currency" in self.last_query:
            return [{
                "currency": "ZAR",
                "income": Decimal("0.00"),
                "expenses": Decimal("12.50"),
                "net": Decimal("-12.50"),
            }]
        return []


class FakePool:
    def open(self, wait: bool = False) -> None:
        assert wait is False

    def close(self) -> None:
        return None

    def connection(self) -> FakeConnection:
        return FakeConnection()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(main, "create_pool", FakePool)
    with TestClient(main.app) as test_client:
        yield test_client


def test_liveness_does_not_require_database(client: TestClient) -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_metrics_endpoint_exposes_requests_and_latency(client: TestClient) -> None:
    client.get("/health/live")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "budgetflow_http_requests_total" in response.text
    assert "budgetflow_http_request_duration_seconds_bucket" in response.text
    assert 'route="/health/live"' in response.text


def test_readiness_checks_migrated_database(client: TestClient) -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_create_transaction_returns_created_resource(client: TestClient) -> None:
    response = client.post(
        "/api/transactions",
        json={
            "direction": "expense",
            "amount": "12.50",
            "currency": "ZAR",
            "category": "food",
            "description": "Lunch",
            "occurred_on": "2026-10-20",
        },
    )
    assert response.status_code == 201
    assert response.json()["amount"] == "12.50"
    assert response.json()["currency"] == "ZAR"


@pytest.mark.parametrize("amount", ["0", "-1", "not-money"])
def test_invalid_amount_is_rejected(client: TestClient, amount: str) -> None:
    response = client.post(
        "/api/transactions",
        json={
            "direction": "expense",
            "amount": amount,
            "currency": "ZAR",
            "category": "food",
            "description": "Lunch",
            "occurred_on": "2026-10-20",
        },
    )
    assert response.status_code == 422


def test_summary_is_grouped_by_currency(client: TestClient) -> None:
    response = client.get("/api/summary")
    assert response.status_code == 200
    assert response.json() == [{
        "currency": "ZAR",
        "income": "0.00",
        "expenses": "12.50",
        "net": "-12.50",
    }]
