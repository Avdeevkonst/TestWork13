from abc import ABC, abstractmethod
from types import TracebackType
from typing import Any

from fastapi import HTTPException
from sqlalchemy import (
    Executable,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from .config import settings
from .utils import handle_error


class NotCreatedSessionError(NotImplementedError): ...


class DatabaseConfig:
    def __init__(
        self,
        db_url_postgresql: str,
    ):
        self.db_url_postgresql = db_url_postgresql

    @property
    def engine(self):
        return create_async_engine(
            self.db_url_postgresql, echo=settings.ECHO, poolclass=NullPool
        )

    @property
    def async_session_maker(self):
        return async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )


class IUnitOfWorkBase(ABC):
    async def __aenter__(self):
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ):
        await self.rollback()

    @abstractmethod
    async def commit(self):
        raise NotImplementedError

    @abstractmethod
    async def close(self):
        raise NotImplementedError

    @abstractmethod
    async def rollback(self):
        raise NotImplementedError


db_config = DatabaseConfig(settings.db_url_postgresql)


class PgUnitOfWork(IUnitOfWorkBase):
    def __init__(self) -> None:
        self._session_factory = db_config.async_session_maker
        self._async_session: AsyncSession | None = None

    def activate_session(self):
        if self._async_session is None:
            self._async_session = self._session_factory()

    async def __aenter__(self):
        self.activate_session()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ):
        if exc_type is not None:
            await self.rollback()

        await self.close()
        if isinstance(exc_val, HTTPException):
            raise exc_val
        handle_error(exc_type, exc_val, exc_tb)

    async def rollback(self):
        if self._async_session is None:
            raise NotCreatedSessionError

        await self._async_session.rollback()

    async def close(self):
        if self._async_session is None:
            raise NotCreatedSessionError
        await self._async_session.close()

    async def commit(self):
        if self._async_session is None:
            raise NotCreatedSessionError
        await self._async_session.commit()

    async def flush(self):
        if self._async_session is None:
            raise NotCreatedSessionError
        await self._async_session.flush()

    async def refresh(self, instance: object):
        if self._async_session is None:
            raise NotCreatedSessionError
        await self._async_session.refresh(instance)

    async def execute(self, statement: Executable, *args: Any):
        if self._async_session is None:
            raise NotCreatedSessionError
        return await self._async_session.execute(statement, *args)

    def add(self, instance: object):
        if self._async_session is None:
            raise NotCreatedSessionError
        self._async_session.add(instance)

    def add_all(self, *instance: object):
        if self._async_session is None:
            raise NotCreatedSessionError
        self._async_session.add_all(instance)
