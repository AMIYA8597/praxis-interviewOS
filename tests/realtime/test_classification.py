import asyncio
import os
import sys
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'packages', 'ai-gateway'))

import pytest
from pydantic import BaseModel
from praxis_ai_gateway.classification import FastClassifier, QuestionClassification
from praxis_ai_gateway.router import GatewayRouter, RoutingContext, RoutedCall

class MockRedis:
    def __init__(self):
        self.store = {}
    async def get(self, key):
        return self.store.get(key)
    async def setex(self, key, ttl, value):
        self.store[key] = value

class MockRouter:
    async def route(self, task: str, context: RoutingContext, method_name: str, **kw):
        if "timeout" in kw.get("messages", [{}])[0].get("content", ""):
            # Simulate slow LLM
            await asyncio.sleep(0.5)
            
        messages = kw.get("messages", [])
        content = messages[0]["content"].lower()
        
        # Extract transcript portion to avoid matching the prompt template itself
        try:
            transcript = content.split("<transcript>")[1].split("</transcript>")[0].strip()
        except IndexError:
            transcript = content
            
        # Test Cases mapping
        if "okay, great" in transcript or "mm-hmm" in transcript or "i see" in transcript or "got it" in transcript or "sure, makes sense" in transcript:
            result = QuestionClassification(is_question=False, confidence=0.9, question_type="other", domain="Other", is_follow_up=False)
        elif "why not use x instead" in transcript or "why not random forest instead" in transcript:
            result = QuestionClassification(is_question=True, confidence=0.9, question_type="follow_up", domain="ML", is_follow_up=True)
        elif "how do i sort an array" in transcript:
            result = QuestionClassification(is_question=True, confidence=0.9, question_type="dsa", domain="General", is_follow_up=False)
        elif "tell me about your background" in content:
            result = QuestionClassification(is_question=True, confidence=0.9, question_type="behavioral", domain="General", is_follow_up=False)
        elif "explain kubernetes" in content:
            result = QuestionClassification(is_question=True, confidence=0.9, question_type="devops", domain="Cloud", is_follow_up=False)
        else:
            result = QuestionClassification(is_question=True, confidence=0.5, question_type="other", domain="Other", is_follow_up=False)
            
        return RoutedCall(provider_name="mock", model="mock", result=result)

async def test_classification_logic():
    router = MockRouter()
    redis = MockRedis()
    classifier = FastClassifier(router=router, redis_pool=redis)
    
    # Warmup
    await classifier.classify("warmup")
    
    print("\n--- 1. Testing Affirmation False-Question Filtering ---")
    affirmations = ["Okay, great", "Mm-hmm", "I see", "Sure, makes sense", "Got it"]
    for aff in affirmations:
        res = await classifier.classify(aff)
        assert res.is_question is False, f"Failed filtering affirmation: {aff}"
    print("All 5 affirmations correctly filtered as non-questions.")
    
    questions = ["How do I sort an array?", "Tell me about your background", "Explain Kubernetes", "What is an index?", "Why did it fail?"]
    for q in questions:
        res = await classifier.classify(q)
        print(f"DEBUG {q} -> {res}")
        assert res.is_question is True, f"Failed recognizing question: {q}"
    print("All 5 genuine questions correctly classified.")
    
    print("\n--- 2. Testing Follow-up Detection ---")
    res1 = await classifier.classify("why not random forest instead", prior_context="We used XGBoost for the project.")
    print(f"Follow up result: is_follow_up={res1.is_follow_up}, question_type={res1.question_type}, domain={res1.domain}")
    assert res1.is_follow_up is True
    
    res2 = await classifier.classify("How do I sort an array", prior_context="We used XGBoost for the project.")
    print(f"New question result: is_follow_up={res2.is_follow_up}, question_type={res2.question_type}, domain={res2.domain}")
    assert res2.is_follow_up is False
    
    print("\n--- 3. Testing Timeout Graceful Degradation ---")
    start = time.perf_counter()
    # "timeout" keyword causes MockRouter to sleep 0.5s
    res_timeout = await classifier.classify("timeout phrase")
    elapsed = (time.perf_counter() - start) * 1000
    print(f"Timeout fallback applied in {elapsed:.1f}ms (Budget: 120ms)")
    assert elapsed < 150, "Timeout breached latency budget!"
    assert res_timeout.is_question is True  # The heuristic treats arbitrary phrases as questions
    assert res_timeout.confidence == 0.5
    
    print("\n--- 4. Testing Redis Caching ---")
    start = time.perf_counter()
    # Cache hit
    res_cache = await classifier.classify("Tell me about your background")
    elapsed_cached = (time.perf_counter() - start) * 1000
    print(f"Cache hit latency: {elapsed_cached:.3f}ms")
    assert elapsed_cached < 10, "Cache retrieval should be instant"

if __name__ == "__main__":
    asyncio.run(test_classification_logic())
