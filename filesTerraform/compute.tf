###############################################################################
# Compute Engine: servidor económico preparado para instalar PostgreSQL.
###############################################################################

resource "google_service_account" "compute" {
  account_id   = "${var.name_prefix}-${var.environment}-vm"
  display_name = "Cuenta de servicio de la VM PostgreSQL"
  project      = var.project_id

  depends_on = [google_project_service.this]
}

resource "google_project_iam_member" "compute_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.compute.email}"
}

resource "google_project_iam_member" "compute_monitoring" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.compute.email}"
}

resource "google_project_iam_member" "os_login_admins" {
  for_each = toset(var.admin_os_login_members)

  project = var.project_id
  role    = "roles/compute.osAdminLogin"
  member  = each.value
}

resource "google_project_iam_member" "iap_tunnel_users" {
  for_each = toset(var.iap_tunnel_members)

  project = var.project_id
  role    = "roles/iap.tunnelResourceAccessor"
  member  = each.value
}

resource "google_compute_instance" "postgresql" {
  name         = local.instance_name
  project      = var.project_id
  zone         = var.zone
  machine_type = var.machine_type
  tags         = ["postgresql", "allow-iap-ssh"]
  labels       = local.common_labels

  boot_disk {
    auto_delete = true

    initialize_params {
      image = "projects/debian-cloud/global/images/family/debian-12"
      size  = var.boot_disk_size_gb
      type  = "pd-balanced"
    }
  }

  network_interface {
    subnetwork = google_compute_subnetwork.this.id
  }

  metadata = {
    enable-oslogin = "TRUE"
    startup-script = file("${path.module}/startup-script.sh")
  }

  service_account {
    email  = google_service_account.compute.email
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
  }



  depends_on = [
    google_project_iam_member.compute_logging,
    google_project_iam_member.compute_monitoring,
  ]
}
