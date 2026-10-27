resource "google_storage_bucket" "delivery" {
  name                        = "${var.project_id}-nexoruta-delivery"
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  lifecycle_rule {
    condition { age = 30 }
    action { type = "Delete" }
  }
  depends_on = [google_project_service.required]
}

resource "google_artifact_registry_repository" "containers" {
  location      = var.region
  repository_id = "nexoruta"
  format        = "DOCKER"
  docker_config { immutable_tags = true }
  depends_on = [google_project_service.required]
}

resource "google_service_account" "builder" {
  account_id   = "nexoruta-demo-builder"
  display_name = "NexoRuta Cloud Build"
  depends_on   = [google_project_service.required]
}

resource "google_service_account_iam_member" "act_as_builder" {
  service_account_id = google_service_account.builder.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_project_iam_member" "builder_logs" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.builder.email}"
}

resource "google_artifact_registry_repository_iam_member" "builder" {
  location   = var.region
  repository = google_artifact_registry_repository.containers.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.builder.email}"
}

resource "google_artifact_registry_repository_iam_member" "runtime" {
  location   = var.region
  repository = google_artifact_registry_repository.containers.name
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_storage_bucket_iam_member" "delivery_deployer" {
  bucket = google_storage_bucket.delivery.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_storage_bucket_iam_member" "delivery_reader" {
  for_each = {
    runtime = google_service_account.runtime.email
    builder = google_service_account.builder.email
  }
  bucket = google_storage_bucket.delivery.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${each.value}"
}

resource "google_secret_manager_secret" "config" {
  for_each  = toset(["nexoruta-demo-runtime", "nexoruta-demo-integrations", "nexoruta-mobile-config", "nexoruta-mobile-keystore", "nexoruta-mobile-signing-password"])
  secret_id = each.key
  replication {
    user_managed {
      replicas { location = var.region }
    }
  }
  depends_on = [google_project_service.required]
}

resource "google_secret_manager_secret_version" "integrations" {
  secret      = google_secret_manager_secret.config["nexoruta-demo-integrations"].id
  secret_data = jsonencode({ smtp_host = "mailpit", smtp_port = 1025, smtp_ssl = false, smtp_username = "", smtp_password = "", smtp_from = "demo@nexoruta.test", geoapify_api_key = "", mapbox_public_token = "" })
}

resource "google_secret_manager_secret_iam_member" "runtime" {
  for_each  = { for name, secret in google_secret_manager_secret.config : name => secret if contains(["nexoruta-demo-runtime", "nexoruta-demo-integrations"], name) }
  secret_id = each.value.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_secret_manager_secret_iam_member" "deployer" {
  for_each  = google_secret_manager_secret.config
  secret_id = each.value.secret_id
  role      = "roles/secretmanager.secretVersionManager"
  member    = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_secret_manager_secret_iam_member" "mobile_reader" {
  for_each  = toset(["nexoruta-mobile-config", "nexoruta-mobile-keystore", "nexoruta-mobile-signing-password"])
  secret_id = google_secret_manager_secret.config[each.key].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.deployer.email}"
}

resource "random_password" "android_signing" {
  length  = 40
  special = false
}

resource "google_secret_manager_secret_version" "android_signing" {
  secret      = google_secret_manager_secret.config["nexoruta-mobile-signing-password"].id
  secret_data = random_password.android_signing.result
}

resource "google_project_iam_member" "runtime_sql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_project_iam_member" "runtime_push" {
  project = var.project_id
  role    = "roles/firebasecloudmessaging.admin"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_firebase_project" "demo" {
  provider   = google-beta
  project    = var.project_id
  depends_on = [google_project_service.required]
}

resource "google_firebase_android_app" "demo" {
  provider     = google-beta
  project      = var.project_id
  display_name = "NexoRuta Demo"
  package_name = "uy.nexoruta.repartidor"
  api_key_id   = google_apikeys_key.mobile.uid
  depends_on   = [google_firebase_project.demo]
}

resource "google_apikeys_key" "mobile" {
  name         = "nexoruta-mobile"
  display_name = "NexoRuta Firebase client"
  restrictions {
    api_targets { service = "firebaseinstallations.googleapis.com" }
    api_targets { service = "fcmregistrations.googleapis.com" }
  }
  depends_on = [google_firebase_project.demo]
}

data "google_firebase_android_app_config" "demo" {
  provider = google-beta
  project  = var.project_id
  app_id   = google_firebase_android_app.demo.app_id
}

resource "google_secret_manager_secret_version" "mobile" {
  secret      = google_secret_manager_secret.config["nexoruta-mobile-config"].id
  secret_data = base64decode(data.google_firebase_android_app_config.demo.config_file_contents)
}

# Hosting identity is generated once by the serialized manual deployment job.
resource "google_secret_manager_secret" "hosting" {
  secret_id = "nexoruta-demo-hosting"
  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }
  depends_on = [google_project_service.required]
}
resource "google_secret_manager_secret_iam_member" "hosting_runtime" {
  secret_id = google_secret_manager_secret.hosting.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.runtime.email}"
}
resource "google_secret_manager_secret_iam_member" "hosting_deployer" {
  for_each  = toset(["roles/secretmanager.secretAccessor", "roles/secretmanager.secretVersionAdder", "roles/secretmanager.viewer"])
  secret_id = google_secret_manager_secret.hosting.id
  role      = each.key
  member    = "serviceAccount:${google_service_account.deployer.email}"
}
resource "google_project_iam_member" "runtime_observability" {
  for_each = toset(["roles/logging.logWriter", "roles/monitoring.metricWriter", "roles/cloudtrace.agent", "roles/monitoring.viewer"])
  project  = var.project_id
  role     = each.key
  member   = "serviceAccount:${google_service_account.runtime.email}"
}
resource "google_project_iam_member" "deployer_monitoring" {
  project = var.project_id
  role    = "roles/monitoring.editor"
  member  = "serviceAccount:${google_service_account.deployer.email}"
}
