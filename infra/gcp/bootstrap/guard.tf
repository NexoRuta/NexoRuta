resource "google_service_account" "guard" {
  account_id   = "nexoruta-demo-guard"
  display_name = "Stop expired demo sessions"
  depends_on   = [google_project_service.required]
}

resource "google_project_iam_custom_role" "guard" {
  role_id     = "nexorutaDemoGuard"
  title       = "NexoRuta demo session guard"
  permissions = ["compute.instances.get", "compute.instances.stop"]
}

resource "google_project_iam_member" "guard" {
  project = var.project_id
  role    = google_project_iam_custom_role.guard.name
  member  = "serviceAccount:${google_service_account.guard.email}"
}

resource "google_storage_bucket_iam_member" "guard" {
  bucket = google_storage_bucket.state.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.guard.email}"
}

resource "google_workflows_workflow" "guard" {
  name            = "nexoruta-demo-guard"
  region          = var.region
  service_account = google_service_account.guard.email
  source_contents = templatefile("${path.module}/guard.yaml.tftpl", {
    project_id     = var.project_id
    zone           = "${var.region}-a"
    secondary_zone = var.secondary_zone
    state_bucket   = google_storage_bucket.state.name
  })
  depends_on = [google_project_service.required, google_project_iam_member.guard]
}

resource "google_service_account" "scheduler" {
  account_id = "nexoruta-demo-scheduler"
  depends_on = [google_project_service.required]
}

resource "google_project_iam_member" "scheduler" {
  project = var.project_id
  role    = "roles/workflows.invoker"
  member  = "serviceAccount:${google_service_account.scheduler.email}"
}

resource "google_cloud_scheduler_job" "guard" {
  name = "nexoruta-demo-guard"
  # Scheduler is not available in Santiago. Only this control-plane timer runs
  # in Sao Paulo; the workflow, VM, SQL, images and data remain in Santiago.
  region           = "southamerica-east1"
  schedule         = "* * * * *"
  time_zone        = "America/Montevideo"
  attempt_deadline = "180s"
  http_target {
    http_method = "POST"
    uri         = "https://workflowexecutions.googleapis.com/v1/${google_workflows_workflow.guard.id}/executions"
    body        = base64encode("{}")
    headers     = { "Content-Type" = "application/json" }
    oauth_token { service_account_email = google_service_account.scheduler.email }
  }
  depends_on = [google_project_iam_member.scheduler]
}

resource "google_project_iam_member" "guard_metrics" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.guard.email}"
}
