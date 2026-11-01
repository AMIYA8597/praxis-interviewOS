import pytest
from unittest.mock import AsyncMock, MagicMock
from realtime_agent.app.scoring.claims import check_grounding
from realtime_agent.app.scoring.models import ClaimClassification, ClaimGroundingResult


@pytest.mark.asyncio
async def test_5tier_claim_supported():
    mock_gateway = MagicMock()
    mock_gateway.db = MagicMock()
    mock_gateway.db.bind = MagicMock()

    # Mock hybrid search returns a chunk
    mock_chunk = MagicMock()
    mock_chunk.id = "chunk-101"
    mock_chunk.content = "Designed and deployed a Redis caching cluster that reduced 95th percentile latency by 45%."
    mock_chunk.project_id = "proj-1"

    routing_ctx = MagicMock()
    routing_ctx.user_id = "u1"
    routing_ctx.session_id = "s1"

    async def mock_hybrid(query, candidate_id, db, k=3, boost_verified=True):
        return [mock_chunk]

    mock_result = MagicMock()
    mock_result.result = ClaimGroundingResult(
        classification=ClaimClassification.SUPPORTED,
        confidence=0.95,
        source_chunk_id="chunk-101",
        source_excerpt="reduced 95th percentile latency by 45%",
    )
    mock_gateway.route = AsyncMock(return_value=mock_result)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("praxis_ai_gateway.retrieval.hybrid_search", mock_hybrid)
        claim = await check_grounding("I built a Redis cluster that decreased p95 latency.", "cand-1", mock_gateway, routing_ctx)

    assert claim.supported is True
    assert claim.classification == "SUPPORTED"
    assert claim.source_chunk_id == "chunk-101"
    assert claim.source_excerpt == "reduced 95th percentile latency by 45%"
    assert claim.confidence == 0.95


@pytest.mark.asyncio
async def test_5tier_claim_contradicted():
    mock_gateway = MagicMock()
    mock_gateway.db = MagicMock()
    mock_gateway.db.bind = MagicMock()

    mock_chunk = MagicMock()
    mock_chunk.id = "chunk-102"
    mock_chunk.content = "Single-node Postgres database without any caching or sharding layer."

    routing_ctx = MagicMock()
    async def mock_hybrid(query, candidate_id, db, k=3, boost_verified=True):
        return [mock_chunk]

    mock_result = MagicMock()
    mock_result.result = ClaimGroundingResult(
        classification=ClaimClassification.CONTRADICTED,
        confidence=0.98,
        source_chunk_id="chunk-102",
        source_excerpt="Single-node Postgres database without any caching",
        reasoning="Candidate claims to have used Redis sharding, but project document states single-node Postgres with no caching.",
    )
    mock_gateway.route = AsyncMock(return_value=mock_result)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("praxis_ai_gateway.retrieval.hybrid_search", mock_hybrid)
        claim = await check_grounding("I scaled the system using a distributed Redis sharding layer.", "cand-1", mock_gateway, routing_ctx)

    assert claim.supported is False
    assert claim.classification == "CONTRADICTED"
    assert claim.source_chunk_id == "chunk-102"


@pytest.mark.asyncio
async def test_5tier_claim_unsupported_when_no_context():
    mock_gateway = MagicMock()
    mock_gateway.db = MagicMock()
    mock_gateway.db.bind = MagicMock()

    routing_ctx = MagicMock()
    async def mock_hybrid(query, candidate_id, db, k=3, boost_verified=True):
        return []  # No corroborating chunks found

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("praxis_ai_gateway.retrieval.hybrid_search", mock_hybrid)
        claim = await check_grounding("I invented PyTorch from scratch in 2012.", "cand-1", mock_gateway, routing_ctx)

    # Must never silently become SUPPORTED
    assert claim.supported is False
    assert claim.classification == "UNSUPPORTED"
    assert claim.source_chunk_id is None
