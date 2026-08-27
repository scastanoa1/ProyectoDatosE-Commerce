###############################################################################
# Habilitación de las APIs requeridas
# Sin estas APIs activas, los recursos fallan con error 403 SERVICE_DISABLED.
###############################################################################

locals {
  required_apis = [
    "compute.googleapis.com",
    "iap.googleapis.com",
    "pubsub.googleapis.com",
    "iam.googleapis.com",
    "cloudresourcemanager.googleapis.com",
  ]
}

resource "google_project_service" "this" {
  for_each = var.enable_apis ? toset(local.required_apis) : toset([])

  project = var.project_id
  service = each.value

  # No deshabilitamos las APIs al destruir: otros recursos podrían usarlas.
  disable_on_destroy         = false
  disable_dependent_services = false
}
