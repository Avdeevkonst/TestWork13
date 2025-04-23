import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import get_db
from app.main import app
from app.models import Base

# Test database setup
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/transactions"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    return client


def test_create_transaction(client):
    response = client.post(
        "/transactions",
        json={
            "transaction_id": "test123",
            "user_id": "user1",
            "amount": 100.50,
            "currency": "USD",
            "timestamp": "2024-01-01T12:00:00",
        },
        headers={"Authorization": "ApiKey your-secret-api-key"},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Transaction received"


def test_delete_transactions(client):
    # First create a transaction
    client.post(
        "/transactions",
        json={
            "transaction_id": "test123",
            "user_id": "user1",
            "amount": 100.50,
            "currency": "USD",
            "timestamp": "2024-01-01T12:00:00",
        },
        headers={"Authorization": "ApiKey your-secret-api-key"},
    )

    # Then delete all transactions
    response = client.delete(
        "/transactions", headers={"Authorization": "ApiKey your-secret-api-key"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Transactions deleted"


def test_get_statistics(client):
    # Create multiple transactions
    transactions = [
        {
            "transaction_id": "test1",
            "user_id": "user1",
            "amount": 100.0,
            "currency": "USD",
            "timestamp": "2024-01-01T12:00:00",
        },
        {
            "transaction_id": "test2",
            "user_id": "user2",
            "amount": 200.0,
            "currency": "USD",
            "timestamp": "2024-01-01T12:00:00",
        },
        {
            "transaction_id": "test3",
            "user_id": "user3",
            "amount": 300.0,
            "currency": "USD",
            "timestamp": "2024-01-01T12:00:00",
        },
    ]

    for transaction in transactions:
        client.post(
            "/transactions",
            json=transaction,
            headers={"Authorization": "ApiKey your-secret-api-key"},
        )

    response = client.get(
        "/statistics", headers={"Authorization": "ApiKey your-secret-api-key"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_transactions"] == 3
    assert data["average_transaction_amount"] == 200.0
    assert len(data["top_transactions"]) == 3
    assert data["top_transactions"][0]["amount"] == 300.0
