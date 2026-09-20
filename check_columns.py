import psycopg2, os
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://praxis:dev_password@localhost:5432/praxis')
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()
cur.execute("SELECT table_name, column_name, data_type FROM information_schema.columns WHERE column_name IN ('processing_status', 'status');")
print('cols:', cur.fetchall())
