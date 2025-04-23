# Transaction Processing Microservice

A robust microservice for processing transactions with real-time statistics calculation.

## Features

- REST API for transaction management
- PostgreSQL database for data persistence
- Redis + Celery for asynchronous processing
- Efficient algorithms for statistics calculation
- API key authentication
- Swagger documentation
- Comprehensive test suite

## Prerequisites

- Python 3.11+
- Docker and Docker Compose
- PostgreSQL
- Redis

## Local Development Setup

1. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/transactions
export REDIS_URL=redis://localhost:6379/0
export API_KEY=your-secret-api-key
```

4. Initialize the database:
```bash
python -c "from app.database import init_db; init_db()"
```

5. Run the application:
```bash
uvicorn app.main:app --reload
```

6. Run Celery worker:
```bash
celery -A app.celery worker --loglevel=info
```

## Docker Setup

1. Build and start the services:
```bash
docker-compose up --build
```

2. The API will be available at: http://localhost:8000
3. Swagger documentation: http://localhost:8000/docs

## API Endpoints

### POST /transactions
Create a new transaction.

Request body:
```json
{
  "transaction_id": "123456",
  "user_id": "user_001",
  "amount": 150.50,
  "currency": "USD",
  "timestamp": "2024-12-12T12:00:00"
}
```

### DELETE /transactions
Delete all transactions.

### GET /statistics
Get transaction statistics.

## Running Tests

```bash
pytest tests/
```

## Security

- API key authentication is required for all endpoints
- Pass the API key in the Authorization header: `Authorization: ApiKey your-secret-api-key`

## Performance Considerations

- Efficient heap-based algorithm for finding top transactions
- Asynchronous processing of statistics updates
- Database indexing for fast queries
- Memory-efficient calculations

## License

MIT License
