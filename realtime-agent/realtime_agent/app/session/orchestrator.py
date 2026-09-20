import logging
from typing import Callable, Any

from realtime_agent.app.interview.policy import InterviewSession
from realtime_agent.app.interview.generation import SessionGenerationManager
from realtime_agent.app.session.manager import SessionManager
from realtime_agent.app.audio.tts import PiperTTSAdapter
from praxis_ai_gateway.router import GatewayRouter, RoutingContext
from realtime_agent.app.scoring.service import score_answer_async
from realtime_agent.app.scoring.claims import process_candidate_answer_claims
from realtime_agent.app.session.state_machine import SessionState
from realtime_agent.app.protocol import Envelope


logger = logging.getLogger(__name__)

class SessionOrchestrator:
    def __init__(
        self,
        session: InterviewSession,
        generation_manager: SessionGenerationManager,
        session_manager: SessionManager,
        gateway: GatewayRouter,
        routing_ctx: RoutingContext,
        tts: PiperTTSAdapter,
        enqueue_event: Callable[[Any], None]
    ):
        self.session = session
        self.generation_manager = generation_manager
        self.session_manager = session_manager
        self.gateway = gateway
        self.routing_ctx = routing_ctx
        self.tts = tts
        self.enqueue_event = enqueue_event
        
        from realtime_agent.app.interview.turn_detection import TurnEndDetector
        self.turn_detector = TurnEndDetector(router=self.gateway)
        from praxis_ai_gateway.classification import FastClassifier
        self.classifier = FastClassifier(router=self.gateway)
        
        from realtime_agent.app.coaching.accumulator import CoachingMetricsAccumulator
        self.coaching = CoachingMetricsAccumulator(
            session_id=self.session_manager.session_id,
            enqueue_event_cb=lambda env, critical=False: self.enqueue_event(env, critical=critical)
        )

    async def start_candidate_turn(self):
        await self.session_manager.transition(SessionState.CANDIDATE_TURN)
        self.coaching.start_turn()

    def handle_vad_event(self, evt: str):
        self.coaching.register_vad_event(evt)
        
    def handle_transcript_update(self, text: str):
        self.coaching.update_text(text)
        
    async def handle_vad_silence(self, vad_silence_ms: int, partial_transcript: str) -> None:
        """Called by the WebSocket handler (Phase 2.12) to evaluate turn completeness."""
        decision = await self.turn_detector.evaluate(vad_silence_ms, partial_transcript)
        if decision.is_turn_end:
            await self.on_candidate_turn_end(final_text=partial_transcript)
    async def begin_interviewer_turn(self, is_follow_up: bool = False, parent_turn_id: str = None) -> None:
        # Task 1: Transition state
        await self.session_manager.transition(SessionState.INTERVIEWER_TURN)
        
        # Task 2: Consult policy
        candidate_answer = getattr(self, "current_candidate_answer", "")
        decision = await self.session.generate_next_turn(
            candidate_answer=candidate_answer,
            gateway_router=self.gateway,
            routing_ctx=self.routing_ctx,
            is_follow_up=is_follow_up,
            parent_turn_id=parent_turn_id
        )
        
        # Reset current answer for next turn
        self.current_candidate_answer = ""
        self.last_interviewer_question = decision.response_text
        
        # Task 5: Enqueue text event
        text_evt = Envelope(
            type="interviewer.text",
            session_id=self.session_manager.session_id, # Will be properly routed by transport
            sequence=0,
            payload={"text": decision.response_text}
        )
        self.enqueue_event(text_evt, critical=True)
        
        # Task 3: Start generation
        import uuid
        turn_id = str(uuid.uuid4())
        
        from sqlalchemy import text
        query_turn = text("""
            INSERT INTO session_turns (id, session_id, speaker, text_content, started_at, ended_at)
            VALUES (:id, :sid, 'interviewer', :text, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """)
        await self.session_manager.db.execute(query_turn, {
            "id": turn_id,
            "sid": self.session_manager.session_id,
            "text": decision.response_text
        })
        await self.session_manager.db.commit()
        
        gen_ctx = self.generation_manager.start_generation(turn_id=turn_id)
        
        # Task 4: Stream through TTS
        async def text_iterator():
            yield decision.response_text
            
        try:
            async for audio_chunk in self.tts.synthesize_streaming(text_iterator(), gen_ctx.token):
                if gen_ctx.token.is_cancelled():
                    break
                self.enqueue_event(audio_chunk, critical=False)
        except Exception as e:
            logger.error(f"TTS streaming failed: {e}")
            
        if gen_ctx.token.is_cancelled():
            return
            
        # Transition out
        await self.session_manager.transition(SessionState.AWAITING_ANSWER)

    async def on_candidate_turn_end(self, final_text: str = "") -> None:
        import asyncio
        import uuid
        from sqlalchemy import text
        
        session_id = self.session_manager.session_id
        db = self.session_manager.db
        candidate_id = self.session.candidate_profile.get("id", "unknown_candidate")
        
        # 1. State machine transition -> TURN_END
        await self.session_manager.transition(SessionState.TURN_END)
        self.coaching.end_turn()
        self.current_candidate_answer = getattr(self, "current_candidate_answer", "") + " " + final_text
        self.current_candidate_answer = self.current_candidate_answer.strip()
        
                # Classify turn
        last_question = getattr(self, "last_interviewer_question", "")
        classification = await self.classifier.classify(self.current_candidate_answer, last_question)
        if not classification.is_question:
            import logging
            logging.getLogger(__name__).info("Candidate utterance was a short affirmation. Blocking scoring.")
            await self.session_manager.transition(SessionState.AWAITING_ANSWER)
            return

        # Transition -> SCORING
        await self.session_manager.transition(SessionState.SCORING)
        
        turn_id = str(uuid.uuid4())
        
        # Insert turn into DB so foreign keys work
        query_turn = text("""
            INSERT INTO session_turns (id, session_id, speaker, text_content, started_at, ended_at)
            VALUES (:id, :sid, 'candidate', :text, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """)
        await db.execute(query_turn, {
            "id": turn_id,
            "sid": session_id,
            "text": self.current_candidate_answer
        })
        await db.commit()
        
        # 3. Score the turn
        last_question = getattr(self, "last_interviewer_question", "")
        
        score_task = asyncio.create_task(score_answer_async(
            question=last_question,
            candidate_answer=self.current_candidate_answer,
            is_behavioral=False, 
            verified_context="", 
            gateway_router=self.gateway,
            routing_ctx=self.routing_ctx
        ))
        
        # 4. Extract claims
        claims_task = asyncio.create_task(process_candidate_answer_claims(
            answer_text=self.current_candidate_answer,
            question_context=last_question,
            session_id=session_id,
            turn_id=turn_id,
            candidate_id=candidate_id,
            gateway_router=self.gateway,
            routing_ctx=self.routing_ctx
        ))
        
        score, claims = await asyncio.gather(score_task, claims_task)
        
        # Persist score
        query_score = text("""
            INSERT INTO turn_scores (id, turn_id, relevance, correctness, structure, grounding, specificity, conciseness, overall, rationale)
            VALUES (:id, :tid, :rel, :cor, :struc, :grnd, :spec, :conc, :overall, :rat)
        """)
        await db.execute(query_score, {
            "id": str(uuid.uuid4()),
            "tid": turn_id,
            "rel": score.relevance,
            "cor": score.correctness,
            "struc": score.structure,
            "grnd": score.grounding,
            "spec": score.specificity,
            "conc": score.conciseness,
            "overall": score.overall,
            "rat": score.rationale
        })
        await db.commit()
        
        # 5. Planning Next
        await self.session_manager.transition(SessionState.PLANNING_NEXT)
        
        if len(self.session.memory.turns) > self.session.memory.turn_count_threshold:
            await self.session.memory.compress(self.gateway, self.routing_ctx)
            
        # 6. Ready -> Decide next step
        await self.session_manager.transition(SessionState.READY)
        if self.session.current_question_idx >= len(self.session.prep_pack):
            await self.end_session_and_debrief()
        else:
            await self.begin_interviewer_turn()

    async def end_session_and_debrief(self) -> None:
        from realtime_agent.app.interview.debrief import generate_debrief
        import json
        import uuid
        from sqlalchemy import text
        
        # 1. Transition to DEBRIEF
        await self.session_manager.transition(SessionState.DEBRIEF)
        
        try:
            # 2. Call generate_debrief
            debrief_result = await generate_debrief(
                self.session_manager.session_id, 
                self.session_manager.db, 
                self.gateway, 
                self.routing_ctx
            )
            
            # 3. Insert into session_debriefs
            await self.session_manager.db.execute(text("""
                INSERT INTO session_debriefs (id, session_id, headline_metrics, strengths, weaknesses, flagged_claims, jd_coverage, generated_at)
                VALUES (:id, :session_id, :headline_metrics, :strengths, :weaknesses, :flagged_claims, :jd_coverage, CURRENT_TIMESTAMP)
            """), {
                "id": str(uuid.uuid4()),
                "session_id": self.session_manager.session_id,
                "headline_metrics": json.dumps(debrief_result.headline_metrics.model_dump()),
                "strengths": json.dumps(debrief_result.strengths),
                "weaknesses": json.dumps(debrief_result.weaknesses),
                "flagged_claims": json.dumps(debrief_result.flagged_claims),
                "jd_coverage": json.dumps(debrief_result.jd_coverage)
            })
            await self.session_manager.db.commit()
        except Exception as e:
            import logging
            logging.error(f"Error in end_session_and_debrief: {e}")
        
        # 4. Enqueue debrief.ready
        self.enqueue_event(Envelope(
            type="debrief.ready",
            session_id=self.session_manager.session_id,
            sequence=0,
            payload={"status": "ready"}
        ), critical=True)
        
        # 5. Transition to STOPPED
        await self.session_manager.transition(SessionState.STOPPED)




