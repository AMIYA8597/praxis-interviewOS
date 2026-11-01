################################################################################
# PRAXIS InterviewOS — Master Terraform Root Configuration
################################################################################

terraform {
  required_version = ">= 1.9.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.14"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 6.14"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

module "gcp_infrastructure" {
  source = "../gcp"

  project_id                 = var.project_id
  region                     = var.region
  environment                = var.environment
  artifact_registry_project  = var.artifact_registry_project
  github_repository          = var.github_repository
  image_tag                  = var.image_tag
  secret_version             = var.secret_version
  db_pool_size               = var.db_pool_size
  db_max_overflow            = var.db_max_overflow
  api_min_instances          = var.api_min_instances
  api_max_instances          = var.api_max_instances
  realtime_min_instances     = var.realtime_min_instances
  realtime_max_instances     = var.realtime_max_instances
  worker_instance_count      = var.worker_instance_count
  redis_memory_gb            = var.redis_memory_gb
  domain                     = var.domain
  alert_notification_channel = var.alert_notification_channel
}
