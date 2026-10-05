# STAGING environment
#
# BLOCKED: GCP project 'praxis-staging' does not exist yet.
# ACTION REQUIRED: See docs/STAGING_PREREQUISITES.md → GCP_STAGING_PROJECT_ID
#
# Option A: Create a new project:
#   gcloud projects create praxis-staging --name="PRAXIS Staging"
#   gcloud billing projects link praxis-staging --billing-account=BILLING_ACCOUNT_ID
#
# Option B: Use an existing project:
#   Update project_id below to your existing project.
#
# WARNING: staging and production must use DIFFERENT GCP projects.

project_id                = "praxis-staging" # REPLACE: see above
region                    = "us-central1"
environment               = "staging"
artifact_registry_project = "praxis-staging" # same as project_id for staging
github_repository         = "AMIYA8597/praxis-interviewOS"

# image_tag is set by CI pipeline via -var="image_tag=${SHORT_SHA}".
# NEVER apply manually with this placeholder — it will fail Terraform validation.
image_tag = "REPLACE_WITH_SHA"

# secret_version: set to "latest" initially, pin to specific version after first deploy.
# Example: secret_version = "3"
secret_version = "latest"

api_min_instances      = 0 # scale-to-zero in staging to save cost
api_max_instances      = 3
realtime_min_instances = 1 # keep at least 1 for WebSocket cold-start latency
realtime_max_instances = 2
worker_instance_count  = 1
redis_memory_gb        = 1

# domain: leave empty to skip TLS cert creation and use Cloud Run URLs.
# Set to a real subdomain (e.g. "staging.praxis.yourdomain.com") when DNS is ready.
# DO NOT use praxis.example.com or any placeholder.
# BLOCKED: no real domain assigned yet — see docs/STAGING_PREREQUISITES.md
domain = ""

alert_notification_channel = "" # optional: Cloud Monitoring channel ID
