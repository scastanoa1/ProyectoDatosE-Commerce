###############################################################################
# Configuración del provider de Google Cloud
# Las credenciales se toman de Application Default Credentials (ADC),
# es decir de: gcloud auth application-default login
###############################################################################

provider "google" {
  project = var.project_id
  region  = var.region

  default_labels = local.common_labels
}
