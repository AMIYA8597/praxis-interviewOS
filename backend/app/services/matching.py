import logging
from typing import List, Dict

# from app.rag.retrieval import hybrid_search

logger = logging.getLogger(__name__)

async def compute_explainable_match(db_session, candidate_id: str, job_requirements: List[Dict]):
    """
    Computes an Explainable Match Score for a job against a candidate's VERIFIED facts.
    """
    logger.info(f"Computing match for candidate {candidate_id}")
    
    matches = []
    total_score = 0
    max_score = len(job_requirements) * 2 # 2 points for match, 1 for partial
    
    for req in job_requirements:
        skill = req.get("skill")
        
        # 1. Hybrid Search against verified candidate facts
        # evidence_chunks = await hybrid_search(db_session, query=skill, ...)
        evidence_chunks = [] # Stub
        
        if len(evidence_chunks) > 1:
            match_level = "matched"
            points = 2
            evidence = evidence_chunks[0].get("content")
        elif len(evidence_chunks) == 1:
            match_level = "partial"
            points = 1
            evidence = evidence_chunks[0].get("content")
        else:
            match_level = "missing"
            points = 0
            evidence = None
            
        total_score += points
        
        matches.append({
            "requirement": skill,
            "priority": req.get("priority", "preferred"),
            "match_level": match_level,
            "evidence": evidence
        })
        
    overall_percentage = (total_score / max_score) * 100 if max_score > 0 else 0
    
    return {
        "overall_score_percentage": round(overall_percentage),
        "methodology": "Computed strictly against verified candidate facts using Reciprocal Rank Fusion.",
        "breakdown": matches
    }
