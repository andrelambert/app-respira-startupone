"""Ambiente do Alembic — usa os metadados do SQLModel (app.models)."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

import app.models  # noqa: F401 — registra as tabelas nos metadados
from app.config import get_settings

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = SQLModel.metadata


def _sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=_sqlite(config.get_main_option("sqlalchemy.url") or ""),
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = config.get_main_option("sqlalchemy.url") or ""
    if _sqlite(url):
        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
    else:
        # Oracle: usuário, senha e wallet vêm das ORACLE_* (o engine do app já os monta).
        from app.db import engine as connectable
    with connectable.connect() as connection:
        # render_as_batch: o SQLite só altera tabela recriando-a. No Oracle, ALTER direto.
        context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=_sqlite(url))
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
