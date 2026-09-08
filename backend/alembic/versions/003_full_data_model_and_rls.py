"""Full Data Model and RLS

Revision ID: 003_full_data_model_and_rls
Revises: 002_context_graph
Create Date: 2026-09-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003_full_data_model_and_rls'
down_revision: Union[str, None] = '002_context_graph'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update document_chunks with content_tsv
    op.execute("ALTER TABLE document_chunks ADD COLUMN content_tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED")
    op.execute("CREATE INDEX idx_document_chunks_content_tsv ON document_chunks USING GIN(content_tsv)")

    # 2. Add columns to projects
    op.add_column('projects', sa.Column('summary', sa.Text(), nullable=True))
    op.add_column('projects', sa.Column('problem', sa.Text(), nullable=True))
    op.add_column('projects', sa.Column('motivation', sa.Text(), nullable=True))
    op.add_column('projects', sa.Column('users_served', sa.String(length=255), nullable=True))
    op.add_column('projects', sa.Column('architecture', sa.Text(), nullable=True))
    op.add_column('projects', sa.Column('tech_stack', sa.JSON(), nullable=True))
    op.add_column('projects', sa.Column('datasets', sa.Text(), nullable=True))
    op.add_column('projects', sa.Column('data_pipeline', sa.Text(), nullable=True))
    op.add_column('projects', sa.Column('models_used', sa.JSON(), nullable=True))
    op.add_column('projects', sa.Column('training_approach', sa.Text(), nullable=True))
    op.add_column('projects', sa.Column('evaluation_method', sa.Text(), nullable=True))
    op.add_column('projects', sa.Column('metrics', sa.JSON(), nullable=True))
    op.add_column('projects', sa.Column('deployment', sa.Text(), nullable=True))
    op.add_column('projects', sa.Column('infra', sa.Text(), nullable=True))
    op.add_column('projects', sa.Column('challenges', sa.Text(), nullable=True))
    op.add_column('projects', sa.Column('failure_cases', sa.Text(), nullable=True))
    op.add_column('projects', sa.Column('tradeoffs', sa.Text(), nullable=True))
    op.add_column('projects', sa.Column('improvements', sa.Text(), nullable=True))
    op.add_column('projects', sa.Column('business_impact', sa.Text(), nullable=True))
    op.add_column('projects', sa.Column('personal_contribution', sa.Text(), nullable=True))
    op.add_column('projects', sa.Column('team_size', sa.String(length=50), nullable=True))
    op.add_column('projects', sa.Column('duration_months', sa.Numeric(), nullable=True))
    op.add_column('projects', sa.Column('github_url', sa.String(length=255), nullable=True))
    op.add_column('projects', sa.Column('demo_url', sa.String(length=255), nullable=True))
    op.add_column('projects', sa.Column('confidence', sa.Numeric(), nullable=True))
    
    # 3. Alter existing verified_by_user to boolean if it isn't
    op.execute("ALTER TABLE projects DROP COLUMN verified_by_user")
    op.add_column('projects', sa.Column('verified_by_user', sa.Boolean(), server_default='false', nullable=False))

    # 4. Create new tables
    op.create_table('resume_claims',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('resume_id', sa.UUID(), nullable=True),
        sa.Column('claim_text', sa.Text(), nullable=True),
        sa.Column('claim_type', sa.String(length=50), nullable=True),
        sa.Column('page', sa.Integer(), nullable=True),
        sa.Column('char_start', sa.Integer(), nullable=True),
        sa.Column('char_end', sa.Integer(), nullable=True),
        sa.Column('extraction_confidence', sa.Numeric(), nullable=True),
        sa.Column('verified_by_user', sa.Boolean(), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['resume_id'], ['resumes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('session_turns',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=True),
        sa.Column('turn_index', sa.Integer(), nullable=True),
        sa.Column('speaker', sa.String(length=50), nullable=True),
        sa.Column('parent_turn_id', sa.UUID(), nullable=True),
        sa.Column('text_content', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['parent_turn_id'], ['session_turns.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['session_id'], ['interview_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('turn_metrics',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('turn_id', sa.UUID(), nullable=True),
        sa.Column('word_count', sa.Integer(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('wpm', sa.Numeric(), nullable=True),
        sa.Column('filler_count', sa.Integer(), nullable=True),
        sa.Column('filler_rate', sa.Numeric(), nullable=True),
        sa.Column('filler_breakdown', sa.JSON(), nullable=True),
        sa.Column('pause_count', sa.Integer(), nullable=True),
        sa.Column('longest_pause_ms', sa.Integer(), nullable=True),
        sa.Column('pause_ratio', sa.Numeric(), nullable=True),
        sa.Column('pitch_variance', sa.Numeric(), nullable=True),
        sa.Column('energy_variance', sa.Numeric(), nullable=True),
        sa.Column('hedge_count', sa.Integer(), nullable=True),
        sa.Column('sentence_count', sa.Integer(), nullable=True),
        sa.Column('avg_sentence_len', sa.Numeric(), nullable=True),
        sa.Column('time_to_first_word_ms', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['turn_id'], ['session_turns.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('turn_scores',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('turn_id', sa.UUID(), nullable=True),
        sa.Column('rubric_version', sa.String(length=50), nullable=True),
        sa.Column('relevance', sa.Numeric(), nullable=True),
        sa.Column('correctness', sa.Numeric(), nullable=True),
        sa.Column('structure', sa.Numeric(), nullable=True),
        sa.Column('grounding', sa.Numeric(), nullable=True),
        sa.Column('specificity', sa.Numeric(), nullable=True),
        sa.Column('conciseness', sa.Numeric(), nullable=True),
        sa.Column('star_completeness', sa.JSON(), nullable=True),
        sa.Column('overall', sa.Numeric(), nullable=True),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('model_used', sa.String(length=100), nullable=True),
        sa.Column('scored_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['turn_id'], ['session_turns.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('session_claims',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=True),
        sa.Column('turn_id', sa.UUID(), nullable=True),
        sa.Column('claim_text', sa.Text(), nullable=True),
        sa.Column('supported', sa.Boolean(), nullable=True),
        sa.Column('source_chunk_id', sa.UUID(), nullable=True),
        sa.Column('source_project_id', sa.UUID(), nullable=True),
        sa.Column('confidence', sa.Numeric(), nullable=True),
        sa.Column('contradiction_of_claim_id', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['contradiction_of_claim_id'], ['session_claims.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['session_id'], ['interview_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_chunk_id'], ['document_chunks.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['source_project_id'], ['projects.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['turn_id'], ['session_turns.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('study_items',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('candidate_id', sa.UUID(), nullable=True),
        sa.Column('topic', sa.String(length=255), nullable=True),
        sa.Column('source', sa.String(length=100), nullable=True),
        sa.Column('source_turn_id', sa.UUID(), nullable=True),
        sa.Column('prompt_text', sa.Text(), nullable=True),
        sa.Column('reference_answer', sa.Text(), nullable=True),
        sa.Column('difficulty', sa.String(length=50), nullable=True),
        sa.Column('ease_factor', sa.Numeric(), nullable=True),
        sa.Column('interval_days', sa.Integer(), nullable=True),
        sa.Column('next_review_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidate_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_turn_id'], ['session_turns.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('study_reviews',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('item_id', sa.UUID(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('quality', sa.Integer(), nullable=True),
        sa.Column('new_interval_days', sa.Integer(), nullable=True),
        sa.Column('new_ease_factor', sa.Numeric(), nullable=True),
        sa.ForeignKeyConstraint(['item_id'], ['study_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('provider_health',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('provider', sa.String(length=100), nullable=True),
        sa.Column('capability', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=50), nullable=True),
        sa.Column('last_success_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_failure_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('consecutive_failures', sa.Integer(), nullable=True),
        sa.Column('latency_p50_ms', sa.Integer(), nullable=True),
        sa.Column('latency_p95_ms', sa.Integer(), nullable=True),
        sa.Column('latency_p99_ms', sa.Integer(), nullable=True),
        sa.Column('error_rate', sa.Numeric(), nullable=True),
        sa.Column('rate_limited_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('checked_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('usage_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.String(length=255), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=True),
        sa.Column('provider', sa.String(length=100), nullable=True),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('capability', sa.String(length=100), nullable=True),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('audio_seconds', sa.Numeric(), nullable=True),
        sa.Column('image_count', sa.Integer(), nullable=True),
        sa.Column('request_count', sa.Integer(), nullable=True),
        sa.Column('estimated_cost_usd', sa.Numeric(), nullable=True),
        sa.Column('was_free_tier', sa.Boolean(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('fell_back_from', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['interview_sessions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # 5. RLS Policies
    
    # candidate_projects
    op.execute("ALTER TABLE projects ENABLE ROW LEVEL SECURITY;")
    op.execute('''
        CREATE POLICY "projects_select_own" ON projects FOR SELECT 
        USING (current_setting('request.jwt.claim.sub', true) = (select user_id from candidate_profiles where id = projects.candidate_id));
    ''')
    op.execute('''
        CREATE POLICY "projects_insert_own" ON projects FOR INSERT 
        WITH CHECK (current_setting('request.jwt.claim.sub', true) = (select user_id from candidate_profiles where id = projects.candidate_id));
    ''')

    # experiences
    op.execute("ALTER TABLE experiences ENABLE ROW LEVEL SECURITY;")
    op.execute('''
        CREATE POLICY "experiences_select_own" ON experiences FOR SELECT 
        USING (current_setting('request.jwt.claim.sub', true) = (select user_id from candidate_profiles where id = experiences.candidate_id));
    ''')

    # study_items
    op.execute("ALTER TABLE study_items ENABLE ROW LEVEL SECURITY;")
    op.execute('''
        CREATE POLICY "study_items_select_own" ON study_items FOR SELECT 
        USING (current_setting('request.jwt.claim.sub', true) = (select user_id from candidate_profiles where id = study_items.candidate_id));
    ''')

def downgrade() -> None:
    # Drop RLS
    op.execute("DROP POLICY IF EXISTS \"study_items_select_own\" ON study_items;")
    op.execute("DROP POLICY IF EXISTS \"experiences_select_own\" ON experiences;")
    op.execute("DROP POLICY IF EXISTS \"projects_insert_own\" ON projects;")
    op.execute("DROP POLICY IF EXISTS \"projects_select_own\" ON projects;")
    
    # Drop Tables
    op.drop_table('usage_events')
    op.drop_table('provider_health')
    op.drop_table('study_reviews')
    op.drop_table('study_items')
    op.drop_table('session_claims')
    op.drop_table('turn_scores')
    op.drop_table('turn_metrics')
    op.drop_table('session_turns')
    op.drop_table('resume_claims')
