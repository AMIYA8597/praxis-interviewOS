import logging
import json
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

from praxis_ai_gateway.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)

class Turn(BaseModel):
    id: str
    role: str
    text: str
    parent_turn_id: Optional[str] = None
    is_follow_up: bool = False

class PolicyDecision(BaseModel):
    is_clarifying_follow_up: bool = Field(description="True if the prior answer had ambiguity worth a genuine follow-up. False if moving to the next prepared topic.")
    response_text: str = Field(description="The question or statement to be spoken by the interviewer.")
    
class SessionMemory:
    def __init__(self):
        self.turns: List[Turn] = []
        self.compressed_summary: str = ""
        self.turn_count_threshold: int = 6

    def add_turn(self, turn: Turn):
        self.turns.append(turn)

    async def compress(self, gateway_router, routing_ctx) -> str:
        """
        Task 4 - Conversation Memory Compression.
        Once the session exceeds the configurable turn-count threshold, summarize older turns
        into a compact running summary, replacing them. Keep the most recent 2-3 turns.
        """
        if len(self.turns) <= self.turn_count_threshold:
            return self.compressed_summary

        # Keep last 3 turns
        turns_to_compress = self.turns[:-3]
        self.turns = self.turns[-3:]

        # Call reasoning alias to summarize
        builder = PromptBuilder()
        builder.add_system("You are an expert technical recruiter summarizing an interview.")
        builder.add_task("Summarize the following older interview turns compactly: topics covered, claims made, technologies mentioned.")
        if self.compressed_summary:
            builder.add_trusted_context("prior_summary", self.compressed_summary)
            
        transcript = "\n".join([f"{t.role}: {t.text}" for t in turns_to_compress])
        builder.add_untrusted("older_turns", "session_transcript", transcript)

        try:
            call_result = await gateway_router.route(
                "fast_classify",
                routing_ctx,
                "generate",
                messages=builder.build()
            )
            self.compressed_summary = call_result.result.text
        except Exception as e:
            logger.error(f"Failed to compress memory: {e}")
            # Fallback compression
            self.compressed_summary += f"\n[Auto-compressed {len(turns_to_compress)} turns]"

        return self.compressed_summary

def build_followup_context(current_turn: Turn, parent_turn: Turn) -> str:
    """
    Task 3 - The Follow-Up Graph.
    Constructs a compact summary of the PARENT turn's question+answer.
    """
    return f"Parent Question: {parent_turn.text}\nCandidate Answer: {current_turn.text}"

class InterviewSession:
    def __init__(self, jd_blueprint: Dict, candidate_profile: Dict, difficulty: str = "standard", interview_type: str = "technical"):
        self.jd_blueprint = jd_blueprint
        self.candidate_profile = candidate_profile
        self.difficulty = difficulty
        self.interview_type = interview_type
        
        self.memory = SessionMemory()
        self.prep_pack: List[str] = []
        self.current_question_idx = 0
        self.cached_context: str = ""
        self.is_warmed_up = False
        
        # Load the core interviewer system prompt
        with open("prompts/interviewer/system_v1.md", "r") as f:
            self.system_prompt = f.read()

    def warm_up(self):
        """
        Task 2 - Session Warm-Up: Pre-fetching Context Once.
        Called ONCE at session start.
        """
        if self.is_warmed_up:
            return
            
        logger.info("Warming up Interview Session context...")
        
        # Candidate Context
        summary = self.candidate_profile.get("summary", "")
        skills = ", ".join(self.candidate_profile.get("verified_skills", []))
        
        # Only verified projects
        projects = self.candidate_profile.get("projects", [])
        verified_projects = [p for p in projects if p.get("verified_by_user", False)]
        proj_str = "\n".join([f"- {p['name']}: {p['description']}" for p in verified_projects])
        
        # JD Context
        self.prep_pack = self.jd_blueprint.get("prep_pack", [])
        
        self.cached_context = (
            f"Candidate Summary: {summary}\n"
            f"Verified Skills: {skills}\n"
            f"Verified Projects:\n{proj_str}\n"
            f"Interview Setup: {self.interview_type} interview, {self.difficulty} difficulty."
        )
        self.is_warmed_up = True

    async def generate_next_turn(self, candidate_answer: str, gateway_router, routing_ctx, is_follow_up: bool = False, parent_turn_id: str = None) -> PolicyDecision:
        """
        Evaluates the candidate's answer and generates the next interviewer question.
        """
        # Ensure warmed up
        if not self.is_warmed_up:
            self.warm_up()
            
        # Add candidate turn
        cand_turn = Turn(id=f"c_{len(self.memory.turns)}", role="Candidate", text=candidate_answer, parent_turn_id=parent_turn_id, is_follow_up=is_follow_up)
        self.memory.add_turn(cand_turn)
        
        # Compress memory if needed
        await self.memory.compress(gateway_router, routing_ctx)
        
        # Build prompt
        builder = PromptBuilder()
        builder.add_system(self.system_prompt)
        
        # Add cached context
        builder.add_trusted_context("interview_context", self.cached_context)
        
        # Task 5: Difficulty and Interview-Type Modulation
        # Instruct the model to respect these params when generating the question
        topic_guidance = (
            f"The interview type is {self.interview_type} and the difficulty is {self.difficulty}. "
            "Ensure the tone, strictness, and depth of technical probing match this difficulty perfectly."
        )
        if self.difficulty == "warmup":
            topic_guidance += " Keep questions foundational, friendly, and non-adversarial."
        elif self.difficulty == "stress":
            topic_guidance += " Be rigorous, adversarial, and push the candidate to defend their technical choices deeply."
            
        builder.add_trusted_context("topic_guidance", topic_guidance)
        
        if self.memory.compressed_summary:
            builder.add_trusted_context("prior_session_summary", self.memory.compressed_summary)
            
        # Task 3: Follow-Up Graph context
        if is_follow_up and parent_turn_id:
            parent_turn = next((t for t in self.memory.turns if t.id == parent_turn_id), None)
            if parent_turn:
                followup_ctx = build_followup_context(cand_turn, parent_turn)
                builder.add_trusted_context("follow_up_focus", followup_ctx)
                
        # Recent turns
        recent_transcript = "\n".join([f"{t.role}: {t.text}" for t in self.memory.turns[-3:]])
        builder.add_untrusted("recent_transcript", "session_transcript", recent_transcript)
        
        # Provide the next prep pack question as an option if we want to transition
        next_q = self.prep_pack[self.current_question_idx] if self.current_question_idx < len(self.prep_pack) else "None left. Generate a new question fitting the topic."
        builder.add_trusted_context("next_prepared_question", next_q)
        
        builder.add_output_schema(PolicyDecision)
        
        # Route to reasoning alias for policy logic
        try:
            call_result = await gateway_router.route(
                "deep_reasoning",
                routing_ctx,
                "structured",
                messages=builder.build(),
                schema=PolicyDecision
            )
            decision = call_result.result
        except Exception as e:
            logger.error(f"Policy generation failed: {e}")
            # Fallback
            decision = PolicyDecision(is_clarifying_follow_up=False, response_text="Could you elaborate a bit more on that?")
            
        # If transitioning, increment idx
        if not decision.is_clarifying_follow_up and self.current_question_idx < len(self.prep_pack):
            self.current_question_idx += 1
            
        # Add our generated turn to memory
        int_turn = Turn(id=f"i_{len(self.memory.turns)}", role="Interviewer", text=decision.response_text)
        self.memory.add_turn(int_turn)
        
        return decision
