import pytest
from unittest.mock import AsyncMock, patch
from backend.app.services.matching import compute_explainable_match
from praxis_ai_gateway.retrieval import ScoredChunk

@pytest.mark.asyncio
async def test_compute_explainable_match():
    candidate_id = "fake-candidate-id"
    job_requirements = [
        {"skill": "Python"},
        {"skill": "Kubernetes"},
        {"skill": "Rust"}
    ]
    
    # We mock hybrid_search to return different chunks based on query
    async def mock_hybrid_search(query, candidate_id, db, k, boost_verified):
        if query == "Python":
            return [
                ScoredChunk(id="c1", document_id="d1", content="Advanced Python", score=1.5, rank=1),
                ScoredChunk(id="c2", document_id="d1", content="Python scripts", score=1.1, rank=2)
            ]
        elif query == "Kubernetes":
            return [
                ScoredChunk(id="c3", document_id="d1", content="Deployed on K8s", score=1.2, rank=1)
            ]
        else:
            return []
            
    with patch("backend.app.services.matching.hybrid_search", side_effect=mock_hybrid_search):
        result = await compute_explainable_match(AsyncMock(), candidate_id, job_requirements)
        
        # Max score is 3 * 2 = 6 points
        # Python -> >1 chunk -> 2 points ("matched")
        # Kubernetes -> 1 chunk -> 1 point ("partial")
        # Rust -> 0 chunks -> 0 points ("missing")
        # Total points = 3. Percentage = (3/6) * 100 = 50%
        
        assert result["overall_score_percentage"] == 50
        assert len(result["breakdown"]) == 3
        
        python_match = next(r for r in result["breakdown"] if r["requirement"] == "Python")
        assert python_match["match_level"] == "matched"
        
        k8s_match = next(r for r in result["breakdown"] if r["requirement"] == "Kubernetes")
        assert k8s_match["match_level"] == "partial"
        
        rust_match = next(r for r in result["breakdown"] if r["requirement"] == "Rust")
        assert rust_match["match_level"] == "missing"
