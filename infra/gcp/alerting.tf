################################################################################
# Phase 111 — Production Alerting
# All alerts are actionable. Thresholds tuned to avoid alert fatigue.
################################################################################

variable "alert_notification_channel" {
  description = "Google Cloud Monitoring notification channel ID for alerts"
  type        = string
  default     = ""
}

locals {
  channels = var.alert_notification_channel != "" ? [var.alert_notification_channel] : []
}

# ── API 5xx spike ─────────────────────────────────────────────────────────────
resource "google_monitoring_alert_policy" "api_5xx" {
  display_name = "[${var.environment}] praxis-api 5xx spike"
  combiner     = "OR"

  conditions {
    display_name = "5xx rate > 1% for 5 minutes"
    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"praxis-api\" AND metric.type=\"run.googleapis.com/request_count\" AND metric.labels.response_code_class=\"5xx\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.01
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = local.channels
  alert_strategy {
    auto_close = "1800s"
  }
}

# ── API latency spike ──────────────────────────────────────────────────────────
resource "google_monitoring_alert_policy" "api_latency" {
  display_name = "[${var.environment}] praxis-api p95 latency > 3s"
  combiner     = "OR"

  conditions {
    display_name = "p95 latency > 3s for 5 minutes"
    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"praxis-api\" AND metric.type=\"run.googleapis.com/request_latencies\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 3000  # ms
      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_DELTA"
        cross_series_reducer = "REDUCE_PERCENTILE_95"
      }
    }
  }

  notification_channels = local.channels
}

# ── Realtime WebSocket errors ─────────────────────────────────────────────────
resource "google_monitoring_alert_policy" "realtime_5xx" {
  display_name = "[${var.environment}] praxis-realtime WebSocket errors > 5%"
  combiner     = "OR"

  conditions {
    display_name = "realtime 5xx > 5% for 5 minutes"
    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"praxis-realtime\" AND metric.type=\"run.googleapis.com/request_count\" AND metric.labels.response_code_class=\"5xx\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0.05
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = local.channels
}

# ── Container crash ───────────────────────────────────────────────────────────
resource "google_monitoring_alert_policy" "container_crash" {
  display_name = "[${var.environment}] Container crash / restart"
  combiner     = "OR"

  conditions {
    display_name = "Any Cloud Run container crashed"
    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/container/instance_count\" AND metric.labels.state=\"crashed\""
      duration        = "0s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MAX"
      }
    }
  }

  notification_channels = local.channels
}

# ── Redis unavailable ─────────────────────────────────────────────────────────
resource "google_monitoring_alert_policy" "redis_unavailable" {
  display_name = "[${var.environment}] Redis/Memorystore unavailable"
  combiner     = "OR"

  conditions {
    display_name = "Redis client errors spike"
    condition_threshold {
      filter          = "resource.type=\"redis_instance\" AND metric.type=\"redis.googleapis.com/server/rejected_connections\""
      duration        = "120s"
      comparison      = "COMPARISON_GT"
      threshold_value = 10
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = local.channels
}

# ── AI budget exceeded ────────────────────────────────────────────────────────
# This alert fires when a custom metric published by the backend exceeds 0.
# The backend emits this metric when BudgetExceeded is raised.
resource "google_monitoring_metric_descriptor" "budget_exceeded" {
  description  = "Count of AI budget exceeded events"
  display_name = "PRAXIS AI Budget Exceeded"
  type         = "custom.googleapis.com/praxis/ai_budget_exceeded"
  metric_kind  = "GAUGE"
  value_type   = "INT64"
  unit         = "1"

  labels {
    key         = "limit_type"
    value_type  = "STRING"
    description = "daily or session"
  }
}

resource "google_monitoring_alert_policy" "budget_exceeded" {
  display_name = "[${var.environment}] AI budget exceeded"
  combiner     = "OR"

  conditions {
    display_name = "AI budget exceeded event > 0"
    condition_threshold {
      filter          = "metric.type=\"custom.googleapis.com/praxis/ai_budget_exceeded\""
      duration        = "0s"
      comparison      = "COMPARISON_GT"
      threshold_value = 0
      aggregations {
        alignment_period   = "300s"
        per_series_aligner = "ALIGN_SUM"
      }
    }
  }

  notification_channels = local.channels
}
