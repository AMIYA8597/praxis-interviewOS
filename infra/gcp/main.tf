################################################################################
# PRAXIS — GCP Infrastructure
#
# Usage (per environment):
#   cd infra/gcp/environments/staging
#   terraform init -backend-config=backend.conf
#   terraform plan -var-file=terraform.tfvars
#   terraform apply -var-file=terraform.tfvars
#
# Bootstrap order:
#   1. Run infra/bootstrap/ to create GCS state bucket
#   2. terraform init (configures remote state)
#   3. terraform plan
#   4. terraform apply
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
    # bucket and prefix are set per-environment via -backend-config=backend.conf
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
  description = "GCP project ID (e.g. praxis-staging)"
  type        = string
}

variable "region" {
  description = "GCP region — choose based on user latency and Supabase location"
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
  description = "Project hosting the shared Artifact Registry (may differ from runtime project)"
  type        = string
}

variable "image_tag" {
  description = "Docker image tag to deploy. Must be a git SHA (e.g. abc1234). NEVER use 'latest'."
  type        = string
  validation {
    condition     = !contains(["latest", "dev", "test", "main", "REPLACE_WITH_SHA", "REPLACE_WITH_IMMUTABLE_TAG"], var.image_tag)
    error_message = "image_tag must be a specific git SHA or immutable tag, not a mutable alias."
  }
}

variable "secret_version" {
  description = "Secret Manager version to pin. 'latest' is allowed during initial bootstrap only — pin to a specific version number after first deploy."
  type        = string
  default     = "latest"
}

variable "github_repository" {
  description = "GitHub repository allowed to use Workload Identity (format: owner/repo)"
  type        = string
  default     = "AMIYA8597/praxis-interviewOS"
}

variable "api_min_instances" {
  description = "Min Cloud Run instances for praxis-api (0 = scale-to-zero)"
  type        = number
  default     = 1
}

variable "api_max_instances" {
  description = "Max Cloud Run instances for praxis-api"
  type        = number
  default     = 10
}

variable "realtime_min_instances" {
  description = "Min Cloud Run instances for praxis-realtime (keep >= 1 for WebSocket latency)"
  type        = number
  default     = 1
}

variable "realtime_max_instances" {
  description = "Max Cloud Run instances for praxis-realtime"
  type        = number
  default     = 5
}

variable "worker_instance_count" {
  description = "Worker Pool instance count (Cloud Run Workers do not auto-scale by default)"
  type        = number
  default     = 1
}

variable "redis_memory_gb" {
  description = "Memorystore Redis memory size in GB"
  type        = number
  default     = 1
}

variable "domain" {
  description = "Base domain for this environment (e.g. staging.praxis.yourdomain.com). Required for TLS cert provisioning. Set to empty string to skip cert creation."
  type        = string
  default     = ""
}

variable "alert_notification_channel" {
  description = "Google Cloud Monitoring notification channel ID for alerts"
  type        = string
  default     = ""
}

################################################################################
# Local values
################################################################################

locals {
  registry_base     = "${var.region}-docker.pkg.dev/${var.artifact_registry_project}/praxis"
  api_image         = "${local.registry_base}/praxis-api:${var.image_tag}"
  realtime_image    = "${local.registry_base}/praxis-realtime:${var.image_tag}"
  worker_image      = "${local.registry_base}/praxis-worker:${var.image_tag}"
  alert_channels    = var.alert_notification_channel != "" ? [var.alert_notification_channel] : []
  domain_configured = var.domain != ""
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
    "servicenetworking.googleapis.com", # required for private Redis peering
    "secretmanager.googleapis.com",
    "cloudtrace.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "cloudbuild.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com", # required for Workload Identity Federation
    "sts.googleapis.com",            # required for Workload Identity Federation
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

# Private services access range — required for Memorystore DIRECT_PEERING
resource "google_compute_global_address" "redis_peering_range" {
  name          = "praxis-${var.environment}-redis-range"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 24
  network       = google_compute_network.praxis.id
}

resource "google_service_networking_connection" "redis_peering" {
  network                 = google_compute_network.praxis.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.redis_peering_range.name]
  depends_on              = [google_project_service.required_apis]
}

resource "google_vpc_access_connector" "praxis" {
  name           = "praxis-${var.environment}"
  region         = var.region
  network        = google_compute_network.praxis.name
  ip_cidr_range  = "10.8.0.0/28"
  min_throughput = 200
  max_throughput = 1000
  depends_on     = [google_project_service.required_apis]
}

################################################################################
# Memorystore Redis (private — not publicly accessible)
################################################################################

resource "google_redis_instance" "praxis" {
  name           = "praxis-${var.environment}"
  memory_size_gb = var.redis_memory_gb
  region         = var.region
  tier           = "BASIC"
  redis_version  = "REDIS_7_2"

  # Private connectivity via VPC peering — Redis is NOT publicly accessible.
  authorized_network = google_compute_network.praxis.id
  connect_mode       = "DIRECT_PEERING"

  # AUTH token (managed separately in Secret Manager)
  auth_enabled = false # set to true and add auth_string when using Memorystore for Redis with AUTH

  transit_encryption_mode = "SERVER_AUTHENTICATION" # TLS in transit

  labels = {
    environment = var.environment
    app         = "praxis"
  }

  depends_on = [google_service_networking_connection.redis_peering]
}

################################################################################
# Service Accounts — one per runtime service (least privilege)
################################################################################

resource "google_service_account" "api" {
  account_id   = "praxis-api-${var.environment}"
  display_name = "PRAXIS API (${var.environment})"
}

resource "google_service_account" "realtime" {
  account_id   = "praxis-realtime-${var.environment}"
  display_name = "PRAXIS Realtime (${var.environment})"
}

resource "google_service_account" "worker" {
  account_id   = "praxis-worker-${var.environment}"
  display_name = "PRAXIS Worker (${var.environment})"
}

resource "google_service_account" "deployer" {
  account_id   = "praxis-deployer-${var.environment}"
  display_name = "PRAXIS GitHub Actions Deployer (${var.environment})"
}

# ── Secret Manager access (each service only accesses its own secrets) ──────

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

# ── Cloud Trace agent (observability) ────────────────────────────────────────

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

resource "google_project_iam_member" "worker_trace_agent" {
  project = var.project_id
  role    = "roles/cloudtrace.agent"
  member  = "serviceAccount:${google_service_account.worker.email}"
}

# ── Deployer: Cloud Run developer + Artifact Registry writer ─────────────────

resource "google_project_iam_member" "deployer_run_developer" {
  project = var.project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_project_iam_member" "deployer_ar_reader" {
  project = var.artifact_registry_project
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_project_iam_member" "deployer_ar_writer" {
  project = var.artifact_registry_project
  role    = "roles/artifactregistry.writer"
  member  = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_project_iam_member" "deployer_service_account_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.deployer.email}"
}

################################################################################
# Workload Identity Federation — GitHub Actions (no long-lived key files)
################################################################################

resource "google_iam_workload_identity_pool" "github" {
  provider                  = google-beta
  workload_identity_pool_id = "github-actions-${var.environment}"
  display_name              = "GitHub Actions (${var.environment})"
  depends_on                = [google_project_service.required_apis]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  provider                           = google-beta
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
    "attribute.ref"        = "assertion.ref"
  }

  # SECURITY: Only tokens from the specific repository can authenticate.
  # This prevents any other GitHub repo from deploying PRAXIS.
  attribute_condition = "attribute.repository == \"${var.github_repository}\""

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# Bind the deployer SA to the WIF pool (only for main branch pushes)
resource "google_service_account_iam_member" "deployer_wif" {
  service_account_id = google_service_account.deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_repository}"
}

################################################################################
# Artifact Registry
################################################################################

resource "google_artifact_registry_repository" "praxis" {
  location      = var.region
  repository_id = "praxis"
  format        = "DOCKER"
  description   = "PRAXIS container images — immutable SHA tags only, no :latest deploys"

  labels = {
    environment = var.environment
    app         = "praxis"
  }

  depends_on = [google_project_service.required_apis]
}

################################################################################
# Cloud Run — API
################################################################################

resource "google_cloud_run_v2_service" "api" {
  name     = "praxis-api"
  location = var.region
  # Traffic must go through the load balancer / Cloud Armor.
  # Direct Cloud Run URL is blocked to prevent bypassing Cloud Armor.
  ingress = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"

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
      image = local.api_image

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

      env {
        name  = "PORT"
        value = "8000"
      }

      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = "praxis-database-url"
            version = var.secret_version
          }
        }
      }

      env {
        name = "REDIS_URL"
        value_source {
          secret_key_ref {
            secret  = "praxis-redis-url"
            version = var.secret_version
          }
        }
      }

      env {
        name = "SUPABASE_URL"
        value_source {
          secret_key_ref {
            secret  = "praxis-supabase-url"
            version = var.secret_version
          }
        }
      }

      env {
        name = "SUPABASE_ANON_KEY"
        value_source {
          secret_key_ref {
            secret  = "praxis-supabase-anon-key"
            version = var.secret_version
          }
        }
      }

      env {
        name = "FERNET_KEY"
        value_source {
          secret_key_ref {
            secret  = "praxis-fernet-key"
            version = var.secret_version
          }
        }
      }

      # Startup probe: must succeed before liveness checks begin.
      # Path matches the actual FastAPI route.
      startup_probe {
        http_get {
          path = "/api/v1/health/live"
          port = 8000
        }
        initial_delay_seconds = 10
        period_seconds        = 5
        failure_threshold     = 12 # 60s total startup time
        timeout_seconds       = 3
      }

      liveness_probe {
        http_get {
          path = "/api/v1/health/live"
          port = 8000
        }
        period_seconds    = 30
        failure_threshold = 3
        timeout_seconds   = 5
      }
    }
  }

  depends_on = [google_project_service.required_apis]
}

################################################################################
# Cloud Run — Realtime Agent (WebSocket)
################################################################################

resource "google_cloud_run_v2_service" "realtime" {
  name     = "praxis-realtime"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"

  template {
    service_account = google_service_account.realtime.email

    scaling {
      # Keep at least 1 instance to avoid cold-start latency on WebSocket connect.
      # Cold starts for the realtime service (with ML models) are ~30-90s.
      min_instance_count = var.realtime_min_instances
      max_instance_count = var.realtime_max_instances
    }

    vpc_access {
      connector = google_vpc_access_connector.praxis.id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    # Max Cloud Run timeout is 3600s. WebSocket clients must handle reconnect.
    timeout = "3600s"

    containers {
      image = local.realtime_image

      resources {
        limits = {
          cpu    = "2000m"
          memory = "2Gi"
        }
        cpu_idle          = false # always-on: realtime audio cannot tolerate CPU throttle
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
        name  = "PORT"
        value = "8080"
      }

      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = "praxis-database-url"
            version = var.secret_version
          }
        }
      }

      env {
        name = "REDIS_URL"
        value_source {
          secret_key_ref {
            secret  = "praxis-redis-url"
            version = var.secret_version
          }
        }
      }

      env {
        name = "SUPABASE_URL"
        value_source {
          secret_key_ref {
            secret  = "praxis-supabase-url"
            version = var.secret_version
          }
        }
      }

      startup_probe {
        http_get {
          path = "/health/live"
          port = 8080
        }
        initial_delay_seconds = 30 # ML model loading takes ~30s
        period_seconds        = 10
        failure_threshold     = 9 # 90s total startup time
        timeout_seconds       = 5
      }

      liveness_probe {
        http_get {
          path = "/health/live"
          port = 8080
        }
        period_seconds    = 30
        failure_threshold = 3
        timeout_seconds   = 5
      }
    }
  }

  depends_on = [google_project_service.required_apis]
}

################################################################################
# Cloud Run Worker (background job processor — Cloud Run Service, not Worker Pool)
#
# Using Cloud Run Service (not Worker Pool) for compatibility with google provider ~> 6.14
# and ARQ's HTTP-based health model.
#
# NOTE: Cloud Run Worker deployments for ARQ use a long-running process that
# polls Redis. The service has no public traffic (ingress=INTERNAL).
# min_instances = worker_instance_count keeps workers always running.
# max_instances = worker_instance_count makes scaling explicit (not automatic).
# See docs/WORKER_SCALING.md.
################################################################################

resource "google_cloud_run_v2_service" "worker" {
  name     = "praxis-worker"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY" # no public traffic; worker only consumes Redis

  template {
    service_account = google_service_account.worker.email

    scaling {
      # Fixed count — ARQ workers do not benefit from request-based autoscaling.
      min_instance_count = var.worker_instance_count
      max_instance_count = var.worker_instance_count
    }

    vpc_access {
      connector = google_vpc_access_connector.praxis.id
      egress    = "PRIVATE_RANGES_ONLY"
    }

    timeout = "3600s" # allow long-running jobs (debrief, embedding batches)

    containers {
      image = local.worker_image

      resources {
        limits = {
          cpu    = "2000m"
          memory = "1Gi"
        }
        cpu_idle = false # workers are always processing; don't throttle CPU
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
            version = var.secret_version
          }
        }
      }

      env {
        name = "REDIS_URL"
        value_source {
          secret_key_ref {
            secret  = "praxis-redis-url"
            version = var.secret_version
          }
        }
      }

      env {
        name = "SUPABASE_URL"
        value_source {
          secret_key_ref {
            secret  = "praxis-supabase-url"
            version = var.secret_version
          }
        }
      }

      env {
        name = "GROQ_API_KEY"
        value_source {
          secret_key_ref {
            secret  = "praxis-groq-api-key"
            version = var.secret_version
          }
        }
      }

      env {
        name = "OPENAI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = "praxis-openai-api-key"
            version = var.secret_version
          }
        }
      }

      env {
        name = "FERNET_KEY"
        value_source {
          secret_key_ref {
            secret  = "praxis-fernet-key"
            version = var.secret_version
          }
        }
      }
    }
  }

  depends_on = [google_project_service.required_apis]
}

################################################################################
# Load Balancer + TLS
# Only created when var.domain is set (non-empty).
################################################################################

resource "google_compute_managed_ssl_certificate" "praxis" {
  count = local.domain_configured ? 1 : 0
  name  = "praxis-${var.environment}"
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

  security_policy = google_compute_security_policy.praxis.id
}

resource "google_compute_backend_service" "realtime" {
  name                  = "praxis-realtime-backend-${var.environment}"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  protocol              = "HTTP2"
  timeout_sec           = 3600

  backend {
    group = google_compute_region_network_endpoint_group.realtime_neg.id
  }

  security_policy = google_compute_security_policy.praxis.id
}

resource "google_compute_url_map" "praxis" {
  name            = "praxis-${var.environment}"
  default_service = google_compute_backend_service.api.id

  dynamic "host_rule" {
    for_each = local.domain_configured ? [1] : []
    content {
      hosts        = ["api.${var.domain}"]
      path_matcher = "api-paths"
    }
  }

  dynamic "host_rule" {
    for_each = local.domain_configured ? [1] : []
    content {
      hosts        = ["realtime.${var.domain}"]
      path_matcher = "realtime-paths"
    }
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
  count            = local.domain_configured ? 1 : 0
  name             = "praxis-${var.environment}-https"
  url_map          = google_compute_url_map.praxis.id
  ssl_certificates = [google_compute_managed_ssl_certificate.praxis[0].id]
}

resource "google_compute_target_http_proxy" "praxis_http_redirect" {
  name    = "praxis-${var.environment}-http-redirect"
  url_map = google_compute_url_map.http_redirect.id
}

resource "google_compute_url_map" "http_redirect" {
  name = "praxis-${var.environment}-http-redirect"
  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}

resource "google_compute_global_forwarding_rule" "https" {
  count                 = local.domain_configured ? 1 : 0
  name                  = "praxis-${var.environment}-https"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  port_range            = "443"
  target                = google_compute_target_https_proxy.praxis[0].id
  ip_address            = google_compute_global_address.praxis.address
}

resource "google_compute_global_forwarding_rule" "http" {
  name                  = "praxis-${var.environment}-http"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  port_range            = "80"
  target                = google_compute_target_http_proxy.praxis_http_redirect.id
  ip_address            = google_compute_global_address.praxis.address
}

################################################################################
# Cloud Armor security policy
################################################################################

resource "google_compute_security_policy" "praxis" {
  name = "praxis-${var.environment}-armor"

  # Default: allow (overridden by more specific rules above)
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

  # Rate limit: 100 requests per IP per 60s
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
    description = "rate limit per IP (100 req/60s)"
  }

  # SQLi protection (pre-configured WAF rule)
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

  # XSS protection
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

  # Large request body limit (protects against oversized payloads)
  # Note: oversized file uploads use a separate /resumes endpoint with its own limit.
  rule {
    action   = "deny(413)"
    priority = "800"
    match {
      expr {
        expression = "int(request.headers['content-length']) > 52428800" # 50 MB
      }
    }
    description = "block oversized request bodies > 50 MB"
  }
}

################################################################################
# Outputs
################################################################################

output "api_cloud_run_url" {
  value       = google_cloud_run_v2_service.api.uri
  description = "Direct Cloud Run URL (bypasses LB/Cloud Armor — use only for health checks from within GCP)"
}

output "realtime_cloud_run_url" {
  value       = google_cloud_run_v2_service.realtime.uri
  description = "Direct Cloud Run URL for realtime service"
}

output "api_url" {
  value       = local.domain_configured ? "https://api.${var.domain}" : "Use api_cloud_run_url (no domain configured)"
  description = "Public API URL (via load balancer)"
}

output "realtime_url" {
  value       = local.domain_configured ? "wss://realtime.${var.domain}" : "Use realtime_cloud_run_url (no domain configured)"
  description = "Public WebSocket URL (via load balancer)"
}

output "redis_host" {
  value       = google_redis_instance.praxis.host
  description = "Memorystore Redis host (private — only accessible from VPC)"
  sensitive   = true
}

output "load_balancer_ip" {
  value       = google_compute_global_address.praxis.address
  description = "External LB IP — configure DNS A records for api.domain and realtime.domain"
}

output "wif_provider_name" {
  value       = google_iam_workload_identity_pool_provider.github.name
  description = "Workload Identity Pool Provider name — use in GitHub Actions workflow"
}

output "deployer_service_account" {
  value       = google_service_account.deployer.email
  description = "Deployer service account email — use in GitHub Actions workflow"
}
