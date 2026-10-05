# PRODUCTION environment — praxis-production GCP project
project_id                = "praxis-production"
region                    = "us-central1"
environment               = "production"
artifact_registry_project = "praxis-production"
image_tag                 = "REPLACE_WITH_IMMUTABLE_TAG"  # e.g. sha256:...

api_min_instances      = 1  # always warm
api_max_instances      = 10
realtime_min_instances = 1  # always warm for low connect latency
realtime_max_instances = 5
redis_memory_gb        = 2
domain                 = "praxis.example.com"  # REPLACE with real domain
