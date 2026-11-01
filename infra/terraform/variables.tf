################################################################################
# PRAXIS InterviewOS — Master Terraform Variables
################################################################################

variable "project_id" {
  description = "GCP Project ID for deployment"
  type        = string
}

variable "region" {
  description = "GCP primary region (default: asia-south1)"
  type        = string
  default     = "asia-south1"
}

variable "environment" {
  description = "Environment identifier (staging or production)"
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be either staging or production."
  }
}

variable "artifact_registry_project" {
  description = "Project ID hosting Google Artifact Registry"
  type        = string
}

variable "github_repository" {
  description = "GitHub repository owner and name (e.g. AMIYA8597/praxis-interviewOS)"
  type        = string
  default     = "AMIYA8597/praxis-interviewOS"
}

variable "image_tag" {
  description = "Container image tag or SHA digest"
  type        = string
}

variable "secret_version" {
  description = "Pinned secret version in Secret Manager"
  type        = string
  default     = "1"
}

variable "db_pool_size" {
  description = "Maximum database connection pool size per container instance"
  type        = number
  default     = 2
}

variable "db_max_overflow" {
  description = "Maximum overflow database connections per container instance"
  type        = number
  default     = 3
}

variable "api_min_instances" {
  description = "Minimum instances for API service"
  type        = number
  default     = 1
}

variable "api_max_instances" {
  description = "Maximum instances for API service"
  type        = number
  default     = 10
}

variable "realtime_min_instances" {
  description = "Minimum instances for realtime gateway"
  type        = number
  default     = 1
}

variable "realtime_max_instances" {
  description = "Maximum instances for realtime gateway"
  type        = number
  default     = 5
}

variable "worker_instance_count" {
  description = "Instance count for background ARQ workers"
  type        = number
  default     = 2
}

variable "redis_memory_gb" {
  description = "Allocated memory in GB for Memorystore Redis instance"
  type        = number
  default     = 1
}

variable "domain" {
  description = "Custom domain for external ingress"
  type        = string
  default     = ""
}

variable "alert_notification_channel" {
  description = "Notification channel ID for Cloud Monitoring alerting"
  type        = string
  default     = ""
}
