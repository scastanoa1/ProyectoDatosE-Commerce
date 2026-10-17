###############################################################################
# Versiones de Terraform y de los providers
###############################################################################

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }

  # Estado remoto opcional en un bucket GCS existente y gestionado por separado.
  # Descomenta y ejecuta: terraform init -migrate-state
  #
  backend "gcs" {
    bucket = "project-174e1e0a-685b-4103-a18-tfstate"
    prefix = "infra/dev"
  }
}
