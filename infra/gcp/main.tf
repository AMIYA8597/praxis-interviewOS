################################################################################
# PRAXIS — GCP Infrastructure
# Phase 99 — Infrastructure as Code
#
# Usage:
#   cd infra/gcp/environments/staging
#   terraform init
#   terraform plan -var-file=terraform.tfvars
#   terraform apply
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
  backend "gcs" {
    # bucket and prefix are set per-environment via -backend-config
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

################################################################################
# Variables
################################################################################

variable "project_id" {
  description = "GCP project ID (e.g. praxis-staging or praxis-production)"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Environment label: staging or production"
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be staging or production"
  }
}

variable "artifact_registry_project" {
  description = "Project hosting the shared Artifact Registry"
  type        = string
}

variable "image_tag" {
  description = "Docker image tag to deploy (e.g. sha256:... or v2026.10.1)"
  type        = string
}

variable "api_min_instances" {
  description = "Min Cloud Run instances for praxis-api"
  type        = number
  default     = 1
}

variable "api_max_instances" {
  description = "Max Cloud Run instances for praxis-api"
  type        = number
  default     = 10
}

variable "realtime_min_instances" {
  description = "Min Cloud Run instances for praxis-realtime"
  type        = number
  default     = 1
}

variable "realtime_max_instances" {
  description = "Max Cloud Run instances for praxis-realtime"
  type        = number
  default     = 5
}

variable "redis_memory_gb" {
  description = "Memorystore Redis memory size in GB"
  type        = number
  default     = 1
}

variable "domain" {
  description = "Production domain (e.g. praxis.yourdomain.com)"
  type        = string
}

################################################################################
# Enable required APIs
################################################################################

resource "google_project_service" "required_apis" {
  for_each = toset([
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "redis.googleapis.com",
    "compute.googleapis.com",
    "vpcaccess.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudtrace.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "cloudbuild.googleapis.com",
    "iam.googleapis.com",
  ])
  service            = each.value
  disable_on_destroy = false
}

################################################################################
# VPC + Serverless VPC connector
################################################################################

resource "google_compute_network" "praxis" {
  name                    = "praxis-${var.environment}"
  auto_create_subnetworks = false
  depends_on              = [google_project_service.required_apis]
}

resource "google_compute_subnetwork" "praxis" {
  name          = "praxis-${var.environment}-subnet"
  network       = google_compute_network.praxis.id
  ip_cidr_range = "10.10.0.0/24"
  region        = var.region
}

resource "google_vpc_access_connector" "praxis" {
  name          = "praxis-${var.environment}"
  region        = var.region
  network       = google_compute_network.praxis.name
  ip_cidr_range = "10.8.0.0/28"
  min_throughput = 200
  max_throughput = 1000
  depends_on    = [google_project_service.required_apis]
}

################################################################################
# Memorystore Redis
################################################################################

resource "google_redis_instance" "praxis" {
  name           = "praxis-${var.environment}"
  memory_size_gb = var.redis_memory_gb
  region         = var.region
  tier           = "BASIC"
  redis_version  = "REDIS_7_2"

  authorized_network = google_compute_network.praxis.id
  connect_mode       = "DIRECT_PEERING"

  labels = {
    environment = var.environment
    app         = "praxis"
  }

  depends_on = [google_project_service.required_apis]
}

################################################################################
# Service Accounts (Phase 100 — IAM Hardening)
################################################################################

resource "google_service_account" "api" {
  account_id   = "praxis-api-${var.environment}"
  display_name = "PRAXIS API Service Account (${var.environment})"
}

resource "google_service_account" "realtime" {
  account_id   = "praxis-realtime-${var.environment}"
  display_name = "PRAXIS Realtime Service Account (${var.environment})"
}

resource "google_service_account" "worker" {
  account_id   = "praxis-worker-${var.environment}"
  display_name = "PRAXIS Worker Service Account (${var.environment})"
}

resource "google_service_account" "deployer" {
  account_id   = "praxis-deployer"
  display_name = "PRAXIS GitHub Actions Deployer"
}

# Least-privilege bindings
resource "google_project_iam_member" "api_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.api.email}"
}

resource "google_project_iam_member" "realtime_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.realtime.email}"
}

resource "google_project_iam_member" "worker_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.worker.email}"
}

resource "google_project_iam_member" "api_trace_agent" {
  project = var.project_id
  role    = "roles/cloudtrace.agent"
  member  = "serviceAccount:${google_service_account.api.email}"
}

resource "google_project_iam_member" "realtime_trace_agent" {
  project = var.project_id
  role    = "roles/cloudtrace.agent"
  member  = "serviceAccount:${google_service_account.realtime.email}"
}

# Deployer: Cloud Run developer + Artifact Registry reader
resource "google_project_iam_member" "deployer_run_developer" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_project_iam_member" "deployer_ar_reader" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.deployer.email}"
}

# Workload Identity for GitHub Actions (no long-lived key files)
resource "google_iam_workload_identity_pool" "github" {
  provider                  = google-beta
  workload_identity_pool_id = "github-actions"
  display_name              = "GitHub Actions"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  provider                           = google-beta
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
  }
  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

################################################################################
# Artifact Registry (Phase 101)
################################################################################

resource "google_artifact_registry_repository" "praxis" {
  location      = var.region
  repository_id = "praxis"
  format        = "DOCKER"
  description   = "PRAXIS container images"

  labels = {
    environment = var.environment
    app         = "praxis"
  }

  depends_on = [google_project_service.required_apis]
}

################################################################################
# Cloud Run — API (Phase 102)
################################################################################

resource "google_cloud_run_v2_service" "api" {
  name     = "praxis-api"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"

  template {
    service_account = google_service_account.api.email

    scaling {
      min_instance_count = var.api_min_instances
      max_instance_count = var.api_max_instances
    }

    vpc_access {
      connector = google_vpc_access_connector.praxis.id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    timeout = "60s"

    containers {
      image = "${var.region}-docker.pkg.dev/${var.artifact_registry_project}/praxis/praxis-api:${var.image_tag}"

      resources {
        limits = {
          cpu    = "1000m"
          memory = "512Mi"
        }
        cpu_idle          = true
        startup_cpu_boost = true
      }

      ports {
        name           = "http1"
        container_port = 8000
      }

      env {
        name  = "APP_ENV"
        value = var.environment
      }

      # Secrets mounted from Secret Manager
      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = "praxis-database-url"
            version = "latest"
          }
        }
      }

      env {
        name = "REDIS_URL"
        value_source {
          secret_key_ref {
            secret  = "praxis-redis-url"
            version = "latest"
          }
        }
      }

      env {
        name = "SUPABASE_URL"
        value_source {
          secret_key_ref {
            secret  = "praxis-supabase-url"
            version = "latest"
          }
        }
      }

      env {
        name = "SUPABASE_ANON_KEY"
        value_source {
          secret_key_ref {
            secret  = "praxis-supabase-anon-key"
            version = "latest"
          }
        }
      }

      startup_probe {
        http_get {
          path = "/health"
          port = 8000
        }
        initial_delay_seconds = 10
        period_seconds        = 5
        failure_threshold     = 12
      }

      liveness_probe {
        http_get {
          path = "/health"
          port = 8000
        }
        period_seconds    = 30
        failure_threshold = 3
      }
    }
  }

  depends_on = [google_project_service.required_apis]
}

################################################################################
# Cloud Run — Realtime Agent (Phase 103)
################################################################################

resource "google_cloud_run_v2_service" "realtime" {
  name     = "praxis-realtime"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"

  template {
    service_account = google_service_account.realtime.email

    scaling {
      min_instance_count = var.realtime_min_instances
      max_instance_count = var.realtime_max_instances
    }

    vpc_access {
      connector = google_vpc_access_connector.praxis.id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    # WebSocket sessions: longer timeout
    timeout = "3600s"

    containers {
      image = "${var.region}-docker.pkg.dev/${var.artifact_registry_project}/praxis/praxis-realtime:${var.image_tag}"

      resources {
        limits = {
          cpu    = "2000m"
          memory = "2Gi"
        }
        cpu_idle          = false  # always-on for low-latency audio
        startup_cpu_boost = true
      }

      ports {
        name           = "http1"
        container_port = 8080
      }

      env {
        name  = "APP_ENV"
        value = var.environment
      }

      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = "praxis-database-url"
            version = "latest"
          }
        }
      }

      env {
        name = "REDIS_URL"
        value_source {
          secret_key_ref {
            secret  = "praxis-redis-url"
            version = "latest"
          }
        }
      }

      startup_probe {
        http_get {
          path = "/health"
          port = 8080
        }
        initial_delay_seconds = 30
        period_seconds        = 10
        failure_threshold     = 9
      }
    }
  }

  depends_on = [google_project_service.required_apis]
}

################################################################################
# Load Balancer + TLS (Phase 108)
################################################################################

resource "google_compute_ssl_certificate" "praxis" {
  count       = 0  # Use google_compute_managed_ssl_certificate in production
  name        = "praxis-${var.environment}-ssl"
  private_key = ""
  certificate = ""
}

resource "google_compute_managed_ssl_certificate" "praxis" {
  name = "praxis-${var.environment}"
  managed {
    domains = [
      "api.${var.domain}",
      "realtime.${var.domain}",
    ]
  }
}

resource "google_compute_global_address" "praxis" {
  name = "praxis-${var.environment}-ip"
}

# Serverless NEGs
resource "google_compute_region_network_endpoint_group" "api_neg" {
  name                  = "praxis-api-neg-${var.environment}"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  cloud_run {
    service = google_cloud_run_v2_service.api.name
  }
}

resource "google_compute_region_network_endpoint_group" "realtime_neg" {
  name                  = "praxis-realtime-neg-${var.environment}"
  network_endpoint_type = "SERVERLESS"
  region                = var.region
  cloud_run {
    service = google_cloud_run_v2_service.realtime.name
  }
}

# Backend services
resource "google_compute_backend_service" "api" {
  name                  = "praxis-api-backend-${var.environment}"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  protocol              = "HTTP2"

  backend {
    group = google_compute_region_network_endpoint_group.api_neg.id
  }

  log_config {
    enable      = true
    sample_rate = 1.0
  }
}

resource "google_compute_backend_service" "realtime" {
  name                  = "praxis-realtime-backend-${var.environment}"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  protocol              = "HTTP2"
  timeout_sec           = 3600  # WebSocket sessions

  backend {
    group = google_compute_region_network_endpoint_group.realtime_neg.id
  }
}

# URL map — /api/* → praxis-api, /realtime/* → praxis-realtime
resource "google_compute_url_map" "praxis" {
  name            = "praxis-${var.environment}"
  default_service = google_compute_backend_service.api.id

  host_rule {
    hosts        = ["api.${var.domain}"]
    path_matcher = "api-paths"
  }

  host_rule {
    hosts        = ["realtime.${var.domain}"]
    path_matcher = "realtime-paths"
  }

  path_matcher {
    name            = "api-paths"
    default_service = google_compute_backend_service.api.id
  }

  path_matcher {
    name            = "realtime-paths"
    default_service = google_compute_backend_service.realtime.id
  }
}

resource "google_compute_target_https_proxy" "praxis" {
  name             = "praxis-${var.environment}-https"
  url_map          = google_compute_url_map.praxis.id
  ssl_certificates = [google_compute_managed_ssl_certificate.praxis.id]
}

resource "google_compute_global_forwarding_rule" "https" {
  name                  = "praxis-${var.environment}-https"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  port_range            = "443"
  target                = google_compute_target_https_proxy.praxis.id
  ip_address            = google_compute_global_address.praxis.address
}

################################################################################
# Cloud Armor (Phase 109)
################################################################################

resource "google_compute_security_policy" "praxis" {
  name = "praxis-${var.environment}-armor"

  # Default: allow
  rule {
    action   = "allow"
    priority = "2147483647"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    description = "default allow"
  }

  # Throttle: max 100 req/60s per IP for API
  rule {
    action   = "throttle"
    priority = "1000"
    match {
      versioned_expr = "SRC_IPS_V1"
      config {
        src_ip_ranges = ["*"]
      }
    }
    rate_limit_options {
      conform_action = "allow"
      exceed_action  = "deny(429)"
      enforce_on_key = "IP"
      rate_limit_threshold {
        count        = 100
        interval_sec = 60
      }
    }
    description = "rate limit per IP"
  }

  # Block requests with SQLi/XSS patterns (pre-configured rule)
  rule {
    action   = "deny(403)"
    priority = "900"
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('sqli-v33-stable')"
      }
    }
    description = "SQLi protection"
  }

  rule {
    action   = "deny(403)"
    priority = "901"
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('xss-v33-stable')"
      }
    }
    description = "XSS protection"
  }
}

################################################################################
# Outputs
################################################################################

output "api_url" {
  value       = "https://api.${var.domain}"
  description = "Production API URL"
}

output "realtime_url" {
  value       = "wss://realtime.${var.domain}"
  description = "Production WebSocket URL"
}

output "redis_host" {
  value       = google_redis_instance.praxis.host
  description = "Memorystore Redis host (private)"
  sensitive   = true
}

output "load_balancer_ip" {
  value       = google_compute_global_address.praxis.address
  description = "External IP — configure DNS A records for api.domain and realtime.domain"
}
