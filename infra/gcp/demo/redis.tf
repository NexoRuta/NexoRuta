# The sole Redis listener belongs to VM B. Both application VMs can reach it
# over the private subnet; no load-balancer or internet source is permitted.
resource "google_compute_firewall" "redis_on_b" {
  name        = "${local.name}-redis-b"
  network     = google_compute_network.demo.name
  source_tags = [local.name]
  target_tags = ["nexoruta-cache-b"]
  allow {
    protocol = "tcp"
    ports    = ["6378"]
  }
}
