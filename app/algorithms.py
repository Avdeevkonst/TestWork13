import heapq
from typing import Sequence

from .models import Statistics, Transaction


def calculate_statistics(transactions: Sequence[Transaction]) -> Statistics:
    count = len(transactions)
    total_amount = sum(transaction.amount for transaction in transactions)
    average_amount = total_amount / count if count > 0 else 0.0

    top_count = 3
    min_heap = []

    for transaction in transactions:
        if len(min_heap) < top_count:
            heapq.heappush(min_heap, (transaction.amount, transaction.transaction_id))
        elif transaction.amount > min_heap[0][0]:
            heapq.heappop(min_heap)
            heapq.heappush(min_heap, (transaction.amount, transaction.transaction_id))

    top_transactions = []
    heap_items = [heapq.heappop(min_heap) for _ in range(len(min_heap))]
    for amount, transaction_id in reversed(heap_items):
        top_transactions.append({"transaction_id": transaction_id, "amount": amount})

    return Statistics(
        total_transactions=count,
        average_amount=average_amount,
        top_transactions=top_transactions,
    )
