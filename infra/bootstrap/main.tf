################################################################################
# PRAXIS — Bootstrap: Terraform Remote State Bucket
#
# This module creates the GCS bucket used as the Terraform remote state backend.
# It MUST be applied BEFORE running main.tf in any environment.
#
# BOOTSTRAP ORDER:
#   1. terraform -chdir=infra/bootstrap init
#   2. terraform -chdir=infra/bootstrap apply -var="project_id=praxis-staging" \
#        -var="environment=staging"
#   3. cd infra/gcp/environments/staging
#   4. terraform init -backend-config=backend.conf
#   5. terraform plan / apply
#
# This module uses LOCAL state (stored in infra/bootstrap/terraform.tfstate).
# The bootstrap state file is small and must be preserved. Do not lose it.
# Commit it to a secure location or back it up manually.
#
# NEVER use Terraform that depends on remote state to provision the remote
# state bucket itself — that is a bootstrap cycle.
################################################################################

terraform {
  required_version = ">= 1.9.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.14"
    }
  }
  # Bootstrap uses LOCAL state intentionally.
  # Do not change this to a remote backend.
}

variable "project_id" {
  description = "GCP project ID where the state bucket will be created"
  type        = string
}

variable "environment" {
  description = "Environment label: staging or production"
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be staging or production"
  }
}

variable "region" {
  description = "GCS bucket region"
  type        = string
  default     = "us-central1"
}

provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_storage_bucket" "terraform_state" {
  name          = "praxis-tf-state-${var.environment}-${var.project_id}"
  location      = upper(var.region)
  force_destroy = false # prevent accidental deletion of state

  # Object versioning: enables state recovery (Terraform recommendation)
  versioning {
    enabled = true
  }

  # State files are small; 90-day lifecycle on noncurrent versions is sufficient.
  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age                = 90
      with_state         = "ARCHIVED"
      num_newer_versions = 5
    }
  }

  # Block all public access
  public_access_prevention = "enforced"

  uniform_bucket_level_access = true

  labels = {
    purpose     = "terraform-state"
    environment = var.environment
    app         = "praxis"
  }
}

# IAM: only the deployer SA can read/write state.
# Terraform plan/apply from CI runs as the deployer SA.
resource "google_storage_bucket_iam_binding" "terraform_state_admin" {
  bucket = google_storage_bucket.terraform_state.name
  role   = "roles/storage.objectAdmin"
  members = [
    "serviceAccount:praxis-deployer-${var.environment}@${var.project_id}.iam.gserviceaccount.com",
  ]
}

output "state_bucket" {
  value       = google_storage_bucket.terraform_state.name
  description = "GCS bucket name — use in backend.conf as: bucket = \"<this value>\""
}

output "backend_conf_content" {
  value       = <<-EOT
    bucket = "${google_storage_bucket.terraform_state.name}"
    prefix = "terraform/state"
  EOT
  description = "Contents for the environment's backend.conf file"
}
