import psycopg2, os
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://praxis:dev_password@localhost:5432/praxis')
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()
cur.execute('SELECT auth.uid();')
print('auth.uid() no session:', cur.fetchone()[0])

cur.execute("SET request.jwt.claims TO '{\"sub\": \"11111111-1111-1111-1111-111111111111\"}';")
cur.execute('SELECT auth.uid();')
print('auth.uid() with session:', cur.fetchone()[0])

cur.execute('SET ROLE authenticated;')
print('SET ROLE authenticated succeeded')
