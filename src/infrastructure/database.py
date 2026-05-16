from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import AsyncAdaptedQueuePool


class Base(DeclarativeBase):
    pass


def create_settings():
    from pydantic_settings import BaseSettings
    
    class Settings(BaseSettings):
        database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/personal_finance"
        secret_key: str = "dev-secret-change-in-production"
        environment: str = "development"
        
        class Config:
            env_file = ".env"
            extra = "ignore"
    
    return Settings()


settings = create_settings()

engine_kwargs = {
    "echo": settings.environment == "development",
    "poolclass": AsyncAdaptedQueuePool,
    "pool_size": 5,
    "max_overflow": 10,
    "pool_pre_ping": True,
}

if "ssl" in settings.database_url.lower() or "neon" in settings.database_url.lower():
    engine_kwargs["connect_args"] = {"ssl": "require"}

engine = create_async_engine(settings.database_url, **engine_kwargs)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session