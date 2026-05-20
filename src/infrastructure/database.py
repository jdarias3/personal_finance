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
    "pool_size": 1,
    "max_overflow": 2,
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

db_url = settings.database_url
if "neon" in db_url.lower():
    db_url = db_url.replace("?sslmode=require", "").replace("&sslmode=require", "")
    db_url = db_url.replace("sslmode=require", "")

engine = create_async_engine(db_url, **engine_kwargs)

engine = create_async_engine(settings.database_url, **engine_kwargs)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    try:
        async with async_session_maker() as session:
            yield session
    except Exception as e:
        error_msg = str(e).lower()
        if "connection" in error_msg or "disconnect" in error_msg or "timeout" in error_msg:
            async with async_session_maker() as session:
                yield session
        else:
            raise