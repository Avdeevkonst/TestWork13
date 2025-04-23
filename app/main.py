from fastapi import FastAPI
from fastapi.security import APIKeyHeader

app = FastAPI(
    title="Transaction Service",
    description="A microservice for processing transactions",
)

api_key_header = APIKeyHeader(name="Authorization")
