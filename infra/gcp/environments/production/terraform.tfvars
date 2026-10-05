# PRODUCTION environment
#
# BLOCKED: GCP project 'praxis-production' does not exist yet.
# ACTION REQUIRED: See docs/STAGING_PREREQUISITES.md → GCP_PRODUCTION_PROJECT_ID
#
# Production MUST NOT be provisioned until staging is certified.
# Sequence: staging certification → review → production provisioning → production deploy.

project_id                = "praxis-production" # REPLACE with real project ID
region                    = "us-central1"
environment               = "production"
artifact_registry_project = "praxis-production"
github_repository         = "AMIYA8597/praxis-interviewOS"

# image_tag must be an immutable digest reference for production.
# Example: image_tag = "sha256:abc123..."
# Set by CI pipeline after staging certification.
image_tag = "REPLACE_WITH_IMMUTABLE_TAG"

# Pin to exact secret version in production. Never leave as "latest" after first deploy.
secret_version = "REPLACE_WITH_SECRET_VERSION"

api_min_instances      = 1 # always warm
api_max_instances      = 10
realtime_min_instances = 1 # always warm for low connect latency
realtime_max_instances = 5
worker_instance_count  = 2
redis_memory_gb        = 2

# domain: set to your real production domain.
# DO NOT deploy with praxis.example.com.
domain = "REPLACE_WITH_REAL_DOMAIN"

alert_notification_channel = "" # REPLACE with Cloud Monitoring channel ID
