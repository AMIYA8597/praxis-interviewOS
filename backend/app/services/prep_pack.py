import logging
from typing import List, Dict

from packages.ai_gateway.router import GatewayRouter, RoutingContext

logger = logging.getLogger(__name__)
gateway = GatewayRouter()

async def generate_prep_pack(match_results: Dict, blueprint: Dict) -> List[str]:
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
    """
    
    provider = gateway.route("reasoning", RoutingContext())
    
    # result = await provider.generate([{"role": "user", "content": prompt}])
    # questions = parse_result(result.text)
    
    # Stub
    questions = [
        f"I see you don't have much listed for {gap}. How would you approach a problem requiring it?"
        for gap in missing_gaps
    ]
    
    while len(questions) < 15:
        questions.append("Can you describe a challenging architecture decision you made?")
        
    return questions[:15]
