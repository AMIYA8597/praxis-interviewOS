import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from .base import Base

class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), unique=True, nullable=False) # Maps to auth.users in Supabase
    name = Column(String(255))
    email = Column(String(255), unique=True)
    summary = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE"))
    filename = Column(String(255))
    raw_text = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_id = Column(UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=True)
    content = Column(Text, nullable=False)
    metadata_ = Column("metadata", JSON, default={})
    embedding = Column(Vector(384)) # Using BAAI/bge-small-en-v1.5 which has 384 dimensions
    # In Postgres this would be generated always as (to_tsvector('english', content)) stored
    content_tsv = Column(Text, nullable=True) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# ==========================================
# PHASE 5: CONTEXT GRAPH RELATIONAL SCHEMA
# ==========================================

class Job(Base):
    __tablename__ = "jobs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255))
    company = Column(String(255))
    raw_jd = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class JDRequirement(Base):
    __tablename__ = "jd_requirements"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"))
    requirement_text = Column(Text)

class Skill(Base):
    __tablename__ = "skills"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True)

class CandidateSkill(Base):
    __tablename__ = "candidate_skills"
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), primary_key=True)
    skill_id = Column(UUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True)

# Expanded candidate_projects
class Project(Base):
    __tablename__ = "projects"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE"))
    title = Column(String(255))
    summary = Column(Text)
    problem = Column(Text)
    motivation = Column(Text)
    users_served = Column(String(255))
    architecture = Column(Text)
    tech_stack = Column(JSON) # Storing text[] as JSON
    datasets = Column(Text)
    data_pipeline = Column(Text)
    models_used = Column(JSON) # Storing text[] as JSON
    training_approach = Column(Text)
    evaluation_method = Column(Text)
    metrics = Column(JSON)
    deployment = Column(Text)
    infra = Column(Text)
    challenges = Column(Text)
    failure_cases = Column(Text)
    tradeoffs = Column(Text)
    improvements = Column(Text)
    business_impact = Column(Text)
    personal_contribution = Column(Text)
    team_size = Column(String(50))
    duration_months = Column(Numeric)
    github_url = Column(String(255))
    demo_url = Column(String(255))
    confidence = Column(Numeric)
    verified_by_user = Column(Boolean, nullable=False, default=False)

class ResumeClaim(Base):
    __tablename__ = "resume_claims"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resume_id = Column(UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"))
    claim_text = Column(Text)
    claim_type = Column(String(50)) # skill|metric|role|project|education|certification
    page = Column(Integer)
    char_start = Column(Integer)
    char_end = Column(Integer)
    extraction_confidence = Column(Numeric)
    verified_by_user = Column(Boolean, default=False)
    verified_at = Column(DateTime(timezone=True))

class Metric(Base):
    __tablename__ = "metrics"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    metric_text = Column(String(255))

class Story(Base):
    __tablename__ = "stories"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    star_format_text = Column(Text)

class Experience(Base):
    __tablename__ = "experiences"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE"))
    company = Column(String(255))
    role = Column(String(255))
    start_date = Column(DateTime)
    end_date = Column(DateTime, nullable=True)

class InterviewSession(Base):
    __tablename__ = "interview_sessions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE"))
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    mode = Column(String(50))
    interview_type = Column(String(50))
    difficulty = Column(String(50))
    language = Column(String(50))
    persona = Column(JSON)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_s = Column(Integer)
    turn_count = Column(Integer, default=0)
    stt_provider = Column(String(50))
    llm_provider = Column(String(50))
    tts_provider = Column(String(50))
    fallback_count = Column(Integer, default=0)
    status = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SessionTurn(Base):
    __tablename__ = "session_turns"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("interview_sessions.id", ondelete="CASCADE"))
    turn_index = Column(Integer)
    speaker = Column(String(50)) # interviewer|candidate
    parent_turn_id = Column(UUID(as_uuid=True), ForeignKey("session_turns.id", ondelete="SET NULL"), nullable=True)
    text_content = Column(Text)
    started_at = Column(DateTime(timezone=True))
    ended_at = Column(DateTime(timezone=True))
    duration_ms = Column(Integer)

class TurnMetric(Base):
    __tablename__ = "turn_metrics"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    turn_id = Column(UUID(as_uuid=True), ForeignKey("session_turns.id", ondelete="CASCADE"))
    word_count = Column(Integer)
    duration_ms = Column(Integer)
    wpm = Column(Numeric)
    filler_count = Column(Integer)
    filler_rate = Column(Numeric)
    filler_breakdown = Column(JSON)
    pause_count = Column(Integer)
    longest_pause_ms = Column(Integer)
    pause_ratio = Column(Numeric)
    pitch_variance = Column(Numeric)
    energy_variance = Column(Numeric)
    hedge_count = Column(Integer)
    sentence_count = Column(Integer)
    avg_sentence_len = Column(Numeric)
    time_to_first_word_ms = Column(Integer)

class TurnScore(Base):
    __tablename__ = "turn_scores"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    turn_id = Column(UUID(as_uuid=True), ForeignKey("session_turns.id", ondelete="CASCADE"))
    rubric_version = Column(String(50))
    relevance = Column(Numeric)
    correctness = Column(Numeric)
    structure = Column(Numeric)
    grounding = Column(Numeric)
    specificity = Column(Numeric)
    conciseness = Column(Numeric)
    star_completeness = Column(JSON)
    overall = Column(Numeric)
    rationale = Column(Text)
    model_used = Column(String(100))
    scored_at = Column(DateTime(timezone=True), server_default=func.now())

class SessionClaim(Base):
    __tablename__ = "session_claims"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("interview_sessions.id", ondelete="CASCADE"))
    turn_id = Column(UUID(as_uuid=True), ForeignKey("session_turns.id", ondelete="CASCADE"))
    claim_text = Column(Text)
    supported = Column(Boolean)
    source_chunk_id = Column(UUID(as_uuid=True), ForeignKey("document_chunks.id", ondelete="SET NULL"), nullable=True)
    source_project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    confidence = Column(Numeric)
    contradiction_of_claim_id = Column(UUID(as_uuid=True), ForeignKey("session_claims.id", ondelete="SET NULL"), nullable=True)

class StudyItem(Base):
    __tablename__ = "study_items"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidate_profiles.id", ondelete="CASCADE"))
    topic = Column(String(255))
    source = Column(String(100)) # weak_answer|missed_concept|jd_gap|manual
    source_turn_id = Column(UUID(as_uuid=True), ForeignKey("session_turns.id", ondelete="SET NULL"), nullable=True)
    prompt_text = Column(Text)
    reference_answer = Column(Text)
    difficulty = Column(String(50))
    ease_factor = Column(Numeric, default=2.5)
    interval_days = Column(Integer, default=1)
    next_review_at = Column(DateTime(timezone=True))

class StudyReview(Base):
    __tablename__ = "study_reviews"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id = Column(UUID(as_uuid=True), ForeignKey("study_items.id", ondelete="CASCADE"))
    reviewed_at = Column(DateTime(timezone=True), server_default=func.now())
    quality = Column(Integer) # 0-5
    new_interval_days = Column(Integer)
    new_ease_factor = Column(Numeric)

class ProviderHealth(Base):
    __tablename__ = "provider_health"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String(100))
    capability = Column(String(100))
    state = Column(String(50)) # closed|open|half_open
    last_success_at = Column(DateTime(timezone=True))
    last_failure_at = Column(DateTime(timezone=True))
    consecutive_failures = Column(Integer, default=0)
    latency_p50_ms = Column(Integer)
    latency_p95_ms = Column(Integer)
    latency_p99_ms = Column(Integer)
    error_rate = Column(Numeric)
    rate_limited_until = Column(DateTime(timezone=True))
    checked_at = Column(DateTime(timezone=True), server_default=func.now())

class UsageEvent(Base):
    __tablename__ = "usage_events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False) # Auth user
    session_id = Column(UUID(as_uuid=True), ForeignKey("interview_sessions.id", ondelete="SET NULL"), nullable=True)
    provider = Column(String(100))
    model = Column(String(100))
    capability = Column(String(100))
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    audio_seconds = Column(Numeric, default=0)
    image_count = Column(Integer, default=0)
    request_count = Column(Integer, default=1)
    estimated_cost_usd = Column(Numeric, default=0)
    was_free_tier = Column(Boolean, default=True)
    latency_ms = Column(Integer)
    fell_back_from = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
