from functools import lru_cache
from pathlib import Path
from typing import Final

from loguru import logger
from pydantic_settings import BaseSettings

BASE_DIR: Final = Path(__file__).parent.parent.parent

logger.add(
    "logs/{time:YYYY-MM-DD}.log",
    format="{time} | {file} | {function} | {level} | {message}",
    rotation="1 day",
)


class Settings(BaseSettings):
    """
    Settings for the application.
    """

    ORIGINS: list[str] = ["*"]
    API_KEY: str = "1234567890"

    PG_HOST: str = "localhost"
    PG_PORT: str = "5432"
    PG_NAME: str = "transactions"
    PG_USER: str = "postgres"
    PG_PASS: str = "postgres"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: str = "6379"

    ECHO: bool = False

    @property
    def db_url_postgresql(self) -> str:
        return f"postgresql+asyncpg://{self.PG_USER}:{self.PG_PASS}@{self.PG_HOST}:{self.PG_PORT}/{self.PG_NAME}"

    @property
    def db_url_redis(self) -> str:
        return f"redis://@{self.REDIS_HOST}:{self.REDIS_PORT}/"


settings_instance = None


@lru_cache(maxsize=2)
def get_settings() -> Settings:
    global settings_instance
    if settings_instance is None:
        settings_instance = Settings()
    return settings_instance


settings = get_settings()
