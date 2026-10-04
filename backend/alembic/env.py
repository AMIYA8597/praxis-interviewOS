"""
Alembic environment.

The canonical DDL is supabase/migrations/*.sql (see scripts/migrate.py).
Revision 004_reconcile_schema adopts it, so `alembic upgrade head` and
`python scripts/migrate.py` converge on the same schema.

URL precedence: `alembic -x db_url=...` > $DATABASE_URL > settings default.
"""
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(REPO_ROOT, ".env"))

from backend.app.db.models import Base  # noqa: E402  (registers all tables on the metadata)
from packages.config.settings import Settings  # noqa: E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

_x = context.get_x_argument(as_dictionary=True)
_url = _x.get("db_url") or Settings().sync_database_url
config.set_main_option("sqlalchemy.url", _url.replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
