import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import JSON, DateTime, Float, String
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(AsyncAttrs, DeclarativeBase): ...


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now
    )

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)


class PrimaryKeyUUID:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class General(Base, PrimaryKeyUUID, TimestampMixin):
    __abstract__ = True

    @declared_attr  # pyright: ignore[reportArgumentType]
    @classmethod
    def __tablename__(cls):
        return cls.__name__.lower()


class Transaction(General):
    transaction_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Statistics(General):
    total_transactions: Mapped[int] = mapped_column(default=0)
    average_amount: Mapped[float] = mapped_column(Float, default=0.0)
    top_transactions: Mapped[Optional[List[dict]]] = mapped_column(JSON, default=list)
