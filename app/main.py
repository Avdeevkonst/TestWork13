from contextlib import asynccontextmanager

from fastapi import FastAPI

from .routers import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Transaction Service",
    description="A microservice for processing transactions",
    lifespan=lifespan,
    version="1.0.0",
)


app.include_router(router)
