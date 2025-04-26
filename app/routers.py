from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select

from app.database import PgUnitOfWork
from app.utils import verify_api_key

from .celery import celery_app
from .models import Statistics, Transaction
from .schemas import (
    StatisticsResponse,
    TopTransaction,
    TransactionCreate,
    TransactionResponse,
)

router = APIRouter(prefix="/api/v1")


@router.post(
    "/transactions",
    response_model=TransactionResponse,
    status_code=201,
)
async def create_transaction(
    transaction: TransactionCreate,
    _=Depends(verify_api_key),
):
    async with PgUnitOfWork() as db:
        result = await db.execute(
            select(Transaction).where(
                Transaction.transaction_id == transaction.transaction_id
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            raise HTTPException(status_code=400, detail="Transaction ID already exists")

        db_transaction = Transaction(**transaction.model_dump())
        db.add(db_transaction)
        await db.commit()
        await db.refresh(db_transaction)

    task = celery_app.send_task("app.tasks.update_statistics")

    return TransactionResponse(
        message="Transaction received",
        task_id=task.id,
    )


@router.delete(
    "/transactions",
    status_code=204,
)
async def delete_transactions(
    _=Depends(verify_api_key),
):
    async with PgUnitOfWork() as db:
        await db.execute(delete(Transaction))
        await db.execute(delete(Statistics))
        await db.commit()
    return {"message": "Transactions deleted"}


@router.get(
    "/statistics",
    response_model=StatisticsResponse,
    status_code=200,
)
async def get_statistics(
    _=Depends(verify_api_key),
):
    async with PgUnitOfWork() as db:
        result = await db.execute(select(Statistics))
        stats = result.scalar_one_or_none()

    if not stats:
        return StatisticsResponse(
            total_transactions=0, average_transaction_amount=0.0, top_transactions=[]
        )

    top_transactions = (
        [
            TopTransaction(transaction_id=t["transaction_id"], amount=t["amount"])
            for t in stats.top_transactions
        ]
        if stats.top_transactions
        else []
    )

    return StatisticsResponse(
        total_transactions=stats.total_transactions,
        average_transaction_amount=stats.average_amount,
        top_transactions=top_transactions,
    )
