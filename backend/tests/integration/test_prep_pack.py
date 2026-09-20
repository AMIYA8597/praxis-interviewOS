import pytest
from unittest.mock import AsyncMock
from backend.app.services.prep_pack import generate_prep_pack
from praxis_ai_gateway.base import LLMResponse
from praxis_ai_gateway.router import RoutedCall

@pytest.mark.asyncio
async def test_generate_prep_pack_varying_outputs():
    # 1. Setup mock gateway
    mock_gateway = AsyncMock()
    
    # We will simulate the LLM returning different questions based on the candidate's gaps.
    async def mock_route(alias, ctx, mode, messages, **kw):
        assert alias == "deep_reasoning"
        prompt = messages[0].content
        
        # Fake responses based on the prompt's context
        if "React" in prompt:
            resp = LLMResponse(text="1. Can you explain React hooks?\n2. What is the virtual DOM?", latency_ms=10.0, model="m", provider="m")
        else:
            resp = LLMResponse(text="1. How do you design a scalable microservice?\n2. What is eventual consistency?", latency_ms=10.0, model="m", provider="m")
            
        return RoutedCall(provider_name="mock", model="mock", result=resp)

    mock_gateway.route.side_effect = mock_route
    
    # 2. Call twice with different inputs
    match_results_1 = {"breakdown": [{"requirement": "React", "match_level": "missing"}]}
    blueprint_1 = {"likely_topics": ["Frontend"]}
    
    match_results_2 = {"breakdown": [{"requirement": "Microservices", "match_level": "missing"}]}
    blueprint_2 = {"likely_topics": ["Backend Architecture"]}
    
    output_1 = await generate_prep_pack(match_results_1, blueprint_1, mock_gateway)
    output_2 = await generate_prep_pack(match_results_2, blueprint_2, mock_gateway)
    
    print("\nOutput 1:", output_1)
    print("Output 2:", output_2)
    
    # 3. Assertions
    fabricated_string = "I see you don't have much listed for"
    
    assert fabricated_string not in output_1[0]
    assert fabricated_string not in output_2[0]
    assert output_1 != output_2
    assert "React" in output_1[0]
    assert "microservice" in output_2[0]
