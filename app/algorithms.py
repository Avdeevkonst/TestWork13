import heapq
from typing import List

from .models import Statistics, Transaction


def calculate_statistics(transactions: List[Transaction]) -> Statistics:
    if not transactions:
        return Statistics()

    # Calculate total and average
    total_amount = 0.0
    for transaction in transactions:
        total_amount += transaction.amount

    average_amount = total_amount / len(transactions)

    # Find top 3 transactions using a min-heap
    heap = []
    for transaction in transactions:
        if len(heap) < 3:
            heapq.heappush(heap, (transaction.amount, transaction))
        else:
            if transaction.amount > heap[0][0]:
                heapq.heappop(heap)
                heapq.heappush(heap, (transaction.amount, transaction))

    # Convert heap to sorted list
    top_transactions = []
    while heap:
        amount, transaction = heapq.heappop(heap)
        top_transactions.append(
            {"transaction_id": transaction.transaction_id, "amount": transaction.amount}
        )

    # Reverse to get descending order
    top_transactions.reverse()

    return Statistics(
        total_transactions=len(transactions),
        average_amount=average_amount,
        top_transactions=top_transactions,
    )
