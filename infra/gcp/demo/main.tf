terraform {
  required_version = "= 1.13.1"
  backend "gcs" {}
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "= 7.46.1"
    }
    random = {
      source  = "hashicorp/random"
      version = "= 3.7.2"
    }
  }
}

variable "project_id" {
  type = string
}

variable "zone" {
  type    = string
  default = "southamerica-west1-a"
  validation {
    condition     = var.zone == "southamerica-west1-a"
    error_message = "The demo and its shutdown guard use southamerica-west1-a, Santiago."
  }
}

variable "base_domain" {
  type        = string
  default     = ""
  description = "Optional owned DNS domain. Empty uses an IP-based sslip.io demo domain."
  validation {
    condition     = var.base_domain == "" || can(regex("^[a-z0-9][a-z0-9.-]*[a-z0-9]$", var.base_domain))
    error_message = "Supply a DNS name without scheme, port or path."
  }
}

variable "manage_dns" {
  type        = bool
  default     = false
  description = "Create a Cloud DNS zone for base_domain; delegate it at the registrar."
}

variable "running" {
  type        = bool
  default     = false
  description = "An explicit start requests RUNNING; every start has a four-hour limit."
}

locals {
  name   = "nexoruta-demo"
  region = join("-", slice(split("-", var.zone), 0, length(split("-", var.zone)) - 1))
}

provider "google" {
  project = var.project_id
  region  = local.region
  zone    = var.zone
}

resource "google_compute_network" "demo" {
  name                    = local.name
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "demo" {
  name                     = local.name
  network                  = google_compute_network.demo.id
  region                   = local.region
  ip_cidr_range            = "10.42.0.0/24"
  private_ip_google_access = true
}

resource "google_compute_firewall" "iap_ssh" {
  name          = "${local.name}-iap-ssh"
  network       = google_compute_network.demo.name
  source_ranges = ["35.235.240.0/20"]
  target_tags   = [local.name]
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}

resource "google_compute_firewall" "web" {
  name          = "${local.name}-web"
  network       = google_compute_network.demo.name
  source_ranges = ["0.0.0.0/0"]
  target_tags   = [local.name]
  allow {
    protocol = "tcp"
    ports    = ["80", "443"]
  }
}

resource "google_compute_address" "demo" {
  name   = local.name
  region = local.region
}

resource "google_compute_disk" "data" {
  name                   = "${local.name}-data"
  type                   = "hyperdisk-balanced"
  zone                   = var.zone
  size                   = 80
  provisioned_iops       = 3000
  provisioned_throughput = 140
  lifecycle {
    prevent_destroy = true
  }
}

resource "google_compute_instance" "demo" {
  name                      = local.name
  zone                      = var.zone
  machine_type              = "n4-highcpu-8"
  desired_status            = var.running ? "RUNNING" : "TERMINATED"
  allow_stopping_for_update = true
  tags                      = [local.name]
  labels = {
    application = "nexoruta"
    environment = "demo"
    managed_by  = "opentofu"
  }

  boot_disk {
    interface = "NVME"
    initialize_params {
      image                  = "debian-cloud/debian-12"
      type                   = "hyperdisk-balanced"
      size                   = 20
      provisioned_iops       = 3000
      provisioned_throughput = 140
    }
  }
  attached_disk {
    source      = google_compute_disk.data.id
    device_name = "nexoruta-data"
  }
  network_interface {
    subnetwork = google_compute_subnetwork.demo.id
    access_config {
      nat_ip = google_compute_address.demo.address
    }
  }
  service_account {
    email  = "nexoruta-demo-runtime@${var.project_id}.iam.gserviceaccount.com"
    scopes = ["cloud-platform"]
  }
  metadata = {
    enable-oslogin         = "TRUE"
    block-project-ssh-keys = "TRUE"
    startup-script         = file("${path.module}/startup.sh")
    shutdown-script        = "#!/bin/bash\nsystemctl stop docker.service containerd.service || true\n"
  }
  scheduling {
    provisioning_model          = "STANDARD"
    automatic_restart           = false
    on_host_maintenance         = "TERMINATE"
    instance_termination_action = "STOP"
    max_run_duration {
      seconds = 14400
    }
  }
  depends_on = [google_secret_manager_secret_version.runtime, google_sql_user.migrator]
}

output "vm_name" {
  value = google_compute_instance.demo.name
}

output "public_ip" {
  value = google_compute_address.demo.address
}

output "zone" {
  value = var.zone
}
