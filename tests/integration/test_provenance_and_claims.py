import pytest
import os
import sys
from typing import List, Dict, Any
from pydantic import BaseModel

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'packages', 'ai-gateway'))

from realtime_agent.app.scoring.claims import (
    process_candidate_answer_claims, 
    _CLAIM_DB, 
    SessionClaim,
    ConsistencyResult,
    get_claim_provenance,
    check_consistency,
    check_grounding
)
from realtime_agent.app.scoring.models import ClaimExtractionResult, ExtractedClaim
from realtime_agent.app.interview.policy import InterviewSession, PolicyDecision

class MockLlmResult(BaseModel):
    result: Any

class MockTextResult(BaseModel):
    text: str

class MockRetriever:
    async def search(self, claim_text: str, candidate_id: str):
        # Return mock chunks based on claim
        if "XGBoost" in claim_text:
            return [{"id": "chunk_123", "project_id": "proj_1", "content": "Built recommendation engine with XGBoost."}]
        return []

class MockProvenanceProvider:
    def __init__(self):
        self.last_prompt = ""

    async def generate_structured(self, messages: List[Dict[str, Any]], schema: type[BaseModel], **kwargs):
        system_prompt = messages[0]["content"]
        user_prompt = messages[1]["content"] if len(messages) > 1 else ""
        self.last_prompt = str(messages)
        
        # 1. Claim Extraction
        if "You are an expert fact-extractor" in system_prompt:
            if "I used XGBoost for the recommendations, and the dataset had 100k rows" in user_prompt:
                return MockLlmResult(result=ClaimExtractionResult(claims=[
                    ExtractedClaim(claim_text="I used XGBoost for recommendations", is_verifiable=True),
                    ExtractedClaim(claim_text="The dataset had 100k rows", is_verifiable=True)
                ]))
            if "I processed 1 million rows" in user_prompt:
                return MockLlmResult(result=ClaimExtractionResult(claims=[
                    ExtractedClaim(claim_text="I processed 1 million rows", is_verifiable=True)
                ]))
            if "I built a UI in React" in user_prompt:
                return MockLlmResult(result=ClaimExtractionResult(claims=[
                    ExtractedClaim(claim_text="I built a UI in React", is_verifiable=True)
                ]))
            print(f"FAILED TO MATCH USER PROMPT: {user_prompt}")
            return MockLlmResult(result=ClaimExtractionResult(claims=[]))
            
        # 3. Consistency Engine
        if "Compare the new claim against the prior claims" in system_prompt:
            class LlmConsistencyResult(BaseModel):
                is_contradiction: bool
                contradicted_claim_id: str | None

            user_prompt = messages[1]["content"] if len(messages) > 1 else ""
            
            if "New Claim: I processed 1 million rows" in user_prompt and "100k rows" in user_prompt:
                # Find the ID of the 100k claim from the prior claims string in user_prompt
                prior_claims_str = user_prompt
                for line in prior_claims_str.split("\n"):
                    if "100k rows" in line and "ID: " in line:
                        id_str = line.split("ID: ")[1].split(" |")[0]
                        return MockLlmResult(result=LlmConsistencyResult(is_contradiction=True, contradicted_claim_id=id_str))
                return MockLlmResult(result=LlmConsistencyResult(is_contradiction=True, contradicted_claim_id="fake_id"))
                
            if "New Claim: I built a UI in React" in user_prompt:
                return MockLlmResult(result=LlmConsistencyResult(is_contradiction=False, contradicted_claim_id=None))
            
            return MockLlmResult(result=LlmConsistencyResult(is_contradiction=False, contradicted_claim_id=None))
                
        # 5. Policy Engine
        if "HEDGE UNVERIFIED FACTS" in system_prompt:
            if "Kubernetes" in user_prompt:
                return MockLlmResult(result=PolicyDecision(
                    is_clarifying_follow_up=False,
                    response_text="Given your background, you may have used Kubernetes for this. How would you handle it?"
                ))
            return MockLlmResult(result=PolicyDecision(
                is_clarifying_follow_up=False,
                response_text="Standard reply."
            ))
        print(f"MOCK FELL THROUGH! System prompt: {system_prompt}")
        return MockLlmResult(result=ClaimExtractionResult(claims=[]))

    async def generate(self, messages: List[Dict[str, Any]], **kwargs):
        system_prompt = messages[0]["content"]
        if "Does this retrieved context genuinely corroborate" in system_prompt:
            task = messages[2]["content"] if len(messages) > 2 else (messages[1]["content"] if len(messages) > 1 else "")
            if "XGBoost" in task:
                return MockLlmResult(result=MockTextResult(text="YES"))
            return MockLlmResult(result=MockTextResult(text="NO"))
        return MockLlmResult(result=MockTextResult(text="YES"))

class MockGatewayRouter:
    def __init__(self):
        self.provider = MockProvenanceProvider()
        
    def route(self, alias: str, context: Any):
        return self.provider

    async def route(self, alias: str, context: Any, method_name: str, **kwargs):
        if method_name == "generate_structured":
            return await self.provider.generate_structured(**kwargs)
        if method_name == "generate":
            return await self.provider.generate(**kwargs)
        raise NotImplementedError()

@pytest.fixture(autouse=True)
def clean_db():
    _CLAIM_DB.clear()
    yield

@pytest.mark.asyncio
async def test_claim_extraction_and_grounding():
    """
    Task 1 & Task 2: Claims are extracted as discrete items, and grounding uses retrieval check.
    """
    router = MockGatewayRouter()
    retriever = MockRetriever()
    
    ans = "I used XGBoost for the recommendations, and the dataset had 100k rows."
    claims = await process_candidate_answer_claims(ans, "Question?", "sess_1", "cand_1", router, None, mock_retriever=retriever)
    
    # 1. Discrete items
    assert len(claims) == 2
    
    # 2. Grounding Check
    xgboost_claim = next(c for c in claims if "XGBoost" in c.claim_text)
    rows_claim = next(c for c in claims if "100k" in c.claim_text)
    
    assert xgboost_claim.supported == True
    assert xgboost_claim.source_chunk_id == "chunk_123"
    
    assert rows_claim.supported == False
    assert rows_claim.source_chunk_id is None

@pytest.mark.asyncio
async def test_consistency_engine():
    """
    Task 3: Consistency checks flag real contradictions and ignore non-contradictions.
    """
    router = MockGatewayRouter()
    retriever = MockRetriever()
    
    # Base claim
    await process_candidate_answer_claims("I used XGBoost for the recommendations, and the dataset had 100k rows.", "Q1", "sess_1", "cand_1", router, None, retriever)
    base_claim = next(c for c in _CLAIM_DB if "100k" in c.claim_text)
    
    # Contradiction
    contradictory_claims = await process_candidate_answer_claims("Actually I processed 1 million rows.", "Q2", "sess_1", "cand_1", router, None, retriever)
    c_claim = contradictory_claims[0]
    
    assert c_claim.contradiction_of_claim_id == base_claim.id
    
    # Non-contradiction
    different_claims = await process_candidate_answer_claims("I built a UI in React.", "Q3", "sess_1", "cand_1", router, None, retriever)
    d_claim = different_claims[0]
    
    assert d_claim.contradiction_of_claim_id is None
    
    print("\n--- CONTRADICTION ENGINE OUTPUT ---")
    print(f"Base Claim: {base_claim.claim_text}")
    print(f"Contradicting Claim: {c_claim.claim_text} | Flagged ID: {c_claim.contradiction_of_claim_id}")
    print(f"Orthogonal Claim: {d_claim.claim_text} | Flagged ID: {d_claim.contradiction_of_claim_id}")

@pytest.mark.asyncio
async def test_structural_interviewer_safeguard():
    """
    Task 4: Structural test confirming contradiction data never reaches the live interviewer.
    """
    router = MockGatewayRouter()
    retriever = MockRetriever()
    
    # Load claims with contradictions into the DB
    await process_candidate_answer_claims("I used XGBoost for the recommendations, and the dataset had 100k rows.", "Q1", "sess_1", "cand_1", router, None, retriever)
    await process_candidate_answer_claims("Actually I processed 1 million rows.", "Q2", "sess_1", "cand_1", router, None, retriever)
    
    assert len([c for c in _CLAIM_DB if c.contradiction_of_claim_id is not None]) > 0
    
    # Generate interviewer response
    session = InterviewSession({"prep_pack": []}, {})
    await session.generate_next_turn("Random answer", router, None)
    
    # Assert _CLAIM_DB contents and "contradiction" are strictly excluded from the prompt
    prompt = router.provider.last_prompt
    assert "contradiction_of_claim_id" not in prompt
    assert "Actually I processed 1 million rows" not in prompt # Not explicitly injected as a claim list

@pytest.mark.asyncio
async def test_interviewer_hedging():
    """
    Task 5: Interviewer hedges instead of fabricating when referencing unverified facts.
    """
    router = MockGatewayRouter()
    session = InterviewSession({"prep_pack": []}, {})
    
    # Trigger the provider's mocked Kubernetes branch
    decision = await session.generate_next_turn("I like Kubernetes", router, None)
    
    assert "Given your background, you may have used" in decision.response_text or "I'd expect you might" in decision.response_text
    
@pytest.mark.asyncio
async def test_get_claim_provenance():
    """
    Task 6: get_claim_provenance returns correct UI-ready data.
    """
    router = MockGatewayRouter()
    retriever = MockRetriever()
    
    claims = await process_candidate_answer_claims("I used XGBoost for the recommendations, and the dataset had 100k rows.", "Q1", "sess_1", "cand_1", router, None, retriever)
    xgboost_claim = next(c for c in claims if "XGBoost" in c.claim_text)
    rows_claim = next(c for c in claims if "100k" in c.claim_text)
    
    prov_xgboost = get_claim_provenance(xgboost_claim.id)
    prov_rows = get_claim_provenance(rows_claim.id)
    
    assert prov_xgboost.supported == True
    assert prov_xgboost.source_chunk_id == "chunk_123"
    assert prov_xgboost.source_project_id == "proj_1"
    
    assert prov_rows.supported == False
    assert prov_rows.source_chunk_id is None
    assert prov_rows.source_project_id is None
    
    print("\n--- PROVENANCE DATA ---")
    print(f"Supported Claim: {prov_xgboost.model_dump_json(indent=2)}")
    print(f"Unsupported Claim: {prov_rows.model_dump_json(indent=2)}")
