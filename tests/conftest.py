import pytest
import psycopg2
import os
import sys

# Add root so we can import packages if needed, though they are installed in env.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from packages.config.settings import settings

@pytest.fixture
def db_conn():
    conn = psycopg2.connect(settings.DATABASE_URL)
    conn.autocommit = True
    yield conn
    conn.close()
