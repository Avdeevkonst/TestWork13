from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict


class TopTransaction(BaseModel):
    transaction_id: str
    amount: float

    model_config = ConfigDict(from_attributes=True)


class TransactionBase(BaseModel):
    transaction_id: str
    user_id: str
    amount: float
    currency: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class TransactionCreate(TransactionBase):
    pass


class TransactionResponse(BaseModel):
    message: str
    task_id: str


class StatisticsResponse(BaseModel):
    total_transactions: int
    average_transaction_amount: float
    top_transactions: List[TopTransaction]

    model_config = ConfigDict(from_attributes=True)
