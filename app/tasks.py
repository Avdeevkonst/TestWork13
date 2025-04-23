from .algorithms import calculate_statistics
from .celery import celery_app
from .database import get_db
from .models import Statistics, Transaction


@celery_app.task(name="app.tasks.update_statistics")
def update_statistics():
    db = next(get_db())
    try:
        # Get all transactions
        transactions = db.query(Transaction).all()

        if not transactions:
            # If no transactions, reset statistics
            stats = Statistics()
            db.add(stats)
        else:
            # Calculate statistics
            stats = calculate_statistics(transactions)

            # Update or create statistics
            existing_stats = db.query(Statistics).first()
            if existing_stats:
                existing_stats.total_transactions = stats.total_transactions
                existing_stats.average_amount = stats.average_amount
                existing_stats.top_transactions = stats.top_transactions
            else:
                db.add(stats)

        db.commit()
    finally:
        db.close()
