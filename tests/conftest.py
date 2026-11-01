import os
os.environ["ENABLE_RATE_LIMIT"] = "false"
import os
import sys
import psycopg2
import pytest

# Add root so we can import packages if needed, though they are installed in env.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from packages.config.settings import settings


@pytest.fixture
def db_conn():
    url = settings.DATABASE_URL
    if not url.startswith("postgresql") and not url.startswith("postgres://"):
        pytest.skip(f"db_conn requires a PostgreSQL URL; got {url!r}")
    try:
        conn = psycopg2.connect(url)
        conn.autocommit = True
    except psycopg2.OperationalError as e:
        pytest.skip(f"PostgreSQL connection failed: {e}")
    yield conn
    conn.close()
