resource "google_compute_global_address" "sql_range" {
  name          = "nexoruta-sql-private"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.demo.id
}

resource "google_service_networking_connection" "sql" {
  network                 = google_compute_network.demo.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.sql_range.name]
}

resource "google_sql_database_instance" "demo" {
  name                = "nexoruta-demo-db"
  region              = local.region
  database_version    = "POSTGRES_18"
  deletion_protection = true
  settings {
    edition                     = "ENTERPRISE"
    tier                        = "db-custom-2-8192"
    availability_type           = "ZONAL"
    activation_policy           = var.running ? "ALWAYS" : "NEVER"
    disk_type                   = "PD_SSD"
    disk_size                   = 20
    disk_autoresize             = true
    disk_autoresize_limit       = 50
    deletion_protection_enabled = true
    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.demo.id
      ssl_mode        = "ENCRYPTED_ONLY"
    }
    backup_configuration {
      enabled                        = true
      point_in_time_recovery_enabled = true
      start_time                     = "06:00"
      location                       = local.region
      transaction_log_retention_days = 3
      backup_retention_settings {
        retained_backups = 7
        retention_unit   = "COUNT"
      }
    }
    maintenance_window {
      day          = 7
      hour         = 6
      update_track = "stable"
    }
    user_labels = { application = "nexoruta", environment = "demo", managed_by = "opentofu" }
  }
  depends_on = [google_service_networking_connection.sql]
}

resource "google_sql_database" "app" {
  name     = "nexoruta"
  instance = google_sql_database_instance.demo.name
}

resource "random_password" "password" {
  for_each = toset(["migrator", "api", "worker", "bootstrap", "rabbit", "mongo", "mail", "admin", "operator", "commerce", "keys_api", "keys_admin", "keys_backoffice", "keys_commerce", "keys_tracking", "monitor", "grafana"])
  length   = 40
  special  = false
}

resource "random_bytes" "key" {
  for_each = toset(["jwt", "tracking", "push", "evidence"])
  length   = 32
}

resource "random_uuid" "organization" {
  for_each = toset(["operator", "commerce", "keys_api", "keys_admin", "keys_backoffice", "keys_commerce", "keys_tracking", "monitor", "grafana"])
}

# The admin is used only by one-shot migrations. Runtime logins are provisioned
# over SQL with NOSUPERUSER/NOBYPASSRLS and never get cloudsqlsuperuser.
resource "google_sql_user" "migrator" {
  name     = "postgres"
  instance = google_sql_database_instance.demo.name
  password = random_password.password["migrator"].result
}

locals {
  domain = var.base_domain != "" ? var.base_domain : "${replace(google_compute_global_address.frontend.address, ".", "-")}.sslip.io"
  endpoints = {
    for name in ["api", "admin", "backoffice", "commerce", "tracking", "mail", "monitor"] : name => "https://${name}.${local.domain}"
  }
}

resource "google_secret_manager_secret_version" "runtime" {
  secret          = "projects/${var.project_id}/secrets/nexoruta-demo-runtime"
  deletion_policy = "ABANDON"
  secret_data = jsonencode({
    project_id       = var.project_id
    region           = local.region
    services_host    = "nexoruta-demo.${var.zone}.c.${var.project_id}.internal"
    frontend_ip      = google_compute_global_address.frontend.address
    nodes            = { a = { name = local.name, zone = var.zone }, b = { name = "${local.name}-b", zone = var.secondary_zone } }
    sql_connection   = google_sql_database_instance.demo.connection_name
    sql_database     = google_sql_database.app.name
    passwords        = { for key, item in random_password.password : key => item.result }
    keys             = { for key, item in random_bytes.key : key => item.base64 }
    organization_ids = { for key, item in random_uuid.organization : key => item.result }
    endpoints        = local.endpoints
    registry         = "${local.region}-docker.pkg.dev/${var.project_id}/nexoruta"
  })
}

resource "google_dns_managed_zone" "demo" {
  count    = var.manage_dns ? 1 : 0
  name     = "nexoruta-demo"
  dns_name = "${var.base_domain}."
  lifecycle {
    precondition {
      condition     = var.base_domain != ""
      error_message = "manage_dns requires an owned base_domain."
    }
  }
}

resource "google_dns_record_set" "app" {
  for_each     = var.manage_dns ? local.endpoints : {}
  managed_zone = google_dns_managed_zone.demo[0].name
  name         = "${each.key}.${var.base_domain}."
  type         = "A"
  ttl          = 60
  rrdatas      = [google_compute_global_address.frontend.address]
}

output "endpoints" { value = local.endpoints }
output "sql_instance" { value = google_sql_database_instance.demo.name }
output "dns_name_servers" { value = var.manage_dns ? google_dns_managed_zone.demo[0].name_servers : [] }
