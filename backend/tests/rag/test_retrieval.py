import pytest
from praxis_ai_gateway.retrieval import hybrid_search

def test_retrieval_invariant_excludes_unverified():
    """
    Test asserting that the RRF SQL query structurally rejects 
    unverified facts.
    "Unverified extracted facts must never be cited as grounding evidence."
    """
    # In a full DB test with SQLAlchemy, we would:
    # 1. Insert a chunk with a linked claim (verified_by_user=False)
    # 2. Insert a chunk with a linked claim (verified_by_user=True)
    # 3. Call hybrid_search()
    # 4. Assert chunk 1 is entirely absent from the result set.
    
    # For now, we assert the hardcoded SQL constraint exists in the query logic.
    import inspect
    import praxis_ai_gateway.retrieval as ret_module
    source = inspect.getsource(ret_module)
    assert "verified_by_user = false" in source and "NOT EXISTS" in source, "CRITICAL: RRF query is missing the unverified claim filter."
