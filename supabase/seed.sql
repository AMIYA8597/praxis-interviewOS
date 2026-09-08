-- ==============================================================================
-- SYNTHETIC SEED DATA
-- This file contains strictly synthetic, realistic data for development and demos.
-- THERE IS NO REAL PERSONAL INFORMATION IN THIS FILE.
-- ==============================================================================

-- 1. Create a User Profile and Candidate
do $$
declare 
    v_user_id uuid := '00000000-0000-0000-0000-000000000001';
    v_candidate_id uuid := '00000000-0000-0000-0000-000000000002';
    v_exp_id uuid := '00000000-0000-0000-0000-000000000003';
    v_project1_id uuid := '00000000-0000-0000-0000-000000000004';
    v_project2_id uuid := '00000000-0000-0000-0000-000000000005';
    v_job_id uuid := '00000000-0000-0000-0000-000000000006';
begin

-- Insert Auth & Profile
insert into auth.users (id) values (v_user_id) on conflict do nothing;
insert into profiles (id) values (v_user_id) on conflict do nothing;

-- Insert Candidate
insert into candidates (id, profile_id, full_name, headline, location, years_experience, target_roles, preferred_language, speaking_style, onboarding_step)
values (
    v_candidate_id, 
    v_user_id, 
    'Alex Mercer', 
    'Senior Machine Learning Engineer | Data Systems', 
    'Seattle, WA', 
    6, 
    array['Machine Learning Engineer', 'Data Scientist', 'AI Platform Engineer'], 
    'Python', 
    '{"conciseness": 0.8, "technical_depth": 0.9}'::jsonb, 
    'completed'
);

-- Insert Experience
insert into candidate_experiences (id, candidate_id, company, title, start_date, end_date, description, achievements)
values (
    v_exp_id,
    v_candidate_id,
    'OmniTech Analytics',
    'Machine Learning Engineer',
    '2021-03-01',
    null,
    'Lead engineer for the personalization and ranking systems core team.',
    array['Improved CTR by 14%', 'Reduced training time from 48h to 6h']
);

-- Insert Fully Populated Project 1 (Recommendation System)
insert into candidate_projects (
    id, candidate_id, experience_id, name, summary, problem, motivation, users_served, 
    architecture, tech_stack, datasets, data_pipeline, models_used, training_approach, 
    evaluation_method, metrics, deployment, infra, challenges, failure_cases, tradeoffs, 
    improvements, business_impact, personal_contribution, team_size, duration_months, 
    confidence, verified_by_user
) values (
    v_project1_id, v_candidate_id, v_exp_id, 
    'Real-time Content Ranking Engine', 
    'Re-architected the feed ranking system using a two-tower neural retrieval model and LightGBM ranker.',
    'The existing collaborative filtering approach suffered from extreme cold-start problems for new content.',
    'Business required faster surfacing of breaking news content to increase user session duration.',
    '2M+ Daily Active Users',
    'Two-tower embedding model served via approximate nearest neighbors (HNSW), followed by a real-time feature-join and LightGBM scoring step.',
    array['Python', 'PyTorch', 'LightGBM', 'Redis', 'Kafka', 'FastAPI'],
    '15TB of historical clickstream logs, 50GB of textual article metadata.',
    'Streaming ingestion from Kafka into a feature store; nightly batch offline training via Airflow and Spark.',
    array['Two-Tower DNN', 'LightGBM'],
    'Contrastive loss for the embedding towers using in-batch negatives. Pointwise regression for the ranker.',
    'Offline NDCG@10 and Recall@50. Online via A/B testing measuring overall Session Duration.',
    '{"ndcg_10": "+12%", "ctr": "+14%", "latency_ms": 45}',
    'Containerized FastAPI service behind a load balancer.',
    'Kubernetes (EKS), AWS SageMaker for training, Redis for feature caching.',
    'Handling the high-throughput real-time feature fetching without blowing up the latency budget.',
    'Initial iteration heavily favored clickbait due to uncalibrated pointwise loss; fixed by adding a dwell-time penalty.',
    'Chose a lighter ranker (LightGBM) over a heavy transformer-based cross-encoder to strictly meet the 50ms p99 latency SLA.',
    'Would like to move to a listwise loss function like LambdaMART for the ranker.',
    'Increased daily active user retention by 3.2% and ad-revenue by roughly $1.2M annually.',
    'Designed the two-tower model architecture, implemented the negative sampling strategy, and led the deployment rollout.',
    4, 6, 0.95, true
);

-- Insert Fully Populated Project 2 (Data Pipeline Optimization)
insert into candidate_projects (
    id, candidate_id, experience_id, name, summary, problem, motivation, users_served, 
    architecture, tech_stack, datasets, data_pipeline, models_used, training_approach, 
    evaluation_method, metrics, deployment, infra, challenges, failure_cases, tradeoffs, 
    improvements, business_impact, personal_contribution, team_size, duration_months, 
    confidence, verified_by_user
) values (
    v_project2_id, v_candidate_id, v_exp_id, 
    'Distributed Embedding Pipeline', 
    'Optimized the batch generation of vector embeddings for the entire content catalog.',
    'Embedding generation took 48 hours to run on a single GPU node, making daily updates impossible.',
    'Downstream systems needed fresh embeddings daily to react to trending topics.',
    'Internal downstream ranking models',
    'Spark-based distributed inference pipeline utilizing a cluster of T4 GPUs for batch encoding.',
    array['PySpark', 'HuggingFace', 'Docker', 'AWS Batch'],
    'Daily ingest of ~500k new textual documents and metadata updates.',
    'Delta Lake for source data, Spark UDFs running PyTorch model inference.',
    array['MiniLM-L6-v2'],
    'Off-the-shelf pre-trained model; no fine-tuning required for this specific phase.',
    'Throughput (documents per second) and Cost per run.',
    '{"runtime_reduction": "87%", "cost_savings": "40%"}',
    'AWS EMR / Spark Cluster.',
    'AWS EMR, EC2 Spot Instances (g4dn).',
    'Handling out-of-memory errors on the GPU when batch sizes were improperly padded during distributed partitions.',
    'Spot instance preemptions caused entire Spark stages to fail and retry, extending job times unpredictably.',
    'Traded complex custom distributed orchestration for native Spark UDFs, sacrificing some GPU utilization for developer velocity.',
    'Implement dynamic batching and better spot-interruption handling logic.',
    'Allowed daily (rather than weekly) model updates, enabling the company to react to daily news trends.',
    'Wrote the PySpark inference UDFs and optimized the AWS EMR spot instance configuration.',
    2, 2, 0.88, true
);

-- Insert STAR Stories
insert into stories (candidate_id, project_id, experience_id, title, situation, task, action, result, competency_tags)
values (
    v_candidate_id, v_project1_id, v_exp_id,
    'Handling Strict Latency Constraints',
    'During the rollout of the Real-time Content Ranking Engine, we realized the cross-encoder model we originally planned was taking 120ms to score.',
    'We had a strict Service Level Agreement (SLA) of 50ms at the 99th percentile for the entire ranking request.',
    'I led the decision to pivot the architecture. Instead of a cross-encoder, I designed a Two-Tower retrieval model to narrow the field using HNSW vector search, followed by a fast LightGBM ranker.',
    'We successfully met the 50ms p99 SLA (hitting 45ms in production) while still achieving a 14% lift in CTR, effectively saving the project from being blocked by infrastructure.',
    array['Architecture', 'Tradeoffs', 'Performance Optimization', 'Decision Making']
);

insert into stories (candidate_id, project_id, experience_id, title, situation, task, action, result, competency_tags)
values (
    v_candidate_id, v_project2_id, v_exp_id,
    'Dealing with Spot Instance Interruptions',
    'Our newly built Spark embedding pipeline was experiencing severe delays because AWS EC2 Spot instances were being preempted heavily during our run window.',
    'I needed to stabilize the pipeline runtime without tripling our cloud compute costs by switching to On-Demand instances.',
    'I implemented a checkpointing mechanism within the Spark job to save intermediate embedding partitions to S3. I also diversified our Spot fleet request to include multiple instance types (g4dn, g5) across different availability zones to reduce the likelihood of bulk preemptions.',
    'The pipeline stabilized, consistently completing within the 6-hour window, and we maintained the 40% cost savings associated with Spot pricing.',
    array['Cloud Infrastructure', 'Cost Optimization', 'Resilience', 'Problem Solving']
);

-- Insert Synthetic Job Fixture
insert into jobs (id, candidate_id, company_name, role_title, raw_jd_text, seniority_signal)
values (
    v_job_id, v_candidate_id, 
    'Quantum Data Systems', 
    'Machine Learning Engineer (Mid-Level)', 
    'About Us: Quantum Data Systems is building the future of predictive logistics. We are looking for a Machine Learning Engineer to join our forecasting team. You will be responsible for building, deploying, and maintaining models that predict supply chain bottlenecks. 
Requirements: 
- 3+ years of experience in deploying ML models to production. 
- Strong proficiency in Python, PyTorch, or TensorFlow.
- Experience with real-time data pipelines (Kafka, Flink, or Spark Streaming).
- Familiarity with Kubernetes and Docker.
- A strong understanding of evaluation metrics and A/B testing methodologies.
Preferred: Experience with Time Series forecasting or Graph Neural Networks.',
    'Mid-Level'
);

-- Insert Job Blueprint
insert into job_blueprints (job_id, top_skills, likely_topics, summary, prep_pack)
values (
    v_job_id,
    '{"Python": "Required", "PyTorch": "Required", "Kafka/Spark": "Required", "Kubernetes": "Required", "Time Series": "Preferred"}'::jsonb,
    array['Model Deployment Lifecycle', 'Real-time Pipeline Architecture', 'A/B Testing and Metric Selection', 'Handling Concept Drift in Production'],
    'A mid-level ML Engineering role focused heavily on productionization, real-time data streaming, and robust deployment infrastructure rather than pure research.',
    '{"focus_areas": ["System Design for Streaming", "MLOps", "Tradeoffs in Model Serving Latency"]}'::jsonb
);

end $$;
