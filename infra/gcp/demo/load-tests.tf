# The generator has its own /26, identity and result bucket. It never shares
# CPU with the application VMs and cannot access SQL, brokers or cache.
resource "google_compute_subnetwork" "load_tests" {
  name                     = "nexoruta-load-tests"
  network                  = google_compute_network.demo.id
  region                   = local.region
  ip_cidr_range            = "10.42.1.0/26"
  private_ip_google_access = true
}

resource "google_compute_firewall" "load_test_metrics" {
  name          = "nexoruta-load-test-metrics"
  network       = google_compute_network.demo.name
  source_ranges = [google_compute_subnetwork.load_tests.ip_cidr_range]
  target_tags   = ["nexoruta-demo-observability"]
  direction     = "INGRESS"
  allow {
    protocol = "tcp"
    ports    = ["9091"]
  }
}

# The runner has one private destination: A's write-only Prometheus gateway.
# Cloud Run Direct VPC egress also gets an explicit deny for RFC1918 destinations
# so it cannot reach SQL, Redis, brokers, Prometheus queries, or other VM ports.
resource "google_compute_firewall" "load_test_metrics_egress" {
  name               = "nexoruta-load-test-metrics-egress"
  network            = google_compute_network.demo.name
  destination_ranges = ["${google_compute_instance.demo.network_interface[0].network_ip}/32"]
  target_tags        = ["nexoruta-load-tests"]
  direction          = "EGRESS"
  priority           = 800
  allow {
    protocol = "tcp"
    ports    = ["9091"]
  }
}

resource "google_compute_firewall" "load_test_private_egress_deny" {
  name               = "nexoruta-load-test-private-egress-deny"
  network            = google_compute_network.demo.name
  destination_ranges = ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
  target_tags        = ["nexoruta-load-tests"]
  direction          = "EGRESS"
  priority           = 900
  deny {
    protocol = "all"
  }
}

locals {
  load_controller_nodes = {
    a = { zone = google_compute_instance.demo.zone, name = google_compute_instance.demo.name }
    b = { zone = google_compute_instance.secondary.zone, name = google_compute_instance.secondary.name }
  }
}

resource "google_compute_instance_iam_member" "load_controller_oslogin" {
  for_each      = local.load_controller_nodes
  project       = var.project_id
  zone          = each.value.zone
  instance_name = each.value.name
  role          = "roles/compute.osAdminLogin"
  member        = "serviceAccount:nexoruta-load-controller@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_iap_tunnel_instance_iam_member" "load_controller_iap" {
  for_each = local.load_controller_nodes
  project  = var.project_id
  zone     = each.value.zone
  instance = each.value.name
  role     = "roles/iap.tunnelResourceAccessor"
  member   = "serviceAccount:nexoruta-load-controller@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_storage_bucket" "load_test_results" {
  name                        = "${var.project_id}-nexoruta-load-results"
  location                    = local.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  lifecycle_rule {
    condition { age = 30 }
    action { type = "Delete" }
  }
  lifecycle { prevent_destroy = true }
}

# Keep runtime-readable control leases outside the OpenTofu state bucket. The
# runner can observe cancellation without being able to read Terraform state.
resource "google_storage_bucket" "load_test_control" {
  name                        = "${var.project_id}-nexoruta-load-control"
  location                    = local.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  lifecycle_rule {
    condition { age = 30 }
    action { type = "Delete" }
  }
  lifecycle { prevent_destroy = true }
}

# Large replay datasets stay out of the 64 KiB Secret Manager payload. The
# objects are immutable and retained until an operator retires the fixture.
resource "google_storage_bucket" "load_test_fixtures" {
  name                        = "${var.project_id}-nexoruta-load-fixtures"
  location                    = local.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  versioning { enabled = true }
  lifecycle { prevent_destroy = true }
}

resource "google_service_account" "load_runner" {
  account_id   = "nexoruta-load-runner"
  display_name = "NexoRuta isolated load test job"
}

resource "google_storage_bucket_iam_member" "load_runner_results" {
  bucket = google_storage_bucket.load_test_results.name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:${google_service_account.load_runner.email}"
}

resource "google_storage_bucket_iam_member" "load_controller_results" {
  bucket = google_storage_bucket.load_test_results.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:nexoruta-load-controller@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_storage_bucket_iam_member" "load_controller_results_writer" {
  bucket = google_storage_bucket.load_test_results.name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:nexoruta-load-controller@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_storage_bucket_iam_member" "load_runner_control" {
  bucket = google_storage_bucket.load_test_control.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.load_runner.email}"
}

resource "google_storage_bucket_iam_member" "load_controller_control" {
  bucket = google_storage_bucket.load_test_control.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:nexoruta-load-controller@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_storage_bucket_iam_member" "load_runner_fixtures" {
  bucket = google_storage_bucket.load_test_fixtures.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.load_runner.email}"
}

resource "google_storage_bucket_iam_member" "load_preparer_fixture_reader" {
  bucket = google_storage_bucket.load_test_fixtures.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:nexoruta-load-preparer@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_storage_bucket_iam_member" "load_preparer_fixture_writer" {
  bucket = google_storage_bucket.load_test_fixtures.name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:nexoruta-load-preparer@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_storage_bucket_iam_member" "load_preparer_lease_reader" {
  bucket = google_storage_bucket.load_test_control.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:nexoruta-load-preparer@${var.project_id}.iam.gserviceaccount.com"
  condition {
    title      = "Load fixture preparer lease only"
    expression = "resource.name == 'projects/_/buckets/${google_storage_bucket.load_test_control.name}/objects/leases/load-test.json'"
  }
}

resource "google_storage_bucket_iam_member" "load_deployer_control" {
  bucket = google_storage_bucket.load_test_control.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:nexoruta-demo-deployer@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_storage_bucket_iam_member" "load_guard_control" {
  bucket = google_storage_bucket.load_test_control.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:nexoruta-demo-guard@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_secret_manager_secret" "load_fixtures" {
  secret_id = "nexoruta-load-fixtures"
  replication {
    auto {}
  }
  lifecycle { prevent_destroy = true }
}

resource "google_secret_manager_secret_iam_member" "load_runner_fixtures" {
  secret_id = google_secret_manager_secret.load_fixtures.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.load_runner.email}"
}

resource "google_secret_manager_secret_iam_member" "load_preparer_fixture_reader" {
  secret_id = google_secret_manager_secret.load_fixtures.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:nexoruta-load-preparer@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_secret_manager_secret_iam_member" "load_preparer_fixture_writer" {
  secret_id = google_secret_manager_secret.load_fixtures.secret_id
  role      = "roles/secretmanager.secretVersionAdder"
  member    = "serviceAccount:nexoruta-load-preparer@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_secret_manager_secret_iam_member" "load_preparer_credentials" {
  secret_id = "projects/${var.project_id}/secrets/nexoruta-load-preparer-credentials"
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:nexoruta-load-preparer@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_secret_manager_secret_iam_member" "load_controller_fixture_versions" {
  for_each  = toset(["roles/secretmanager.viewer"])
  secret_id = google_secret_manager_secret.load_fixtures.secret_id
  role      = each.key
  member    = "serviceAccount:nexoruta-load-controller@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_service_account_iam_member" "load_controller_act_as_runner" {
  service_account_id = google_service_account.load_runner.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:nexoruta-load-controller@${var.project_id}.iam.gserviceaccount.com"
}

resource "google_cloud_run_v2_job" "load_tests" {
  name                = "nexoruta-load-tests"
  location            = local.region
  deletion_protection = true
  template {
    task_count  = 1
    parallelism = 1
    template {
      service_account = google_service_account.load_runner.email
      timeout         = "5400s"
      max_retries     = 0
      containers {
        image   = "us-docker.pkg.dev/cloudrun/container/hello"
        command = ["python3", "/suite/runner.py"]
        env {
          name  = "NEXORUTA_RESULTS_BUCKET"
          value = google_storage_bucket.load_test_results.name
        }
        env {
          name  = "NEXORUTA_LOAD_CONTROL_BUCKET"
          value = google_storage_bucket.load_test_control.name
        }
        env {
          name  = "NEXORUTA_LOAD_FIXTURES_BUCKET"
          value = google_storage_bucket.load_test_fixtures.name
        }
        # A fixture version is attached by the load-tests workflow for each run.
        # Keep it out of the base Job so deployment does not require synthetic
        # users and replay data to exist before the infrastructure can be applied.
        env {
          name  = "NEXORUTA_API_ORIGIN"
          value = local.endpoints["api"]
        }
        env {
          name  = "NEXORUTA_PROMETHEUS_WRITE_URL"
          value = "http://${google_compute_instance.demo.network_interface[0].network_ip}:9091/api/v1/write"
        }
        resources {
          limits = { cpu = "2", memory = "2Gi" }
        }
      }
      vpc_access {
        egress = "PRIVATE_RANGES_ONLY"
        network_interfaces {
          network    = google_compute_network.demo.name
          subnetwork = google_compute_subnetwork.load_tests.name
          tags       = ["nexoruta-load-tests"]
        }
      }
    }
  }
}

resource "google_project_iam_custom_role" "load_job_controller" {
  role_id     = "nexorutaLoadJobController"
  title       = "NexoRuta load job updater and executor"
  permissions = ["run.jobs.get", "run.jobs.update", "run.jobs.run", "run.jobs.runWithOverrides"]
}

resource "google_cloud_run_v2_job_iam_member" "load_test_executor" {
  project  = var.project_id
  location = google_cloud_run_v2_job.load_tests.location
  name     = google_cloud_run_v2_job.load_tests.name
  role     = google_project_iam_custom_role.load_job_controller.name
  member   = "serviceAccount:nexoruta-load-controller@${var.project_id}.iam.gserviceaccount.com"
}

output "load_test_job" {
  value = google_cloud_run_v2_job.load_tests.name
}
output "load_test_results_bucket" {
  value = google_storage_bucket.load_test_results.name
}
output "load_test_control_bucket" {
  value = google_storage_bucket.load_test_control.name
}
output "load_test_fixtures_bucket" {
  value = google_storage_bucket.load_test_fixtures.name
}
