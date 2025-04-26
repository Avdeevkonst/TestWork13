import asyncio
import os
from datetime import datetime
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.main import app
from app.models import Base

# Test database setup - using async driver
TEST_DB_NAME = "transactions_test"
SQLALCHEMY_DATABASE_URL = f"postgresql+asyncpg://{settings.PG_USER}:{settings.PG_PASS}@{settings.PG_HOST}:{settings.PG_PORT}/{TEST_DB_NAME}"

engine = create_async_engine(SQLALCHEMY_DATABASE_URL)
test_async_session = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


@pytest_asyncio.fixture
async def setup_db():
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Provide the session
    yield

    # Clean up
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def async_client(setup_db) -> AsyncGenerator[AsyncClient, None]:
    # Override the dependency to use test database
    original_db_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = SQLALCHEMY_DATABASE_URL

    # Create client
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    # Restore original environment
    if original_db_url:
        os.environ["DATABASE_URL"] = original_db_url
    else:
        os.environ.pop("DATABASE_URL", None)


@pytest.mark.asyncio
async def test_create_transaction(async_client):
    response = await async_client.post(
        "/api/v1/transactions",
        json={
            "transaction_id": "test123",
            "user_id": "user1",
            "amount": 100.50,
            "currency": "USD",
            "timestamp": datetime.utcnow().isoformat(),
        },
        headers={"Authorization": settings.API_KEY},
    )
    assert response.status_code == 201
    assert response.json()["message"] == "Transaction received"
    assert "task_id" in response.json()


@pytest.mark.asyncio
async def test_duplicate_transaction(async_client):
    # Create transaction
    transaction_data = {
        "transaction_id": "duplicate_test",
        "user_id": "user1",
        "amount": 100.50,
        "currency": "USD",
        "timestamp": datetime.utcnow().isoformat(),
    }

    # First request should succeed
    response1 = await async_client.post(
        "/api/v1/transactions",
        json=transaction_data,
        headers={"Authorization": settings.API_KEY},
    )
    assert response1.status_code == 201

    # Second request with same transaction_id should fail
    response2 = await async_client.post(
        "/api/v1/transactions",
        json=transaction_data,
        headers={"Authorization": settings.API_KEY},
    )
    assert response2.status_code == 400
    assert "already exists" in response2.json()["detail"]


@pytest.mark.asyncio
async def test_delete_transactions(async_client):
    # Create a transaction first
    await async_client.post(
        "/api/v1/transactions",
        json={
            "transaction_id": "delete_test",
            "user_id": "user1",
            "amount": 100.50,
            "currency": "USD",
            "timestamp": datetime.utcnow().isoformat(),
        },
        headers={"Authorization": settings.API_KEY},
    )

    # Then delete all transactions
    response = await async_client.delete(
        "/api/v1/transactions", headers={"Authorization": settings.API_KEY}
    )
    assert response.status_code == 204

    # Verify statistics are reset
    stats_response = await async_client.get(
        "/api/v1/statistics", headers={"Authorization": settings.API_KEY}
    )
    assert stats_response.status_code == 200
    stats_data = stats_response.json()
    assert stats_data["total_transactions"] == 0
    assert stats_data["average_transaction_amount"] == 0.0
    assert len(stats_data["top_transactions"]) == 0


@pytest.mark.asyncio
async def test_get_statistics(async_client):
    # Create multiple transactions
    transactions = [
        {
            "transaction_id": f"test{i}",
            "user_id": f"user{i}",
            "amount": 100.0 * (i + 1),
            "currency": "USD",
            "timestamp": datetime.utcnow().isoformat(),
        }
        for i in range(3)
    ]

    for transaction in transactions:
        await async_client.post(
            "/api/v1/transactions",
            json=transaction,
            headers={"Authorization": settings.API_KEY},
        )

    # Allow time for the Celery task to complete
    await asyncio.sleep(1)

    # Get statistics
    response = await async_client.get(
        "/api/v1/statistics", headers={"Authorization": settings.API_KEY}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_transactions"] == 3
    assert data["average_transaction_amount"] == 200.0
    assert len(data["top_transactions"]) == 3
    # Verify top transaction has the highest amount
    assert data["top_transactions"][0]["amount"] == 300.0
    assert data["top_transactions"][0]["transaction_id"] == "test2"


@pytest.mark.asyncio
async def test_race_condition(async_client):
    """Test creating multiple transactions concurrently to simulate race conditions"""

    # Define a large number of concurrent transactions
    num_transactions = 50
    transactions = [
        {
            "transaction_id": f"race{i}",
            "user_id": f"user{i % 5}",  # Reuse some user_ids
            "amount": float(i * 10),  # Different amounts
            "currency": "USD",
            "timestamp": datetime.utcnow().isoformat(),
        }
        for i in range(num_transactions)
    ]

    # Function to create a single transaction
    async def create_transaction(transaction):
        return await async_client.post(
            "/api/v1/transactions",
            json=transaction,
            headers={"Authorization": settings.API_KEY},
        )

    # Create all transactions concurrently
    tasks = [create_transaction(tx) for tx in transactions]
    responses = await asyncio.gather(*tasks)

    # Verify all responses
    for i, response in enumerate(responses):
        assert response.status_code == 201, f"Transaction {i} failed: {response.text}"

    # Allow time for the Celery tasks to complete
    await asyncio.sleep(2)

    # Verify statistics
    stats_response = await async_client.get(
        "/api/v1/statistics", headers={"Authorization": settings.API_KEY}
    )
    assert stats_response.status_code == 200

    stats_data = stats_response.json()
    assert stats_data["total_transactions"] == num_transactions

    # Calculate expected average
    expected_avg = sum(tx["amount"] for tx in transactions) / num_transactions
    assert abs(stats_data["average_transaction_amount"] - expected_avg) < 0.01

    # Verify top 3 transactions
    assert len(stats_data["top_transactions"]) == 3

    # Top transactions should be the ones with highest amounts
    sorted_amounts = sorted([tx["amount"] for tx in transactions], reverse=True)
    top_three_amounts = sorted_amounts[:3]

    stat_amounts = [tx["amount"] for tx in stats_data["top_transactions"]]
    for amount in top_three_amounts:
        assert amount in stat_amounts
