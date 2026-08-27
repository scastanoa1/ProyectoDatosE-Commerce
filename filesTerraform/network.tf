###############################################################################
# Red: VPC personalizada para Compute Engine. Pub/Sub es administrado y no usa
# subredes ni reglas de firewall.
###############################################################################

resource "google_compute_network" "this" {
  name                    = local.vpc_name
  project                 = var.project_id
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"

  depends_on = [google_project_service.this]
}

resource "google_compute_subnetwork" "this" {
  name          = local.subnet_name
  project       = var.project_id
  region        = var.region
  network       = google_compute_network.this.id
  ip_cidr_range = var.subnet_cidr

  private_ip_google_access = true
}

resource "google_compute_firewall" "allow_iap_ssh" {
  name          = "${local.prefix}-allow-iap-ssh"
  project       = var.project_id
  network       = google_compute_network.this.name
  direction     = "INGRESS"
  priority      = 1000
  source_ranges = ["35.235.240.0/20"]
  target_tags   = ["allow-iap-ssh"]

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}

# Cloud NAT proporciona salida para actualizaciones e instalación de paquetes;
# no asigna una IP pública a la instancia.
resource "google_compute_router" "nat" {
  count = var.enable_cloud_nat ? 1 : 0

  name    = "${local.prefix}-nat-router"
  project = var.project_id
  region  = var.region
  network = google_compute_network.this.id
}

resource "google_compute_router_nat" "this" {
  count = var.enable_cloud_nat ? 1 : 0

  name                               = "${local.prefix}-nat"
  project                            = var.project_id
  region                             = var.region
  router                             = google_compute_router.nat[0].name
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "LIST_OF_SUBNETWORKS"

  subnetwork {
    name                    = google_compute_subnetwork.this.id
    source_ip_ranges_to_nat = ["ALL_IP_RANGES"]
  }
}
