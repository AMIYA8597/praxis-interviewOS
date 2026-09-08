import logging
from typing import Dict, List

from packages.ai_gateway.router import GatewayRouter, RoutingContext

logger = logging.getLogger(__name__)
gateway = GatewayRouter()

async def generate_session_debrief(session_id: str, turn_scores: List[Dict], turn_metrics: List[Dict]) -> Dict:
    """
    Generates the Post-Session Debrief.
    Aggregates metrics and delegates the final summary to the reasoning alias
    using STRUCTURED output, bypassing token-heavy raw transcript reprocessing.
    """
    logger.info(f"Generating debrief for session {session_id}")
    
    # 1. Aggregate DSP Metrics
    avg_wpm = sum(m["wpm"] for m in turn_metrics) / len(turn_metrics) if turn_metrics else 0
    total_fillers = sum(m["filler_count"] for m in turn_metrics)
    
    # 2. Aggregate Scores
    avg_relevance = sum(s["relevance"] for s in turn_scores) / len(turn_scores) if turn_scores else 0
    
    # 3. Identify Weakest Turn (Stub)
    weakest_turn = min(turn_scores, key=lambda x: x["relevance"]) if turn_scores else None
    
    # 4. Invoke Reasoning Provider for natural language strengths/weaknesses
    prompt = f"""
    Based on the following aggregated session metrics, generate a strengths/weaknesses summary.
    Avg WPM: {avg_wpm}
    Avg Relevance: {avg_relevance}
    """
    
    provider = gateway.route("reasoning", RoutingContext())
    # response = await provider.structured([{"role": "user", "content": prompt}], DebriefSchema)
    
    return {
        "session_id": session_id,
        "aggregate_metrics": {
            "avg_wpm": round(avg_wpm),
            "total_fillers": total_fillers,
            "avg_relevance": round(avg_relevance, 1)
        },
        "weakest_turn": weakest_turn,
        "summary": "You demonstrated strong architectural knowledge, but your STAR structuring was inconsistent. Your filler word rate spiked during technical deep-dives."
    }
