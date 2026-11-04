# STAGING Environment Configuration
project_id                = "praxis-staging"
region                    = "asia-south1"
environment               = "staging"
artifact_registry_project = "praxis-staging"
github_repository         = "AMIYA8597/praxis-interviewOS"
# image_tag is set by CI pipeline via -var="image_tag=${SHORT_SHA}".
# NEVER apply manually with a placeholder — it will fail validation.
image_tag      = "REPLACE_WITH_SHA"
secret_version = "1"

api_min_instances      = 0
api_max_instances      = 3
realtime_min_instances = 1
realtime_max_instances = 2
worker_instance_count  = 1
redis_memory_gb        = 1

domain                     = ""
alert_notification_channel = ""
