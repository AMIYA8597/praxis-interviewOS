import os
import psycopg2
import pytest

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://praxis@localhost:5432/praxis")

@pytest.fixture
def db_conn():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    yield conn
    conn.close()

def test_fk_indexes_exist(db_conn):
    cur = db_conn.cursor()
    
    # Run EXPLAIN on candidate_projects filtering by candidate_id
    cur.execute("EXPLAIN SELECT * FROM candidate_projects WHERE candidate_id = '00000000-0000-0000-0000-000000000000';")
    plan = "\n".join([row[0] for row in cur.fetchall()])
    
    assert "Index" in plan or "Bitmap Heap Scan" in plan, f"Expected index scan for candidate_projects.candidate_id. Got:\n{plan}"

def test_vector_index_exists(db_conn):
    cur = db_conn.cursor()
    
    # We disable sequential scan to force the query planner to use an index if one exists
    cur.execute("SET enable_seqscan = off;")
    
    # Query ordering by cosine distance using a 384-dimensional zero vector
    vector_384 = "[" + ",".join(["0"] * 384) + "]"
    cur.execute(f"EXPLAIN SELECT id FROM document_chunks ORDER BY embedding <=> '{vector_384}'::vector LIMIT 5;")
    plan = "\n".join([row[0] for row in cur.fetchall()])
    
    # Wait, HNSW indexes show up as "Index Scan using idx_document_chunks_embedding"
    assert "Index Scan" in plan and "idx_document_chunks_embedding" in plan, f"Expected HNSW vector index scan. Got:\n{plan}"
    
def test_fts_index_exists(db_conn):
    cur = db_conn.cursor()
    
    cur.execute("SET enable_seqscan = off;")
    cur.execute("EXPLAIN SELECT id FROM document_chunks WHERE content_tsv @@ to_tsquery('english', 'machine & learning');")
    plan = "\n".join([row[0] for row in cur.fetchall()])
    
    # GIN indexes usually show up as "Bitmap Index Scan" or "Index Scan"
    assert "Index" in plan and "idx_document_chunks_content_tsv" in plan, f"Expected GIN text search index scan. Got:\n{plan}"
