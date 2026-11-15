terraform {
  required_version = "= 1.13.1"
  backend "gcs" {}
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "= 7.46.1"
    }
  }
}

provider "google" {
  billing_project       = var.control_project_id
  user_project_override = true
}

variable "control_project_id" {
  type        = string
  description = "Existing external project used only for Google API quota and billing attribution."
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.control_project_id))
    error_message = "control_project_id must be an explicit valid Google Cloud project ID."
  }
}

variable "project_id" {
  type        = string
  description = "Unique project ID derived from the NFR-14 reproduction run ID."
  validation {
    condition     = can(regex("^nfr14-r-[a-f0-9]{16}$", var.project_id))
    error_message = "project_id must use the NFR-14 reproduction run profile."
  }
}

variable "run_id" {
  type        = string
  description = "Immutable 32-character NFR-14 reproduction identity."
  validation {
    condition     = can(regex("^[a-f0-9]{32}$", var.run_id))
    error_message = "run_id must be 32 lowercase hexadecimal characters."
  }
}

variable "parent" {
  type        = string
  description = "Explicit approved organization/ or folders/ parent."
  validation {
    condition     = can(regex("^(organizations|folders)/[0-9]+$", var.parent))
    error_message = "parent must be an explicit organizations/<id> or folders/<id> resource name."
  }
}

variable "billing_account_id" {
  type        = string
  description = "Explicit approved billing account ID; never inferred from local gcloud configuration."
  validation {
    condition     = can(regex("^[A-Z0-9-]{6,30}$", var.billing_account_id))
    error_message = "billing_account_id must be the approved public billing account ID."
  }
}

variable "approved_budget_usd" {
  type        = number
  description = "Approved monthly alert budget for this disposable project, in whole USD."
  validation {
    condition     = var.approved_budget_usd >= 1 && var.approved_budget_usd <= 10000 && floor(var.approved_budget_usd) == var.approved_budget_usd
    error_message = "approved_budget_usd must be an explicitly approved whole-dollar amount from 1 to 10000."
  }
}

locals {
  parent_is_folder = startswith(var.parent, "folders/")
  parent_id        = trimprefix(var.parent, local.parent_is_folder ? "folders/" : "organizations/")
}

resource "google_project" "reproduction" {
  name                = "NexoRuta NFR-14 reproduction ${substr(var.run_id, 0, 8)}"
  project_id          = var.project_id
  org_id              = local.parent_is_folder ? null : local.parent_id
  folder_id           = local.parent_is_folder ? local.parent_id : null
  billing_account     = var.billing_account_id
  auto_create_network = false
  deletion_policy     = "DELETE"
  labels = {
    nfr14_owner = "nfr-14"
    nfr14_run   = substr(var.run_id, 0, 16)
  }
}

data "google_project" "reproduction" {
  project_id = google_project.reproduction.project_id
  depends_on = [google_project.reproduction]
}

resource "google_billing_budget" "reproduction" {
  billing_account = var.billing_account_id
  display_name    = "NFR-14 reproduction ${substr(var.run_id, 0, 8)}"

  budget_filter {
    projects               = ["projects/${data.google_project.reproduction.number}"]
    calendar_period        = "MONTH"
    credit_types_treatment = "EXCLUDE_ALL_CREDITS"
  }

  amount {
    specified_amount {
      currency_code = "USD"
      units         = tostring(var.approved_budget_usd)
    }
  }

  threshold_rules { threshold_percent = 0.5 }
  threshold_rules { threshold_percent = 0.8 }
  threshold_rules { threshold_percent = 1.0 }
  depends_on = [google_project.reproduction]
}

output "project_id" {
  value = google_project.reproduction.project_id
}

output "project_number" {
  value = data.google_project.reproduction.number
}

output "budget_id" {
  value = google_billing_budget.reproduction.name
}

output "budget_filter_project_number" {
  value = data.google_project.reproduction.number
}
