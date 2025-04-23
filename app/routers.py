import os

from fastapi import APIRouter, Depends, Header, HTTPException

from .celery import celery_app
from .database import get_db
from .models import Statistics, Transaction
from .schemas import StatisticsResponse, TransactionCreate, TransactionResponse

router = APIRouter()

API_KEY = os.getenv("API_KEY", "your-secret-api-key")


async def verify_api_key(authorization: str = Header(...)):
    if authorization != f"ApiKey {API_KEY}":
        raise HTTPException(status_code=403, detail="Invalid API key")
    return authorization


@router.post("/transactions", response_model=TransactionResponse)
async def create_transaction(
    transaction: TransactionCreate, db=Depends(get_db), _=Depends(verify_api_key)
):
    # Check for duplicate transaction_id
    existing = (
        db.query(Transaction)
        .filter(Transaction.transaction_id == transaction.transaction_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Transaction ID already exists")

    # Create new transaction
    db_transaction = Transaction(**transaction.model_dump())
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)

    # Trigger statistics update
    celery_app.send_task("app.tasks.update_statistics")

    return TransactionResponse(
        message="Transaction received",
        task_id="task_placeholder",  # In a real app, this would be the actual Celery task ID
    )


@router.delete("/transactions")
async def delete_transactions(db=Depends(get_db), _=Depends(verify_api_key)):
    db.query(Transaction).delete()
    db.query(Statistics).delete()
    db.commit()
    return {"message": "Transactions deleted"}


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(db=Depends(get_db), _=Depends(verify_api_key)):
    stats = db.query(Statistics).first()
    if not stats:
        return StatisticsResponse(
            total_transactions=0, average_transaction_amount=0.0, top_transactions=[]
        )
    return StatisticsResponse(
        total_transactions=stats.total_transactions,
        average_transaction_amount=stats.average_amount,
        top_transactions=stats.top_transactions,
    )
