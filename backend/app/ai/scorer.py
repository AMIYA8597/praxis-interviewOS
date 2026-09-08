class Scorer:
    """
    Answer scorer checking technical correctness and candidate-profile grounding.
    """
    def score_answer(self, question: str, candidate_answer: str, context: dict) -> dict:
        # In a real implementation, this uses a fast LLM call.
        # For MVP, returning a static structure.
        return {
            "score": 0.85,
            "correctness": 0.9,
            "grounding": 0.8,
            "feedback": "Good explanation of the tradeoff, but could use more specific metrics from your resume."
        }

class FollowUpPlanner:
    """
    Follow-up planner maintaining the interview state graph.
    """
    def plan_next_question(self, previous_question: str, candidate_answer: str, domain: str) -> str:
        # Simulated logic
        if domain == "ML":
            return "How would you handle it if the dataset was imbalanced?"
        elif domain == "CODING":
            return "What is the time complexity of that approach?"
        else:
            return "Can you elaborate on your specific role in that outcome?"
