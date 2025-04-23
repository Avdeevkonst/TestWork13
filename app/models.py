from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, unique=True, index=True)
    user_id = Column(String, index=True)
    amount = Column(Float)
    currency = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)


class Statistics(Base):
    __tablename__ = "statistics"

    id = Column(Integer, primary_key=True, index=True)
    total_transactions = Column(Integer, default=0)
    average_amount = Column(Float, default=0.0)
    top_transactions = Column(JSON, default=list)
