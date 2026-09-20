import logging
from typing import List, Dict

from praxis_ai_gateway.router import GatewayRouter, RoutingContext
from praxis_ai_gateway.base import LLMMessage

logger = logging.getLogger(__name__)

async def generate_prep_pack(match_results: Dict, blueprint: Dict, gateway: GatewayRouter) -> List[str]:
    """
    Pre-computes the top 15 likely interview questions based on the JD Blueprint
    and aggressively weighted toward the candidate's 'missing' gaps.
    This eliminates realtime blocking during the Practice Arena Phase 6.
    """
    
    missing_gaps = [m["requirement"] for m in match_results.get("breakdown", []) if m["match_level"] == "missing"]
    topics = blueprint.get("likely_topics", [])
    
    logger.info(f"Generating Prep Pack. Identified gaps: {missing_gaps}")
    
    # 1. We construct a targeted prompt
    prompt = f"""
    Generate exactly 15 concrete, specific interview questions for this role.
    Role Topics: {topics}
    Candidate Gaps (MUST PROBE THESE DEEPLY): {missing_gaps}
    
    Do not generate generic filler like 'What is your greatest weakness?'.
    Output ONLY a list of questions separated by newlines.
    """
    
    route_ctx = RoutingContext(user_id="system")
    
    messages = [
        LLMMessage(role="user", content=prompt)
    ]
    
    try:
        result = await gateway.route("deep_reasoning", route_ctx, "generate", messages=messages)
        text = result.result.text
        
        # Parse into a list
        questions = [q.strip().lstrip('0123456789.- ') for q in text.split('\n') if q.strip()]
        
        if not questions:
            raise ValueError("No questions generated")
            
        return questions[:15]
    except Exception as e:
        logger.error(f"Failed to generate prep pack: {e}")
        # Fallback without fabricating AI output
        return ["Could not generate interview prep questions at this time. Please try again later."]
