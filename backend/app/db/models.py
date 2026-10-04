"""
SQLAlchemy ORM models for the PRAXIS data model.

SOURCE OF TRUTH
---------------
The canonical DDL lives in `supabase/migrations/*.sql` (applied by
`scripts/migrate.py`, CI and Supabase) and is mirrored by the Alembic chain
(`backend/alembic`, revision 004_reconcile_schema). These models describe
the same tables/columns so services can use typed queries; they do not
carry CHECK constraints, RLS or triggers (those stay in the migrations).

Portability: Postgres-only types use `.with_variant(..., "sqlite")` so unit
tests can build a throwaway schema with `Base.metadata.create_all`.
"""
import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CHAR,
    JSON,
    BigInteger,
    Boolean,
    TypeDecorator,
    Column,
    Date,
    DateTime,
    FetchedValue,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR, UUID

from .base import Base

EMBEDDING_DIM = 384  # BAAI/bge-small-en-v1.5

class GUID(TypeDecorator):
    """Native `uuid` on Postgres; canonical hyphenated text elsewhere (SQLite tests),
    so raw-SQL fixtures and ORM queries agree on the stored representation."""

    impl = CHAR(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None or dialect.name == "postgresql":
            return value
        return str(value if isinstance(value, uuid.UUID) else uuid.UUID(str(value)))

    def process_result_value(self, value, dialect):
        if value is None or isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


JSONType = JSONB().with_variant(JSON(), "sqlite")
TextArray = ARRAY(Text).with_variant(JSON(), "sqlite")
UUIDType = GUID()


def _pk():
    # The DB-side default (gen_random_uuid()) lives in the migrations; declaring it
    # here would break create_all on SQLite. The ORM always supplies uuid4.
    return Column(UUIDType, primary_key=True, default=uuid.uuid4)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _created_at():
    # Python-side default keeps full precision on every backend (stable keyset
    # pagination); server_default still covers raw-SQL inserts.
    return Column(DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now())


def _updated_at():
    return Column(DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now(), onupdate=_utcnow)


# ════════════════════════════════════════════════════════════════════
# Identity & profile
# ════════════════════════════════════════════════════════════════════

class Profile(Base):
    __tablename__ = "profiles"
    id = Column(UUIDType, primary_key=True)  # == auth.users.id
    is_banned = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    paid_provider_acknowledged = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    created_at = _created_at()
    updated_at = _updated_at()


class Candidate(Base):
    __tablename__ = "candidates"
    id = _pk()
    profile_id = Column(UUIDType, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, unique=True)
    full_name = Column(Text, nullable=False)
    headline = Column(Text)
    location = Column(Text)
    years_experience = Column(Numeric)
    target_roles = Column(TextArray)
    preferred_language = Column(Text)
    speaking_style = Column(JSONType)
    onboarding_step = Column(Text)
    onboarding_completed_at = Column(DateTime(timezone=True))
    created_at = _created_at()
    updated_at = _updated_at()


# Backwards-compatible alias for code that imported the old name.
CandidateProfile = Candidate


class UserSettings(Base):
    __tablename__ = "user_settings"
    id = _pk()
    candidate_id = Column(UUIDType, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    theme = Column(Text)
    latency_mode = Column(Text)
    cost_mode = Column(Text)
    answer_style_default = Column(Text)
    shortcuts = Column(JSONType)
    data_retention_days = Column(Integer, default=30)
    created_at = _created_at()
    updated_at = _updated_at()


class AdminUser(Base):
    __tablename__ = "admin_users"
    id = _pk()
    profile_id = Column(UUIDType, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, unique=True)
    role = Column(Text)
    created_at = _created_at()
    updated_at = _updated_at()


# ════════════════════════════════════════════════════════════════════
# Candidate brain
# ════════════════════════════════════════════════════════════════════

class Skill(Base):
    __tablename__ = "skills"
    id = _pk()
    name = Column(Text, nullable=False, unique=True)
    category = Column(Text)
    created_at = _created_at()
    updated_at = _updated_at()


class CandidateSkill(Base):
    __tablename__ = "candidate_skills"
    __table_args__ = (UniqueConstraint("candidate_id", "skill_id"),)
    id = _pk()
    candidate_id = Column(UUIDType, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = Column(UUIDType, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)
    proficiency = Column(Text)
    years_used = Column(Numeric)
    evidence_source = Column(Text)
    created_at = _created_at()
    updated_at = _updated_at()


class CandidateExperience(Base):
    __tablename__ = "candidate_experiences"
    id = _pk()
    candidate_id = Column(UUIDType, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    company = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)
    description = Column(Text)
    achievements = Column(TextArray)
    created_at = _created_at()
    updated_at = _updated_at()


# Backwards-compatible alias.
Experience = CandidateExperience


class CandidateProject(Base):
    __tablename__ = "candidate_projects"
    id = _pk()
    candidate_id = Column(UUIDType, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    experience_id = Column(UUIDType, ForeignKey("candidate_experiences.id", ondelete="CASCADE"))
    name = Column(Text, nullable=False)
    summary = Column(Text)
    problem = Column(Text)
    motivation = Column(Text)
    users_served = Column(Text)
    architecture = Column(Text)
    tech_stack = Column(TextArray)
    datasets = Column(Text)
    data_pipeline = Column(Text)
    models_used = Column(TextArray)
    training_approach = Column(Text)
    evaluation_method = Column(Text)
    metrics = Column(JSONType)
    deployment = Column(Text)
    infra = Column(Text)
    challenges = Column(Text)
    failure_cases = Column(Text)
    tradeoffs = Column(Text)
    improvements = Column(Text)
    business_impact = Column(Text)
    personal_contribution = Column(Text)
    team_size = Column(Integer)
    duration_months = Column(Integer)
    github_url = Column(Text)
    demo_url = Column(Text)
    confidence = Column(Numeric)
    verified_by_user = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    created_at = _created_at()
    updated_at = _updated_at()


# Backwards-compatible alias.
Project = CandidateProject


class ProjectMetric(Base):
    __tablename__ = "project_metrics"
    id = _pk()
    project_id = Column(UUIDType, ForeignKey("candidate_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    metric_name = Column(Text, nullable=False)
    metric_value = Column(Text, nullable=False)
    unit = Column(Text)
    is_estimate = Column(Boolean)
    created_at = _created_at()
    updated_at = _updated_at()


class Story(Base):
    __tablename__ = "stories"
    id = _pk()
    candidate_id = Column(UUIDType, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(UUIDType, ForeignKey("candidate_projects.id", ondelete="SET NULL"))
    experience_id = Column(UUIDType, ForeignKey("candidate_experiences.id", ondelete="SET NULL"))
    title = Column(Text, nullable=False)
    situation = Column(Text)
    task = Column(Text)
    action = Column(Text)
    result = Column(Text)
    competency_tags = Column(TextArray)
    created_at = _created_at()
    updated_at = _updated_at()


# ════════════════════════════════════════════════════════════════════
# Documents & retrieval
# ════════════════════════════════════════════════════════════════════

class Document(Base):
    __tablename__ = "documents"
    id = _pk()
    candidate_id = Column(UUIDType, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = Column(Text)  # resume | other
    original_filename = Column(Text)
    storage_path = Column(Text)
    mime_type = Column(Text)
    size_bytes = Column(BigInteger)
    processing_status = Column(Text)  # uploading|parsing|embedding|ready|failed
    error_message = Column(Text)
    created_at = _created_at()
    updated_at = _updated_at()


class Resume(Base):
    __tablename__ = "resumes"
    id = _pk()
    candidate_id = Column(UUIDType, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(UUIDType, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    is_primary = Column(Boolean, default=False)
    created_at = _created_at()
    updated_at = _updated_at()


class ResumeVersion(Base):
    __tablename__ = "resume_versions"
    id = _pk()
    resume_id = Column(UUIDType, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer)
    label = Column(Text)
    generated_for_job_id = Column(UUIDType, ForeignKey("jobs.id", ondelete="SET NULL"))
    created_at = _created_at()
    updated_at = _updated_at()


class ResumeClaim(Base):
    __tablename__ = "resume_claims"
    id = _pk()
    resume_version_id = Column(UUIDType, ForeignKey("resume_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    claim_text = Column(Text, nullable=False)
    claim_type = Column(Text)  # skill|metric|role|project|education|certification
    page = Column(Integer)
    char_start = Column(Integer)
    char_end = Column(Integer)
    extraction_confidence = Column(Numeric)
    verified_by_user = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    verified_at = Column(DateTime(timezone=True))
    created_at = _created_at()
    updated_at = _updated_at()


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (UniqueConstraint("document_id", "chunk_index"),)
    id = _pk()
    document_id = Column(UUIDType, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    token_count = Column(Integer)
    # vector(384) when pgvector is installed (text fallback otherwise, see scripts/migrate.py)
    embedding = Column(Vector(EMBEDDING_DIM).with_variant(Text(), "sqlite"))
    embedding_model = Column(Text, nullable=False)
    embedding_version = Column(Text, nullable=False)
    metadata_ = Column("metadata", JSONType, default=dict)
    # GENERATED ALWAYS AS (to_tsvector('english', content)) STORED — DB-managed.
    content_tsv = Column(TSVECTOR().with_variant(Text(), "sqlite"), server_default=FetchedValue())
    created_at = _created_at()
    updated_at = _updated_at()


# ════════════════════════════════════════════════════════════════════
# Job brain
# ════════════════════════════════════════════════════════════════════

class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (Index("idx_jobs_candidate_created", "candidate_id", "created_at"),)
    id = _pk()
    candidate_id = Column(UUIDType, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    company_name = Column(Text, nullable=False)
    role_title = Column(Text, nullable=False)
    raw_jd_text = Column(Text)
    seniority_signal = Column(Text)
    processing_status = Column(Text, nullable=False, default="pending", server_default=text("'pending'"))
    error_message = Column(Text)
    created_at = _created_at()
    updated_at = _updated_at()


class JobBlueprint(Base):
    __tablename__ = "job_blueprints"
    id = _pk()
    job_id = Column(UUIDType, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, unique=True)
    top_skills = Column(JSONType)
    likely_topics = Column(TextArray)
    summary = Column(Text)
    prep_pack = Column(JSONType)
    created_at = _created_at()
    updated_at = _updated_at()


class JobRequirement(Base):
    __tablename__ = "job_requirements"
    id = _pk()
    job_blueprint_id = Column(UUIDType, ForeignKey("job_blueprints.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_text = Column(Text, nullable=False)
    category = Column(Text)
    priority = Column(Text)  # required | preferred
    evidence_quote = Column(Text)
    created_at = _created_at()
    updated_at = _updated_at()


class JobMatch(Base):
    __tablename__ = "job_matches"
    id = _pk()
    job_id = Column(UUIDType, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, unique=True)
    candidate_id = Column(UUIDType, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    overall_score = Column(Numeric)
    methodology_version = Column(Text)
    breakdown = Column(JSONType)
    created_at = _created_at()
    updated_at = _updated_at()


# ════════════════════════════════════════════════════════════════════
# Practice sessions
# ════════════════════════════════════════════════════════════════════

class PracticeSession(Base):
    __tablename__ = "practice_sessions"
    __table_args__ = (Index("idx_practice_sessions_candidate_created", "candidate_id", "created_at"),)
    id = _pk()
    candidate_id = Column(UUIDType, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(UUIDType, ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    mode = Column(Text)  # mock_interview|drill|freeform|debrief
    interview_type = Column(Text)  # behavioral|technical|system_design|mixed|screening
    difficulty = Column(Text)  # warmup|standard|senior|stress
    language = Column(Text)
    persona = Column(JSONType)
    focus_area = Column(Text)
    started_at = Column(DateTime(timezone=True))
    ended_at = Column(DateTime(timezone=True))
    duration_s = Column(Integer)
    turn_count = Column(Integer, default=0)
    stt_provider = Column(Text)
    llm_provider = Column(Text)
    tts_provider = Column(Text)
    fallback_count = Column(Integer, default=0)
    status = Column(Text)  # pending|active|completed|abandoned|failed
    created_at = _created_at()
    updated_at = _updated_at()


class SessionTurn(Base):
    __tablename__ = "session_turns"
    __table_args__ = (UniqueConstraint("session_id", "turn_index"),)
    id = _pk()
    session_id = Column(UUIDType, ForeignKey("practice_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    turn_index = Column(Integer, nullable=False)
    speaker = Column(Text)  # interviewer|candidate
    question_id = Column(UUIDType)
    parent_turn_id = Column(UUIDType, ForeignKey("session_turns.id", ondelete="CASCADE"), index=True)
    text = Column(Text)
    started_at = Column(DateTime(timezone=True))
    ended_at = Column(DateTime(timezone=True))
    duration_ms = Column(Integer)
    created_at = _created_at()
    updated_at = _updated_at()


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"
    id = _pk()
    session_id = Column(UUIDType, ForeignKey("practice_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    turn_id = Column(UUIDType, ForeignKey("session_turns.id", ondelete="CASCADE"), nullable=False, index=True)
    is_interim = Column(Boolean, nullable=False, default=False)
    text = Column(Text)
    start_ms = Column(Integer)
    end_ms = Column(Integer)
    confidence = Column(Numeric)
    language = Column(Text)
    created_at = _created_at()
    updated_at = _updated_at()


class TurnMetric(Base):
    __tablename__ = "turn_metrics"
    id = _pk()
    turn_id = Column(UUIDType, ForeignKey("session_turns.id", ondelete="CASCADE"), nullable=False, unique=True)
    word_count = Column(Integer)
    duration_ms = Column(Integer)
    wpm = Column(Numeric)
    filler_count = Column(Integer)
    filler_rate = Column(Numeric)
    filler_breakdown = Column(JSONType)
    pause_count = Column(Integer)
    longest_pause_ms = Column(Integer)
    pause_ratio = Column(Numeric)
    pitch_variance = Column(Numeric)
    energy_variance = Column(Numeric)
    hedge_count = Column(Integer)
    sentence_count = Column(Integer)
    avg_sentence_len = Column(Numeric)
    time_to_first_word_ms = Column(Integer)
    created_at = _created_at()
    updated_at = _updated_at()


class TurnScore(Base):
    __tablename__ = "turn_scores"
    id = _pk()
    turn_id = Column(UUIDType, ForeignKey("session_turns.id", ondelete="CASCADE"), nullable=False, unique=True)
    rubric_version = Column(Text)
    relevance = Column(Numeric)
    correctness = Column(Numeric)
    structure = Column(Numeric)
    grounding = Column(Numeric)
    specificity = Column(Numeric)
    conciseness = Column(Numeric)
    star_completeness = Column(JSONType)
    overall = Column(Numeric)
    rationale = Column(Text)
    model_used = Column(Text)
    scored_at = Column(DateTime(timezone=True))
    created_at = _created_at()
    updated_at = _updated_at()


class SessionClaim(Base):
    __tablename__ = "session_claims"
    id = _pk()
    session_id = Column(UUIDType, ForeignKey("practice_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    turn_id = Column(UUIDType, ForeignKey("session_turns.id", ondelete="CASCADE"), nullable=False, index=True)
    claim_text = Column(Text, nullable=False)
    supported = Column(Boolean)
    source_chunk_id = Column(UUIDType, ForeignKey("document_chunks.id", ondelete="SET NULL"))
    source_project_id = Column(UUIDType, ForeignKey("candidate_projects.id", ondelete="SET NULL"))
    confidence = Column(Numeric)
    contradiction_of_claim_id = Column(UUIDType, ForeignKey("session_claims.id", ondelete="SET NULL"))
    created_at = _created_at()
    updated_at = _updated_at()


class SessionStateLog(Base):
    __tablename__ = "session_state_log"
    id = _pk()
    session_id = Column(UUIDType, ForeignKey("practice_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    from_state = Column(Text)
    to_state = Column(Text, nullable=False)
    reason = Column(Text)
    occurred_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at = _created_at()
    updated_at = _updated_at()


class SessionDebrief(Base):
    __tablename__ = "session_debriefs"
    id = _pk()
    session_id = Column(UUIDType, ForeignKey("practice_sessions.id", ondelete="CASCADE"), nullable=False, unique=True)
    headline_metrics = Column(JSONType)
    strengths = Column(TextArray)
    weaknesses = Column(TextArray)
    flagged_claims = Column(JSONType)
    jd_coverage = Column(JSONType)
    generated_at = Column(DateTime(timezone=True))
    created_at = _created_at()
    updated_at = _updated_at()


# ════════════════════════════════════════════════════════════════════
# Study loop
# ════════════════════════════════════════════════════════════════════

class ScreenshotTask(Base):
    __tablename__ = "screenshot_tasks"
    id = _pk()
    candidate_id = Column(UUIDType, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    storage_path = Column(Text, nullable=False)
    status = Column(Text)
    created_at = _created_at()
    updated_at = _updated_at()


class SolverResult(Base):
    __tablename__ = "solver_results"
    id = _pk()
    screenshot_task_id = Column(UUIDType, ForeignKey("screenshot_tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    solution = Column(Text)
    confidence = Column(Numeric)
    screenshot_type = Column(Text)
    hints = Column(JSONType)
    created_at = _created_at()
    updated_at = _updated_at()


class StudyItem(Base):
    __tablename__ = "study_items"
    __table_args__ = (Index("idx_study_items_candidate_next_review", "candidate_id", "next_review_at"),)
    id = _pk()
    candidate_id = Column(UUIDType, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    topic = Column(Text, nullable=False)
    source = Column(Text)  # weak_answer|missed_concept|jd_gap|manual|screenshot_solve|generated
    source_turn_id = Column(UUIDType, ForeignKey("session_turns.id", ondelete="CASCADE"))
    solver_result_id = Column(UUIDType, ForeignKey("solver_results.id", ondelete="CASCADE"))
    prompt = Column(Text, nullable=False)
    reference_answer = Column(Text)
    difficulty = Column(Text)
    ease_factor = Column(Numeric, default=2.5)
    interval_days = Column(Integer, default=1)
    repetitions = Column(Integer, default=0)
    next_review_at = Column(DateTime(timezone=True))
    created_at = _created_at()
    updated_at = _updated_at()


class StudyReview(Base):
    __tablename__ = "study_reviews"
    id = _pk()
    item_id = Column(UUIDType, ForeignKey("study_items.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    quality = Column(Integer)
    new_interval_days = Column(Integer)
    new_ease_factor = Column(Numeric)
    created_at = _created_at()
    updated_at = _updated_at()


# ════════════════════════════════════════════════════════════════════
# Career ops
# ════════════════════════════════════════════════════════════════════

class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (Index("idx_applications_candidate_created", "candidate_id", "created_at"),)
    id = _pk()
    candidate_id = Column(UUIDType, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(UUIDType, ForeignKey("jobs.id", ondelete="SET NULL"))
    company = Column(Text)
    role = Column(Text)
    source = Column(Text)
    status = Column(Text)
    recruiter = Column(Text)
    interview_round = Column(Text)
    next_action = Column(Text)
    notes = Column(Text)
    applied_at = Column(DateTime(timezone=True))
    deleted_at = Column(DateTime(timezone=True))
    created_at = _created_at()
    updated_at = _updated_at()


class ApplicationEvent(Base):
    __tablename__ = "application_events"
    id = _pk()
    application_id = Column(UUIDType, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(Text)
    event_date = Column(DateTime(timezone=True))
    notes = Column(Text)
    created_at = _created_at()
    updated_at = _updated_at()


class OutreachDraft(Base):
    __tablename__ = "outreach_drafts"
    id = _pk()
    application_id = Column(UUIDType, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient_name = Column(Text)
    subject = Column(Text)
    body = Column(Text)
    created_at = _created_at()
    updated_at = _updated_at()


# ════════════════════════════════════════════════════════════════════
# Platform & governance
# ════════════════════════════════════════════════════════════════════

class ProviderHealth(Base):
    __tablename__ = "provider_health"
    id = _pk()
    provider = Column(Text, nullable=False)
    capability = Column(Text, nullable=False)
    state = Column(Text)  # closed|open|half_open
    last_success_at = Column(DateTime(timezone=True))
    last_failure_at = Column(DateTime(timezone=True))
    consecutive_failures = Column(Integer, default=0)
    latency_p50_ms = Column(Integer)
    latency_p95_ms = Column(Integer)
    latency_p99_ms = Column(Integer)
    error_rate = Column(Numeric)
    rate_limited_until = Column(DateTime(timezone=True))
    checked_at = Column(DateTime(timezone=True))
    created_at = _created_at()
    updated_at = _updated_at()


class ModelRequest(Base):
    __tablename__ = "model_requests"
    id = _pk()
    profile_id = Column(UUIDType, ForeignKey("profiles.id", ondelete="SET NULL"))
    session_id = Column(UUIDType, ForeignKey("practice_sessions.id", ondelete="SET NULL"))
    provider = Column(Text)
    model = Column(Text)
    prompt = Column(Text)
    response = Column(Text)
    latency_ms = Column(Integer)
    created_at = _created_at()
    updated_at = _updated_at()


class UsageEvent(Base):
    __tablename__ = "usage_events"
    id = _pk()
    profile_id = Column(UUIDType, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(UUIDType, ForeignKey("practice_sessions.id", ondelete="SET NULL"), index=True)
    provider = Column(Text)
    model = Column(Text)
    capability = Column(Text)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    audio_seconds = Column(Numeric)
    image_count = Column(Integer)
    request_count = Column(Integer)
    estimated_cost_usd = Column(Numeric, default=0)
    was_free_tier = Column(Boolean)
    latency_ms = Column(Integer)
    fell_back_from = Column(Text)
    created_at = _created_at()
    updated_at = _updated_at()


class DeletionJob(Base):
    __tablename__ = "deletion_jobs"
    id = _pk()
    profile_id = Column(UUIDType, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id = Column(UUIDType, ForeignKey("candidates.id", ondelete="SET NULL"))
    status = Column(Text, nullable=False)
    scheduled_for = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    rows_deleted_summary = Column(JSONType)
    created_at = _created_at()
    updated_at = _updated_at()


class FailedJob(Base):
    __tablename__ = "failed_jobs"
    id = _pk()
    job_name = Column(Text, nullable=False)
    job_id = Column(Text, nullable=False)
    args = Column(JSONType)
    error_message = Column(Text)
    failed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    candidate_id = Column(UUIDType, ForeignKey("candidates.id", ondelete="SET NULL"))
    resolved = Column(Boolean, nullable=False, default=False)
    created_at = _created_at()
    updated_at = _updated_at()


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = _pk()
    profile_id = Column(UUIDType, ForeignKey("profiles.id", ondelete="SET NULL"))
    action = Column(Text, nullable=False)
    resource = Column(Text)
    details = Column(JSONType)
    created_at = _created_at()
    updated_at = _updated_at()


class PrivacyEvent(Base):
    __tablename__ = "privacy_events"
    id = _pk()
    profile_id = Column(UUIDType, ForeignKey("profiles.id", ondelete="SET NULL"))
    event_type = Column(Text, nullable=False)
    consent_given = Column(Boolean)
    created_at = _created_at()
    updated_at = _updated_at()
