variable "billing_account_id" {
  type        = string
  default     = ""
  description = "Optional billing account ID to create an USD 80/month project alert budget."
}

data "google_project" "current" {
  project_id = var.project_id
}

resource "google_billing_budget" "demo" {
  count           = var.billing_account_id != "" ? 1 : 0
  billing_account = var.billing_account_id
  display_name    = "NexoRuta demo - USD 80 monthly"
  budget_filter {
    projects               = ["projects/${data.google_project.current.number}"]
    calendar_period        = "MONTH"
    credit_types_treatment = "EXCLUDE_ALL_CREDITS"
  }
  amount {
    specified_amount {
      currency_code = "USD"
      units         = "80"
    }
  }
  threshold_rules { threshold_percent = 0.5 }
  threshold_rules { threshold_percent = 0.8 }
  threshold_rules { threshold_percent = 1.0 }
  depends_on = [google_project_service.required]
}
