import asyncio
import os
import random
import uuid
from datetime import datetime, timezone
from typing import Dict, Union

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import delete, select

from app.database import PgUnitOfWork  # type: ignore
from app.main import app
from app.models import Statistics, Transaction

# API key from environment or default for testing
API_KEY = os.getenv("API_KEY", "your-secret-api-key")
HEADERS = {"Authorization": f"ApiKey {API_KEY}"}

BASE_URL = "http://test"


@pytest.fixture
async def client():
    """Async client fixture for testing the API."""
    async with AsyncClient(app=app, base_url=BASE_URL) as client:
        yield client


@pytest.fixture
async def clean_db():
    """Clean the database before and after each test."""
    async with PgUnitOfWork() as db:  # type: ignore
        await db.execute(delete(Transaction))
        await db.execute(delete(Statistics))
        await db.commit()
    yield
    async with PgUnitOfWork() as db:  # type: ignore
        await db.execute(delete(Transaction))
        await db.execute(delete(Statistics))
        await db.commit()


def create_transaction_data(transaction_id: str | None = None) -> Dict:
    """Create random transaction data."""
    return {
        "transaction_id": transaction_id
        if transaction_id is not None
        else str(uuid.uuid4()),
        "user_id": f"user_{random.randint(1, 1000)}",
        "amount": round(random.uniform(10, 1000), 2),
        "currency": random.choice(["USD", "EUR", "GBP"]),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def verify_statistics(client: AsyncClient, expected_count: int) -> None:
    """Verify that statistics endpoint returns expected data."""
    response = await client.get("/api/v1/statistics", headers=HEADERS)
    assert response.status_code == 200

    data = response.json()
    assert data["total_transactions"] == expected_count

    if expected_count > 0:
        assert data["average_transaction_amount"] > 0
        assert len(data["top_transactions"]) <= 3

        # Verify the top transactions are in descending order
        if len(data["top_transactions"]) > 1:
            amounts = [t["amount"] for t in data["top_transactions"]]
            assert all(amounts[i] >= amounts[i + 1] for i in range(len(amounts) - 1))


@pytest.mark.asyncio
async def test_create_transaction(client: AsyncClient, clean_db):
    """Test creating a transaction."""
    data = create_transaction_data()

    response = await client.post("/api/v1/transactions", json=data, headers=HEADERS)
    assert response.status_code == 201

    result = response.json()
    assert "message" in result
    assert "task_id" in result
    assert result["message"] == "Transaction received"

    # Verify transaction was added to database
    async with PgUnitOfWork() as db:  # type: ignore
        result = await db.execute(
            select(Transaction).where(
                Transaction.transaction_id == data["transaction_id"]
            )
        )
        transaction = result.scalar_one_or_none()
        assert transaction is not None
        assert transaction.transaction_id == data["transaction_id"]
        assert transaction.amount == data["amount"]


@pytest.mark.asyncio
async def test_create_duplicate_transaction(client: AsyncClient, clean_db):
    """Test creating a transaction with duplicate ID."""
    data = create_transaction_data()

    # First creation should succeed
    response = await client.post("/api/v1/transactions", json=data, headers=HEADERS)
    assert response.status_code == 201

    # Second creation with same ID should fail
    response = await client.post("/api/v1/transactions", json=data, headers=HEADERS)
    assert response.status_code == 400
    assert "Transaction ID already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_statistics_empty(client: AsyncClient, clean_db):
    """Test getting statistics when no transactions exist."""
    response = await client.get("/api/v1/statistics", headers=HEADERS)
    assert response.status_code == 200

    data = response.json()
    assert data["total_transactions"] == 0
    assert data["average_transaction_amount"] == 0
    assert data["top_transactions"] == []


@pytest.mark.asyncio
async def test_get_statistics_with_transactions(client: AsyncClient, clean_db):
    """Test getting statistics with transactions."""
    # Add 5 transactions
    transactions = []
    for _ in range(5):
        data = create_transaction_data()
        transactions.append(data)
        await client.post("/api/v1/transactions", json=data, headers=HEADERS)

    # Wait a bit for statistics to update
    await asyncio.sleep(1)

    # Get statistics
    response = await client.get("/api/v1/statistics", headers=HEADERS)
    assert response.status_code == 200

    data = response.json()
    assert data["total_transactions"] == 5

    # Calculate expected average
    expected_avg = sum(t["amount"] for t in transactions) / len(transactions)
    assert abs(data["average_transaction_amount"] - expected_avg) < 0.01

    # Verify top transactions (up to 3)
    top_transactions = sorted(transactions, key=lambda x: x["amount"], reverse=True)[:3]
    top_amounts = [t["amount"] for t in top_transactions]

    returned_amounts = [t["amount"] for t in data["top_transactions"]]
    assert len(returned_amounts) <= 3

    # Verify the returned top transactions are indeed the largest ones
    for amount in returned_amounts:
        assert amount in top_amounts


@pytest.mark.asyncio
async def test_delete_transactions(client: AsyncClient, clean_db):
    """Test deleting all transactions."""
    # Add some transactions
    for _ in range(3):
        await client.post(
            "/api/v1/transactions", json=create_transaction_data(), headers=HEADERS
        )

    # Delete all transactions
    response = await client.delete("/api/v1/transactions", headers=HEADERS)
    assert response.status_code == 204

    # Verify transactions were deleted
    async with PgUnitOfWork() as db:  # type: ignore
        result = await db.execute(select(Transaction))
        transactions = result.scalars().all()
        assert len(transactions) == 0

        # Verify statistics were also reset
        result = await db.execute(select(Statistics))
        stats = result.scalar_one_or_none()
        assert stats is None or stats.total_transactions == 0


@pytest.mark.asyncio
async def test_authorization(client: AsyncClient, clean_db):
    """Test that API requires valid authorization."""
    # Try without headers
    response = await client.get("/api/v1/statistics")
    assert response.status_code == 403

    # Try with invalid API key
    invalid_headers = {"Authorization": "ApiKey invalid-key"}
    response = await client.get("/api/v1/statistics", headers=invalid_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_race_condition(client: AsyncClient, clean_db):
    """Test for race conditions when multiple transactions are created simultaneously."""
    # Create 20 transactions to submit concurrently
    transaction_data = [create_transaction_data() for _ in range(20)]

    # Submit all transactions concurrently
    async def submit_transaction(data) -> Response:
        return await client.post("/api/v1/transactions", json=data, headers=HEADERS)

    tasks = [submit_transaction(data) for data in transaction_data]
    responses = await asyncio.gather(*tasks)

    # Check that all transactions were submitted successfully
    success_count = sum(1 for r in responses if r.status_code == 201)
    assert success_count == 20

    # Wait for statistics to update
    await asyncio.sleep(1)

    # Verify statistics
    await verify_statistics(client, expected_count=20)

    # Verify all transactions are in the database
    async with PgUnitOfWork() as db:  # type: ignore
        result = await db.execute(select(Transaction))
        transactions = result.scalars().all()
        assert len(transactions) == 20


@pytest.mark.asyncio
async def test_race_condition_duplicate_ids(client: AsyncClient, clean_db):
    """Test for race conditions with duplicate transaction IDs."""
    # Create 10 transactions, with some having duplicate IDs
    transaction_ids = [
        str(uuid.uuid4()) for _ in range(5)
    ] * 2  # 5 unique IDs, each used twice
    transaction_data = [create_transaction_data(tid) for tid in transaction_ids]

    # Submit all transactions concurrently
    async def submit_transaction(data) -> Union[Response, Exception]:
        try:
            return await client.post("/api/v1/transactions", json=data, headers=HEADERS)
        except Exception as e:
            # Return the exception to ensure we can gather all results
            return e

    tasks = [submit_transaction(data) for data in transaction_data]
    responses = await asyncio.gather(*tasks)

    # Check results - we should have 5 successful and 5 failed submissions
    success_count = sum(
        1 for r in responses if isinstance(r, Response) and r.status_code == 201
    )
    error_count = sum(
        1 for r in responses if isinstance(r, Response) and r.status_code == 400
    )

    assert success_count + error_count == 10
    assert success_count >= 5  # At least our unique IDs should succeed

    # Wait for statistics to update
    await asyncio.sleep(1)

    # Verify statistics reflect only the successful transactions
    await verify_statistics(client, expected_count=success_count)


@pytest.mark.asyncio
async def test_statistics_calculation_accuracy(client: AsyncClient, clean_db):
    """Test that statistics are calculated accurately, especially for top transactions."""
    # Create transactions with known amounts
    amounts = [100, 200, 50, 500, 300, 250, 150, 450, 350, 400]
    top_amounts = sorted(amounts, reverse=True)[:3]  # Top 3 amounts

    for amount in amounts:
        data = create_transaction_data()
        data["amount"] = amount
        await client.post("/api/v1/transactions", json=data, headers=HEADERS)

    # Wait for statistics to update
    await asyncio.sleep(1)

    # Get statistics
    response = await client.get("/api/v1/statistics", headers=HEADERS)
    assert response.status_code == 200

    data = response.json()
    assert data["total_transactions"] == len(amounts)

    # Verify average
    expected_avg = sum(amounts) / len(amounts)
    assert abs(data["average_transaction_amount"] - expected_avg) < 0.01

    # Verify top transactions
    returned_amounts = [t["amount"] for t in data["top_transactions"]]
    assert len(returned_amounts) == 3

    # The returned top amounts should match our expected top amounts
    for amount in returned_amounts:
        assert amount in top_amounts
