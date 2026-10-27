locals {
  nodes = {
    a = { name = google_compute_instance.demo.name, zone = var.zone, instance = google_compute_instance.demo.self_link }
    b = { name = google_compute_instance.secondary.name, zone = var.secondary_zone, instance = google_compute_instance.secondary.self_link }
  }
  web_services = {
    api        = { port = 18080, health_path = "/health/ready", affinity = false }
    admin      = { port = 18081, health_path = "/health/ready", affinity = false }
    backoffice = { port = 18082, health_path = "/health/ready", affinity = false }
    commerce   = { port = 18083, health_path = "/health/ready", affinity = true }
    tracking   = { port = 18084, health_path = "/health/ready", affinity = true }
    monitor    = { port = 13000, health_path = "/api/health", affinity = false }
    mail       = { port = 18025, health_path = "/", affinity = false }
  }
}

resource "google_compute_global_address" "frontend" {
  name = "${local.name}-frontend"
}

resource "google_compute_instance_group" "web" {
  for_each  = local.nodes
  name      = "${local.name}-${each.key}"
  zone      = each.value.zone
  instances = [each.value.instance]
  dynamic "named_port" {
    for_each = local.web_services
    content {
      name = named_port.key
      port = named_port.value.port
    }
  }
}

resource "google_compute_health_check" "web" {
  for_each            = local.web_services
  name                = "${local.name}-${each.key}"
  check_interval_sec  = 10
  timeout_sec         = 5
  healthy_threshold   = 2
  unhealthy_threshold = 2
  http_health_check {
    port         = each.value.port
    request_path = each.value.health_path
    host         = trimprefix(local.endpoints[each.key], "https://")
  }
}

resource "google_compute_backend_service" "web" {
  for_each                        = local.web_services
  name                            = "${local.name}-${each.key}"
  load_balancing_scheme           = "EXTERNAL_MANAGED"
  protocol                        = "HTTP"
  port_name                       = each.key
  timeout_sec                     = each.value.affinity ? 14400 : 300
  connection_draining_timeout_sec = 30
  session_affinity                = each.value.affinity ? "GENERATED_COOKIE" : "NONE"
  affinity_cookie_ttl_sec         = each.value.affinity ? 14400 : 0
  health_checks                   = [google_compute_health_check.web[each.key].id]
  dynamic "backend" {
    for_each = each.key == "mail" ? { a = google_compute_instance_group.web["a"] } : google_compute_instance_group.web
    content {
      group           = backend.value.self_link
      balancing_mode  = "UTILIZATION"
      capacity_scaler = 1
      max_utilization = 0.8
    }
  }
  # LB request logs include full URLs. Tokens embedded in existing tracking
  # links must never enter Cloud Logging; metrics remain available separately.
  log_config {
    enable = false
  }
}

resource "google_compute_url_map" "web" {
  name            = "${local.name}-https"
  default_service = google_compute_backend_service.web["api"].id
  dynamic "host_rule" {
    for_each = local.web_services
    content {
      hosts        = [trimprefix(local.endpoints[host_rule.key], "https://")]
      path_matcher = host_rule.key
    }
  }
  dynamic "path_matcher" {
    for_each = local.web_services
    content {
      name            = path_matcher.key
      default_service = google_compute_backend_service.web[path_matcher.key].id
    }
  }
}

resource "google_compute_managed_ssl_certificate" "web" {
  name = "${local.name}-frontend-${substr(sha256(join(",", values(local.endpoints))), 0, 8)}"
  managed {
    domains = [for endpoint in values(local.endpoints) : trimprefix(endpoint, "https://")]
  }
  lifecycle {
    create_before_destroy = true
  }
}

resource "google_compute_target_https_proxy" "web" {
  name             = "${local.name}-https"
  url_map          = google_compute_url_map.web.id
  ssl_certificates = [google_compute_managed_ssl_certificate.web.id]
}

resource "google_compute_global_forwarding_rule" "https" {
  name                  = "${local.name}-https"
  ip_address            = google_compute_global_address.frontend.address
  port_range            = "443"
  target                = google_compute_target_https_proxy.web.id
  load_balancing_scheme = "EXTERNAL_MANAGED"
}

resource "google_compute_url_map" "redirect" {
  name = "${local.name}-http-redirect"
  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}

resource "google_compute_target_http_proxy" "redirect" {
  name    = "${local.name}-http-redirect"
  url_map = google_compute_url_map.redirect.id
}

resource "google_compute_global_forwarding_rule" "http" {
  name                  = "${local.name}-http"
  ip_address            = google_compute_global_address.frontend.address
  port_range            = "80"
  target                = google_compute_target_http_proxy.redirect.id
  load_balancing_scheme = "EXTERNAL_MANAGED"
}

resource "google_compute_firewall" "load_balancer" {
  name                    = "${local.name}-load-balancer"
  network                 = google_compute_network.demo.name
  source_ranges           = ["35.191.0.0/16", "130.211.0.0/22"]
  target_service_accounts = ["nexoruta-demo-runtime@${var.project_id}.iam.gserviceaccount.com"]
  allow {
    protocol = "tcp"
    ports    = [for service in values(local.web_services) : tostring(service.port)]
  }
}

resource "google_compute_firewall" "shared_services" {
  name                    = "${local.name}-shared-services"
  network                 = google_compute_network.demo.name
  source_ranges           = [google_compute_subnetwork.demo.ip_cidr_range]
  target_service_accounts = ["nexoruta-demo-runtime@${var.project_id}.iam.gserviceaccount.com"]
  allow {
    protocol = "tcp"
    ports    = ["5672", "19092", "27017", "1025", "15692"]
  }
}

output "nodes" {
  value = {
    for key, node in local.nodes : key => {
      name  = node.name
      zone  = node.zone
      group = google_compute_instance_group.web[key].name
    }
  }
}

output "load_balancer_ip" {
  value = google_compute_global_address.frontend.address
}
