import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy.ext.asyncio import create_async_engine

from src.infrastructure.database import Base
from src.domain.models import *

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url():
    from src.infrastructure.database import settings
    return settings.database_url


async def run_migrations_async() -> None:
    connectable = create_async_engine(get_url(), echo=False)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


asyncio.run(run_migrations_async())