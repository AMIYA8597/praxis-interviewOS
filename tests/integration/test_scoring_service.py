import pytest
import asyncio
import os
import sys
import time
from typing import List, Dict, Any
from pydantic import BaseModel

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'packages', 'ai-gateway'))

from realtime_agent.app.scoring.service import trigger_background_scoring, calculate_grounding_score, score_answer_async
from realtime_agent.app.scoring.models import AnswerScore, StarCompleteness, ClaimExtractionResult, ExtractedClaim

class MockLlmResult(BaseModel):
    result: Any

class MockTextResult(BaseModel):
    text: str

class MockScoringProvider:
    def __init__(self, slow_scoring: bool = False):
        self.slow_scoring = slow_scoring

    async def generate_structured(self, messages: List[Dict[str, Any]], schema: type[BaseModel], **kwargs):
        if self.slow_scoring:
            await asyncio.sleep(0.5)
            
        system_prompt = messages[0]["content"]
        user_prompt = messages[1]["content"]
        
        # Are we doing claim extraction?
        if "Extract key verifiable factual claims" in system_prompt:
            if "I designed the rate limiter using Redis" in user_prompt:
                return MockLlmResult(result=ClaimExtractionResult(claims=[
                    ExtractedClaim(claim_text="Designed rate limiter using Redis", is_verifiable=True)
                ]))
            elif "I increased conversion by 50% overnight without looking at the code" in user_prompt:
                return MockLlmResult(result=ClaimExtractionResult(claims=[
                    ExtractedClaim(claim_text="Increased conversion by 50%", is_verifiable=True)
                ]))
            return MockLlmResult(result=ClaimExtractionResult(claims=[]))
            
        # Are we scoring?
        # Task 4: STAR Completeness
        if "Situation, Task, Action, Result" in system_prompt:
            if "I noticed the query was slow" in user_prompt and "I added an index" in user_prompt and "it became 10x faster" in user_prompt:
                # Full STAR
                star = StarCompleteness(situation=True, task=True, action=True, result=True)
                return MockLlmResult(result=schema(
                    relevance=1.0, correctness=1.0, structure=1.0, specificity=1.0, conciseness=1.0, 
                    star_completeness=star, rationale="Excellent STAR answer."
                ))
            elif "The query was slow, so I added an index" in user_prompt and "became" not in user_prompt:
                # Missing Result
                star = StarCompleteness(situation=True, task=True, action=True, result=False)
                return MockLlmResult(result=schema(
                    relevance=0.8, correctness=1.0, structure=0.6, specificity=0.7, conciseness=0.9, 
                    star_completeness=star, rationale="Missing result."
                ))
            elif "I added an index to the timestamp column" in user_prompt and "slow because it was scanning" not in user_prompt and "The query was slow" not in user_prompt:
                # Only Action
                star = StarCompleteness(situation=False, task=False, action=True, result=False)
                return MockLlmResult(result=schema(
                    relevance=0.5, correctness=1.0, structure=0.2, specificity=0.4, conciseness=0.5, 
                    star_completeness=star, rationale="Only action provided."
                ))
                
        # Task 6: Calibration Pass (5 answers)
        if "Explain how a hash map works" in user_prompt:
            if "It's an array with a hash function" in user_prompt: # Excellent
                return MockLlmResult(result=schema(relevance=1.0, correctness=1.0, structure=1.0, specificity=0.9, conciseness=1.0, rationale="Excellent"))
            elif "It maps keys to values" in user_prompt: # Good
                return MockLlmResult(result=schema(relevance=1.0, correctness=0.8, structure=0.8, specificity=0.6, conciseness=0.9, rationale="Good"))
            elif "It's a data structure" in user_prompt: # Mediocre
                return MockLlmResult(result=schema(relevance=0.8, correctness=0.5, structure=0.5, specificity=0.3, conciseness=0.8, rationale="Mediocre"))
            elif "It's like a list" in user_prompt: # Poor
                return MockLlmResult(result=schema(relevance=0.4, correctness=0.2, structure=0.4, specificity=0.1, conciseness=0.8, rationale="Poor"))
            elif "I don't know" in user_prompt: # Terrible
                return MockLlmResult(result=schema(relevance=0.0, correctness=0.0, structure=0.0, specificity=0.0, conciseness=0.0, rationale="Terrible"))
                
        # Default fallback
        return MockLlmResult(result=schema(
            relevance=0.5, correctness=0.5, structure=0.5, specificity=0.5, conciseness=0.5, rationale="Fallback"
        ))

    async def generate(self, messages: List[Dict[str, Any]], **kwargs):
        system_prompt = messages[0]["content"]
        if "Is the following claim supported by the verified context?" in system_prompt:
            user_prompt = messages[1]["content"]
            if "Redis" in user_prompt and "Redis" in user_prompt.split("Claim to verify:")[0]:
                return MockTextResult(text="YES")
            return MockTextResult(text="NO")
        return MockTextResult(text="YES")

class MockScoringRouter:
    def __init__(self, slow_scoring: bool = False):
        self.provider = MockScoringProvider(slow_scoring)
        
    def route(self, alias: str, context: Any):
        return self.provider
        
    async def route(self, alias: str, context: Any, method_name: str, **kwargs):
        if method_name == "generate_structured":
            return await self.provider.generate_structured(**kwargs)
        if method_name == "generate":
            return await self.provider.generate(**kwargs)
        raise NotImplementedError()

class DummyStateMachine:
    def __init__(self):
        self.last_score = None

@pytest.mark.asyncio
async def test_non_blocking_scoring():
    """
    Task 2: Assert the next interviewer question is generated BEFORE a deliberately-slowed scoring call completes.
    """
    router = MockScoringRouter(slow_scoring=True)
    state_machine = DummyStateMachine()
    
    start_time = time.time()
    
    # Fire and forget scoring
    task = trigger_background_scoring("Q1", "A1", False, "Context", router, None, state_machine=state_machine)
    
    # Ensure it returns immediately (much faster than the 0.5s sleep in the mock)
    elapsed_after_trigger = time.time() - start_time
    assert elapsed_after_trigger < 0.1, "Scoring blocked the main thread!"
    
    # State machine proceeds to NEXT question
    assert state_machine.last_score is None, "Score was calculated synchronously!"
    
    # Await the task manually to clean up and verify
    await task
    assert state_machine.last_score is not None

@pytest.mark.asyncio
async def test_grounding_score_extraction():
    """
    Task 3: Grounding score calculation via hybrid retrieval check.
    """
    router = MockScoringRouter()
    
    # 1. Supported claim
    ans1 = "I designed the rate limiter using Redis."
    ctx1 = "Built caching layer using Redis."
    score1 = await calculate_grounding_score(ans1, ctx1, router, None)
    assert score1 == 1.0
    
    # 2. Unsupported claim
    ans2 = "I increased conversion by 50% overnight without looking at the code."
    ctx2 = "Backend engineer"
    score2 = await calculate_grounding_score(ans2, ctx2, router, None)
    assert score2 == 0.0

@pytest.mark.asyncio
async def test_star_completeness():
    """
    Task 4: STAR completeness for behavioral answers.
    """
    router = MockScoringRouter()
    q = "Tell me about a time you optimized a slow query."
    
    # 1. Full STAR
    ans_full = "I noticed the query was slow because it was scanning the whole table. My task was to fix it. I added an index to the timestamp column. As a result, it became 10x faster."
    score_full = await score_answer_async(q, ans_full, True, "", router, None)
    assert score_full.star_completeness.situation == True
    assert score_full.star_completeness.result == True
    
    # 2. Missing Result
    ans_no_res = "The query was slow, so I added an index to the timestamp column."
    score_no_res = await score_answer_async(q, ans_no_res, True, "", router, None)
    assert score_no_res.star_completeness.situation == True
    assert score_no_res.star_completeness.action == True
    assert score_no_res.star_completeness.result == False
    
    # 3. Just Action
    ans_action = "I added an index to the timestamp column."
    score_action = await score_answer_async(q, ans_action, True, "", router, None)
    assert score_action.star_completeness.situation == False
    assert score_action.star_completeness.task == False
    assert score_action.star_completeness.action == True
    assert score_action.star_completeness.result == False

@pytest.mark.asyncio
async def test_calibration_sanity_check():
    """
    Task 6: Scoring Accuracy Sanity Check (5 synthetic answers)
    """
    router = MockScoringRouter()
    q = "Explain how a hash map works."
    
    answers = [
        "It's an array with a hash function mapping keys to indices, handling collisions via chaining.", # Excellent
        "It maps keys to values using a hash function.", # Good
        "It's a data structure for storing key-value pairs.", # Mediocre
        "It's like a list where you put things.", # Poor
        "I don't know." # Terrible
    ]
    
    scores = []
    print("\n--- 5-ANSWER CALIBRATION SCORES ---")
    for ans in answers:
        score = await score_answer_async(q, ans, False, "", router, None)
        scores.append(score)
        print(f"Answer: '{ans}'")
        print(f"Score: {score.overall:.2f} (Rationale: {score.rationale})")
        
    # Check strict ordering
    assert scores[0].overall > scores[1].overall
    assert scores[1].overall > scores[2].overall
    assert scores[2].overall > scores[3].overall
    assert scores[3].overall > scores[4].overall
