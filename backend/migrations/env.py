"""Alembic environment — wired to the shared SQLAlchemy metadata.

Schema is defined across the app via a single ``metadata`` object. We register
every table module, then point Alembic at that metadata so autogenerate and the
baseline migration see the full schema. The DB URL comes from app settings.
"""
from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings  # noqa: E402
from database import metadata, _register_all_tables, _sync_engine  # noqa: E402

# Ensure every table is registered on the shared metadata before we use it.
_register_all_tables()

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = _sync_engine()
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
