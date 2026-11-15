terraform {
  required_version = "= 1.13.1"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "= 7.46.1"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "= 7.46.1"
    }
    random = {
      source  = "hashicorp/random"
      version = "= 3.7.2"
    }
  }
}

provider "google" {
  project               = var.project_id
  region                = var.region
  billing_project       = var.project_id
  user_project_override = true
}

provider "google-beta" {
  project               = var.project_id
  region                = var.region
  billing_project       = var.project_id
  user_project_override = true
}

provider "google" {
  alias                 = "firebase"
  project               = var.firebase_project_id
  region                = var.region
  billing_project       = var.firebase_project_id
  user_project_override = true
}

provider "google-beta" {
  alias                 = "firebase"
  project               = var.firebase_project_id
  region                = var.region
  billing_project       = var.firebase_project_id
  user_project_override = true
}

variable "project_id" {
  type        = string
  description = "Existing Google Cloud project with active billing."
}

variable "firebase_project_id" {
  type        = string
  description = "Firebase project used by the Android app and push worker."
  default     = "nexoruta-mobile"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.firebase_project_id))
    error_message = "firebase_project_id must be a Google Cloud project ID."
  }
}

variable "firebase_android_app_id" {
  type        = string
  description = "Existing Firebase Android app ID for uy.nexoruta.repartidor."
  default     = "1:646442506693:android:100447ba9efe843258d3ac"
  validation {
    condition     = can(regex("^1:[0-9]+:android:[a-f0-9]+$", var.firebase_android_app_id))
    error_message = "firebase_android_app_id must be an Android Firebase app ID."
  }
}

variable "region" {
  type    = string
  default = "southamerica-west1"
  validation {
    condition     = var.region == "southamerica-west1"
    error_message = "This demo is located in Santiago, close to Uruguay."
  }
}

variable "github_repository" {
  type    = string
  default = "NexoRuta/NexoRuta"
}

variable "github_repository_id" {
  type        = string
  description = "Immutable numeric GitHub repository ID (gh api repos/NexoRuta/NexoRuta)."
  validation {
    condition     = can(regex("^[0-9]+$", var.github_repository_id))
    error_message = "Supply the numeric repository ID."
  }
}

variable "github_owner_id" {
  type        = string
  description = "Immutable numeric GitHub organization/user ID."
  validation {
    condition     = can(regex("^[0-9]+$", var.github_owner_id))
    error_message = "Supply the numeric repository owner ID."
  }
}

variable "github_environment" {
  type        = string
  description = "GitHub Actions environment included in the immutable OIDC subject."
  default     = "nexoruta-demo"
}

variable "wif_profile" {
  type        = string
  description = "Supported workload identity profile used by the immutable provider condition."
  default     = "demo"
  validation {
    condition     = contains(["demo", "reproduction"], var.wif_profile)
    error_message = "wif_profile must be demo or reproduction."
  }
}

variable "github_refs" {
  type        = list(string)
  description = "Exact Git refs allowed to obtain credentials from this project's provider."
  default     = ["refs/heads/main", "refs/heads/develop"]
  validation {
    condition = length(var.github_refs) == length(toset(var.github_refs)) && (
      toset(var.github_refs) == toset(["refs/heads/main", "refs/heads/develop"]) ||
    toset(var.github_refs) == toset(["refs/heads/main"]))
    error_message = "Only the demo main/develop profile or reproduction main-only profile is supported."
  }
}

variable "github_events" {
  type        = list(string)
  description = "Exact GitHub Actions event types allowed by this project's provider."
  default     = ["workflow_dispatch", "push"]
  validation {
    condition = length(var.github_events) == length(toset(var.github_events)) && (
      toset(var.github_events) == toset(["workflow_dispatch", "push"]) ||
    toset(var.github_events) == toset(["workflow_dispatch"]))
    error_message = "Only the demo workflow_dispatch/push profile or reproduction workflow_dispatch profile is supported."
  }
}

variable "github_workflows" {
  type        = list(string)
  description = "Exact workflow_ref claims allowed by this project's provider."
  default = [
    "NexoRuta/NexoRuta/.github/workflows/publish.yml@refs/heads/main",
    "NexoRuta/NexoRuta/.github/workflows/vm-controls.yml@refs/heads/main",
    "NexoRuta/NexoRuta/.github/workflows/vm-controls.yml@refs/heads/develop",
    "NexoRuta/NexoRuta/.github/workflows/load-tests.yml@refs/heads/main",
    "NexoRuta/NexoRuta/.github/workflows/load-tests.yml@refs/heads/develop",
  ]
  validation {
    condition = length(var.github_workflows) == length(toset(var.github_workflows)) && (
      toset(var.github_workflows) == toset([
        "NexoRuta/NexoRuta/.github/workflows/publish.yml@refs/heads/main",
        "NexoRuta/NexoRuta/.github/workflows/vm-controls.yml@refs/heads/main",
        "NexoRuta/NexoRuta/.github/workflows/vm-controls.yml@refs/heads/develop",
        "NexoRuta/NexoRuta/.github/workflows/load-tests.yml@refs/heads/main",
        "NexoRuta/NexoRuta/.github/workflows/load-tests.yml@refs/heads/develop",
    ]) || toset(var.github_workflows) == toset(["NexoRuta/NexoRuta/.github/workflows/reproduce.yml@refs/heads/main"]))
    error_message = "Only the existing demo workflows or the main-only NFR-14 reproduction workflow is supported."
  }
}

locals {
  state_bucket     = "${var.project_id}-tofu-state"
  github_refs      = join(", ", [for value in var.github_refs : "'${value}'"])
  github_events    = join(", ", [for value in var.github_events : "'${value}'"])
  github_workflows = join(", ", [for value in var.github_workflows : "'${value}'"])
  services = toset([
    "cloudresourcemanager.googleapis.com",
    "compute.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "iap.googleapis.com",
    "oslogin.googleapis.com",
    "sts.googleapis.com",
    "storage.googleapis.com",
    "sqladmin.googleapis.com",
    "servicenetworking.googleapis.com",
    "redis.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudquotas.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "cloudtrace.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudscheduler.googleapis.com",
    "workflows.googleapis.com",
    "workflowexecutions.googleapis.com",
    "dns.googleapis.com",
    "firebase.googleapis.com",
    "firebaseinstallations.googleapis.com",
    "fcm.googleapis.com",
    "apikeys.googleapis.com",
    "billingbudgets.googleapis.com",
  ])
}

resource "google_project_service" "required" {
  for_each           = local.services
  project            = var.project_id
  service            = each.key
  disable_on_destroy = false
}

resource "google_storage_bucket" "state" {
  name                        = local.state_bucket
  location                    = var.region
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  versioning {
    enabled = true
  }
  lifecycle_rule {
    condition {
      num_newer_versions = 10
      with_state         = "ARCHIVED"
    }
    action {
      type = "Delete"
    }
  }
  lifecycle {
    prevent_destroy = true
  }
  depends_on = [google_project_service.required]
}

resource "google_service_account" "deployer" {
  account_id   = "nexoruta-demo-deployer"
  display_name = "GitHub Actions demo VM deployer"
  depends_on   = [google_project_service.required]
}

resource "google_service_account" "load_controller" {
  account_id   = "nexoruta-load-controller"
  display_name = "Orchestrate bounded NexoRuta load tests"
  depends_on   = [google_project_service.required]
}

resource "google_service_account" "load_preparer" {
  account_id   = "nexoruta-load-preparer"
  display_name = "Prepare synthetic application data for OPT-06 load tests"
  depends_on   = [google_project_service.required]
}

resource "google_project_iam_custom_role" "load_fixture_preparer" {
  role_id     = "nexorutaLoadFixturePreparer"
  title       = "Resolve the public demo address for OPT-06 fixture preparation"
  permissions = ["compute.globalAddresses.get"]
}

resource "google_project_iam_member" "load_fixture_preparer" {
  project = var.project_id
  role    = google_project_iam_custom_role.load_fixture_preparer.name
  member  = "serviceAccount:${google_service_account.load_preparer.email}"
}

resource "google_project_iam_custom_role" "load_execution" {
  role_id     = "nexorutaLoadExecution"
  title       = "NexoRuta load execution observer and canceller"
  permissions = ["run.executions.get", "run.executions.list", "run.executions.cancel", "run.operations.get"]
}

resource "google_project_iam_member" "load_controller" {
  for_each = {
    compute_viewer         = "roles/compute.viewer"
    cloudsql_viewer        = "roles/cloudsql.viewer"
    cloudbuild_editor      = "roles/cloudbuild.builds.editor"
    service_usage_consumer = "roles/serviceusage.serviceUsageConsumer"
    load_execution         = google_project_iam_custom_role.load_execution.name
  }
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.load_controller.email}"
}

resource "google_service_account" "runtime" {
  account_id   = "nexoruta-demo-runtime"
  display_name = "NexoRuta demo VM runtime"
  depends_on   = [google_project_service.required]
}

resource "google_project_iam_member" "deployer" {
  for_each = toset([
    "roles/owner",
    "roles/compute.instanceAdmin.v1",
    "roles/compute.networkAdmin",
    "roles/compute.securityAdmin",
    "roles/serviceusage.serviceUsageConsumer",
    "roles/cloudsql.admin",
    "roles/servicenetworking.networksAdmin",
    "roles/cloudbuild.builds.editor",
    "roles/artifactregistry.reader",
    "roles/compute.osAdminLogin",
    "roles/iap.tunnelResourceAccessor",
    "roles/dns.admin",
  ])
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_service_account_iam_member" "act_as_runtime" {
  service_account_id = google_service_account.runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_storage_bucket_iam_member" "state" {
  bucket = google_storage_bucket.state.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_storage_bucket_iam_member" "load_controller_control_objects" {
  bucket = google_storage_bucket.state.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.load_controller.email}"
  condition {
    title      = "NexoRuta load control objects only"
    expression = "resource.name == 'projects/_/buckets/${local.state_bucket}/objects/locks/demo-control.json' || resource.name == 'projects/_/buckets/${local.state_bucket}/objects/leases/demo.json'"
  }
}

resource "google_storage_bucket_iam_member" "load_preparer_control_lock" {
  bucket = google_storage_bucket.state.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.load_preparer.email}"
  condition {
    title      = "Load fixture preparer control lock only"
    expression = "resource.name == 'projects/_/buckets/${local.state_bucket}/objects/locks/demo-control.json'"
  }
}

resource "google_storage_bucket_iam_member" "load_preparer_session_reader" {
  bucket = google_storage_bucket.state.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.load_preparer.email}"
  condition {
    title      = "Load fixture preparer session lease only"
    expression = "resource.name == 'projects/_/buckets/${local.state_bucket}/objects/leases/demo.json'"
  }
}

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "nexoruta-github"
  display_name              = "NexoRuta GitHub Actions"
  depends_on                = [google_project_service.required]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "demo-vm"
  attribute_mapping = {
    "google.subject"                = "assertion.sub"
    "attribute.repository_id"       = "assertion.repository_id"
    "attribute.repository_owner_id" = "assertion.repository_owner_id"
  }
  attribute_condition = join(" && ", [
    "assertion.repository_id == '${var.github_repository_id}'",
    "assertion.repository_owner_id == '${var.github_owner_id}'",
    "assertion.repository == '${var.github_repository}'",
    "assertion.ref in [${local.github_refs}]",
    "assertion.sub == 'repo:${split("/", var.github_repository)[0]}@${var.github_owner_id}/${split("/", var.github_repository)[1]}@${var.github_repository_id}:environment:${var.github_environment}'",
    "assertion.workflow_ref in [${local.github_workflows}]",
    "assertion.event_name in [${local.github_events}]",
  ])
  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
  lifecycle {
    precondition {
      condition = var.wif_profile == "demo" ? (
        var.github_environment == "nexoruta-demo" &&
        toset(var.github_refs) == toset(["refs/heads/main", "refs/heads/develop"]) &&
        toset(var.github_events) == toset(["workflow_dispatch", "push"]) &&
        toset(var.github_workflows) == toset([
          "NexoRuta/NexoRuta/.github/workflows/publish.yml@refs/heads/main",
          "NexoRuta/NexoRuta/.github/workflows/vm-controls.yml@refs/heads/main",
          "NexoRuta/NexoRuta/.github/workflows/vm-controls.yml@refs/heads/develop",
          "NexoRuta/NexoRuta/.github/workflows/load-tests.yml@refs/heads/main",
          "NexoRuta/NexoRuta/.github/workflows/load-tests.yml@refs/heads/develop",
        ])
        ) : (
        var.github_environment == "nexoruta-demo" &&
        toset(var.github_refs) == toset(["refs/heads/main"]) &&
        toset(var.github_events) == toset(["workflow_dispatch"]) &&
        toset(var.github_workflows) == toset(["NexoRuta/NexoRuta/.github/workflows/reproduce.yml@refs/heads/main"])
      )
      error_message = "The WIF profile inputs must exactly match the supported demo or NFR-14 reproduction workflow."
    }
  }
}

resource "google_service_account_iam_member" "github" {
  service_account_id = google_service_account.deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository_id/${var.github_repository_id}"
}

resource "google_service_account_iam_member" "github_load_controller" {
  service_account_id = google_service_account.load_controller.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository_id/${var.github_repository_id}"
}

resource "google_service_account_iam_member" "github_load_preparer" {
  service_account_id = google_service_account.load_preparer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository_id/${var.github_repository_id}"
}

output "github_variables" {
  value = {
    GCP_PROJECT_ID                    = var.project_id
    GCP_REGION                        = var.region
    GCP_ZONE                          = "${var.region}-a"
    GCP_STATE_BUCKET                  = google_storage_bucket.state.name
    GCP_DELIVERY_BUCKET               = google_storage_bucket.delivery.name
    GCP_WORKLOAD_IDENTITY_PROVIDER    = google_iam_workload_identity_pool_provider.github.name
    GCP_DEPLOY_SERVICE_ACCOUNT        = google_service_account.deployer.email
    GCP_LOAD_SERVICE_ACCOUNT          = google_service_account.load_controller.email
    GCP_LOAD_PREPARER_SERVICE_ACCOUNT = google_service_account.load_preparer.email
  }
}

output "bootstrap_configuration" {
  value = {
    project_id           = var.project_id
    project_number       = data.google_project.current.number
    state_bucket         = google_storage_bucket.state.name
    github_repository    = var.github_repository
    github_repository_id = var.github_repository_id
    github_owner_id      = var.github_owner_id
    github_environment   = var.github_environment
    wif_profile          = var.wif_profile
    billing_account_id   = var.billing_account_id
  }
}

variable "secondary_zone" {
  type    = string
  default = "southamerica-west1-b"
  validation {
    condition     = var.secondary_zone == "southamerica-west1-b"
    error_message = "The second demo node uses Santiago zone b."
  }
}
