import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class InterviewPolicyEngine:
    """
    Manages the session state machine, context compression, and question selection.
    """
    def __init__(self, prep_pack: List[str], candidate_context: Dict):
        # 1. Warm pre-fetched context
        self.prep_pack = prep_pack
        self.candidate_context = candidate_context
        self.current_question_idx = 0
        self.rolling_summary = "Session started."
        
        logger.info(f"Policy Engine initialized with {len(prep_pack)} prep pack questions.")

    async def evaluate_next_turn(self, candidate_answer: str, gateway_router, routing_ctx) -> str:
        """
        Executes on Turn End to decide the next action: Follow-up or Next Question.
        """
        logger.info("Evaluating next turn policy...")
        
        # 1. Compress context if needed (Stub)
        self.rolling_summary += f"\nCandidate discussed: {candidate_answer[:50]}..."
        
        # 2. Decide if follow-up is warranted (Using fast_classify alias)
        provider = gateway_router.route("fast_classify", routing_ctx)
        prompt = f"Does this answer require a probing follow-up? Answer YES or NO.\nAnswer: {candidate_answer}"
        # response = await provider.generate(...)
        # is_followup = "YES" in response.text
        is_followup = len(candidate_answer.split()) > 20 # Stub heuristic
        
        if is_followup:
            logger.info("Decision: Generating contextual follow-up.")
            # In a real run, invoke 'reasoning' provider with RAG context
            return "Can you elaborate on exactly what your personal contribution was to that architecture?"
            
        else:
            logger.info("Decision: Moving to next Prep Pack question.")
            if self.current_question_idx < len(self.prep_pack):
                q = self.prep_pack[self.current_question_idx]
                self.current_question_idx += 1
                return q
            else:
                return "That concludes the technical portion of our interview. Do you have any questions for me?"
