variable "monitoring_notification_channels" {
  type        = list(string)
  default     = []
  description = "Existing Cloud Monitoring channel resource names. Empty keeps incidents visible in Cloud Monitoring without external notifications."
}

locals {
  monitoring_metrics = {
    service_up                  = ["service"]
    container_up                = ["service"]
    container_restarts          = ["service"]
    container_oom               = ["service"]
    outbox_pending              = ["transport", "status"]
    outbox_oldest_seconds       = ["transport", "status"]
    kafka_lag                   = []
    rabbit_queue_pending        = []
    rabbit_queue_unacknowledged = []
    session_remaining           = []
    last_sample                 = []
    applied_release             = ["release"]
    collection_success          = ["collector"]
    node_running                = []
    session_active              = []
  }
  capacity_alerts = {
    cpu = {
      metric    = "compute.googleapis.com/instance/cpu/utilization"
      threshold = 0.85
      extra     = ""
      label     = "CPU sobre 85%"
    }
    memory = {
      metric    = "agent.googleapis.com/memory/percent_used"
      threshold = 85
      extra     = " AND metric.labels.state = \"used\""
      label     = "RAM sobre 85%"
    }
    disk = {
      metric    = "agent.googleapis.com/disk/percent_used"
      threshold = 80
      extra     = " AND metric.labels.state = \"used\""
      label     = "Disco sobre 80%"
    }
  }
}

resource "google_monitoring_metric_descriptor" "demo" {
  for_each     = local.monitoring_metrics
  project      = var.project_id
  type         = "custom.googleapis.com/nexoruta/${each.key}"
  display_name = "NexoRuta ${each.key}"
  metric_kind  = "GAUGE"
  value_type   = "DOUBLE"
  unit         = contains(["outbox_oldest_seconds", "session_remaining", "last_sample"], each.key) ? "s" : "1"

  dynamic "labels" {
    for_each = concat(["node"], each.value)
    content {
      key        = labels.value
      value_type = "STRING"
    }
  }
}

# The guard emits these global-resource signals even when a VM cannot emit
# metrics. Each policy selects the same node on both conditions explicitly.
resource "google_monitoring_alert_policy" "node_down" {
  for_each              = toset(["a", "b"])
  project               = var.project_id
  display_name          = "NexoRuta: VM ${upper(each.key)} detenida durante la sesión"
  combiner              = "AND_WITH_MATCHING_RESOURCE"
  notification_channels = var.monitoring_notification_channels

  dynamic "conditions" {
    for_each = {
      node_running   = { comparison = "COMPARISON_LT", threshold = 1, aligner = "ALIGN_MAX" }
      session_active = { comparison = "COMPARISON_GT", threshold = 0, aligner = "ALIGN_MIN" }
    }
    content {
      display_name = conditions.key
      condition_threshold {
        filter                  = "resource.type = \"global\" AND metric.type = \"custom.googleapis.com/nexoruta/${conditions.key}\" AND metric.labels.node = \"${each.key}\""
        comparison              = conditions.value.comparison
        threshold_value         = conditions.value.threshold
        duration                = "120s"
        evaluation_missing_data = "EVALUATION_MISSING_DATA_INACTIVE"
        aggregations {
          alignment_period   = "60s"
          per_series_aligner = conditions.value.aligner
        }
      }
    }
  }
  depends_on = [google_monitoring_metric_descriptor.demo]
}

resource "google_monitoring_alert_policy" "service_down" {
  project               = var.project_id
  display_name          = "NexoRuta: servicio no disponible durante la sesión"
  combiner              = "AND_WITH_MATCHING_RESOURCE"
  notification_channels = var.monitoring_notification_channels

  dynamic "conditions" {
    for_each = {
      service_up        = { comparison = "COMPARISON_LT", threshold = 1, aligner = "ALIGN_MAX" }
      session_remaining = { comparison = "COMPARISON_GT", threshold = 0, aligner = "ALIGN_MIN" }
    }
    content {
      display_name = conditions.key
      condition_threshold {
        filter                  = "resource.type = \"gce_instance\" AND metric.type = \"custom.googleapis.com/nexoruta/${conditions.key}\""
        comparison              = conditions.value.comparison
        threshold_value         = conditions.value.threshold
        duration                = "120s"
        evaluation_missing_data = "EVALUATION_MISSING_DATA_INACTIVE"
        aggregations {
          alignment_period   = "60s"
          per_series_aligner = conditions.value.aligner
        }
      }
    }
  }
  depends_on = [google_monitoring_metric_descriptor.demo]
}

resource "google_monitoring_alert_policy" "capacity" {
  for_each              = local.capacity_alerts
  project               = var.project_id
  display_name          = "NexoRuta: ${each.value.label} durante la sesión"
  combiner              = "AND_WITH_MATCHING_RESOURCE"
  notification_channels = var.monitoring_notification_channels

  conditions {
    display_name = each.value.label
    condition_threshold {
      filter                  = "resource.type = \"gce_instance\" AND metric.type = \"${each.value.metric}\"${each.value.extra}"
      comparison              = "COMPARISON_GT"
      threshold_value         = each.value.threshold
      duration                = "120s"
      evaluation_missing_data = "EVALUATION_MISSING_DATA_INACTIVE"
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }
  conditions {
    display_name = "Sesión vigente"
    condition_threshold {
      filter                  = "resource.type = \"gce_instance\" AND metric.type = \"custom.googleapis.com/nexoruta/session_remaining\""
      comparison              = "COMPARISON_GT"
      threshold_value         = 0
      duration                = "120s"
      evaluation_missing_data = "EVALUATION_MISSING_DATA_INACTIVE"
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MIN"
      }
    }
  }
  depends_on = [google_monitoring_metric_descriptor.demo]
}
