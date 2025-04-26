import asyncio

from sqlalchemy import select

from .algorithms import calculate_statistics
from .celery import celery_app
from .database import PgUnitOfWork
from .models import Statistics, Transaction


@celery_app.task(name="app.tasks.update_statistics")
def update_statistics():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(_update_statistics_async())
    finally:
        loop.close()


async def _update_statistics_async():
    async with PgUnitOfWork() as session:
        transactions = (await session.execute(select(Transaction))).scalars().all()
        stats_result = (await session.execute(select(Statistics))).scalar_one_or_none()

        if not transactions:
            if stats_result:
                stats_result.total_transactions = 0
                stats_result.average_amount = 0.0
                stats_result.top_transactions = []
            else:
                stats = Statistics()
                session.add(stats)
        else:
            stats = calculate_statistics(transactions)

            if stats_result:
                stats_result.total_transactions = stats.total_transactions
                stats_result.average_amount = stats.average_amount
                stats_result.top_transactions = stats.top_transactions
            else:
                session.add(stats)

        await session.commit()

    return "Statistics updated"
