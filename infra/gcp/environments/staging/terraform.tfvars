# STAGING environment — praxis-staging GCP project
project_id                = "praxis-staging"
region                    = "us-central1"
environment               = "staging"
artifact_registry_project = "praxis-production"  # shared registry
image_tag                 = "latest"  # overridden by CI pipeline with actual sha

api_min_instances      = 0  # scale to zero in staging to save cost
api_max_instances      = 3
realtime_min_instances = 0
realtime_max_instances = 2
redis_memory_gb        = 1
domain                 = "staging.praxis.example.com"
