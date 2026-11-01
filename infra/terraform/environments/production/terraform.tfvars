# PRODUCTION Environment Configuration
project_id                = "praxis-production"
region                    = "asia-south1"
environment               = "production"
artifact_registry_project = "praxis-production"
github_repository         = "AMIYA8597/praxis-interviewOS"
image_tag                 = "prod-pinned"
secret_version            = "1"

api_min_instances      = 1
api_max_instances      = 10
realtime_min_instances = 1
realtime_max_instances = 5
worker_instance_count  = 2
redis_memory_gb        = 2

domain                     = ""
alert_notification_channel = ""
