import pytest
import psycopg2
import os
import sys

# Add root so we can import packages if needed, though they are installed in env.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from packages.config.settings import settings

@pytest.fixture
def db_conn():
    url = settings.DATABASE_URL
    if not url.startswith("postgresql") and not url.startswith("postgres://"):
        pytest.skip(f"db_conn requires a PostgreSQL URL; got {url!r}")
    conn = psycopg2.connect(url)
    conn.autocommit = True
    yield conn
    conn.close()
