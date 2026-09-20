import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from realtime_agent.app.scoring.claims import process_candidate_answer_claims
from praxis_ai_gateway.base import LLMResponse
from praxis_ai_gateway.router import RoutedCall

@pytest.mark.asyncio
async def test_claims_engine_end_to_end():
    mock_router = AsyncMock()
    # mock_router.db.execute for inserting claims and retrieving prior claims
    
    # Let's mock the internal methods directly since the prompt asks for
    # mocking LLM, but we can just mock the external dependencies of the pipeline.
    
    # We will mock gateway_router.route to return different responses based on the task (classification vs extraction vs entailment)
    async def mock_route(task_name, routing_ctx, method_name, messages, schema=None, **kwargs):
        if schema and schema.__name__ == "ClaimExtractionResult":
            # 1. Extraction
            class MockExtraction:
                class MockClaim:
                    def __init__(self, t):
                        self.claim_text = t
                        self.is_verifiable = True
                claims = [MockClaim("claim 1"), MockClaim("claim 2")]
            return RoutedCall(provider_name="test", model="test", result=MockExtraction())
            
        elif schema and schema.__name__ == "LlmConsistencyResult":
            # 2. Consistency
            prompt_text = str(messages)
            if "claim 2" in prompt_text:
                # Contradicts!
                class MockConsistency:
                    is_contradiction = True
                    contradicted_claim_id = "prior-claim-id"
                return RoutedCall(provider_name="test", model="test", result=MockConsistency())
            else:
                class MockConsistency:
                    is_contradiction = False
                    contradicted_claim_id = None
                return RoutedCall(provider_name="test", model="test", result=MockConsistency())
                
        else:
            # 3. Entailment
            prompt_text = str(messages)
            if "claim 1" in prompt_text:
                return RoutedCall(provider_name="test", model="test", result=LLMResponse(text="YES", latency_ms=10, model="test", provider="test"))
            else:
                return RoutedCall(provider_name="test", model="test", result=LLMResponse(text="NO", latency_ms=10, model="test", provider="test"))

    mock_router.route.side_effect = mock_route
    
    # Mock DB execute for prior claims
    async def mock_db_execute(query, params=None):
        mock_res = MagicMock()
        if "SELECT id, claim_text FROM session_claims" in str(query):
            # Return prior claims
            class MockRow:
                def __init__(self, id, text):
                    self.id = id
                    self.claim_text = text
            mock_res.fetchall.return_value = [MockRow("prior-claim-id", "prior claim")]
        return mock_res
        
    mock_router.db.execute = mock_db_execute
    mock_router.db.bind = AsyncMock() # For hybrid_search
    
    # Mock hybrid search
    async def mock_hybrid_search(query, candidate_id, db, k, boost_verified):
        if "claim 1" in query:
            class MockChunk:
                def __init__(self):
                    self.id = "chunk-1"
                    self.content = "supportive chunk"
                    self.project_id = "proj-1"
            return [MockChunk()]
        return []
        
    with patch("praxis_ai_gateway.retrieval.hybrid_search", side_effect=mock_hybrid_search):
        claims = await process_candidate_answer_claims("answer", "question", "session-1", "turn-1", "cand-1", mock_router, None)
        
        assert len(claims) == 2
        
        c1 = next(c for c in claims if c.claim_text == "claim 1")
        assert c1.supported is True
        assert c1.source_chunk_id == "chunk-1"
        assert c1.contradiction_of_claim_id is None
        
        c2 = next(c for c in claims if c.claim_text == "claim 2")
        assert c2.supported is False
        assert c2.source_chunk_id is None
        assert c2.contradiction_of_claim_id == "prior-claim-id"
