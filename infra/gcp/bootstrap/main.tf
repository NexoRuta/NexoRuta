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

variable "project_id" {
  type        = string
  description = "Existing Google Cloud project with active billing."
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

locals {
  state_bucket = "${var.project_id}-tofu-state"
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
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudquotas.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "cloudtrace.googleapis.com",
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

resource "google_service_account" "runtime" {
  account_id   = "nexoruta-demo-runtime"
  display_name = "NexoRuta demo VM runtime"
  depends_on   = [google_project_service.required]
}

resource "google_project_iam_member" "deployer" {
  for_each = toset([
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
    "assertion.ref == 'refs/heads/main'",
    "assertion.sub in ['repo:${var.github_repository}:environment:nexoruta-demo', 'repo:${split("/", var.github_repository)[0]}@${var.github_owner_id}/${split("/", var.github_repository)[1]}@${var.github_repository_id}:environment:nexoruta-demo']",
    "assertion.workflow_ref in ['${var.github_repository}/.github/workflows/publish.yml@refs/heads/main', '${var.github_repository}/.github/workflows/vm-controls.yml@refs/heads/main']",
    "assertion.event_name in ['workflow_dispatch', 'push']",
  ])
  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_member" "github" {
  service_account_id = google_service_account.deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository_id/${var.github_repository_id}"
}

output "github_variables" {
  value = {
    GCP_PROJECT_ID                 = var.project_id
    GCP_REGION                     = var.region
    GCP_ZONE                       = "${var.region}-a"
    GCP_STATE_BUCKET               = google_storage_bucket.state.name
    GCP_DELIVERY_BUCKET            = google_storage_bucket.delivery.name
    GCP_WORKLOAD_IDENTITY_PROVIDER = google_iam_workload_identity_pool_provider.github.name
    GCP_DEPLOY_SERVICE_ACCOUNT     = google_service_account.deployer.email
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
