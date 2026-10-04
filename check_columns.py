import psycopg2
from packages.config.settings import settings
DATABASE_URL = settings.DATABASE_URL
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()
cur.execute("SELECT table_name, column_name, data_type FROM information_schema.columns WHERE column_name IN ('processing_status', 'status');")
print('cols:', cur.fetchall())
