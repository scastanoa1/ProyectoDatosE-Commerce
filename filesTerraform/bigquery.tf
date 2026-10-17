###############################################################################
# Dataset analítico de BigQuery
###############################################################################

resource "google_bigquery_dataset" "gold" {
  project       = var.project_id
  dataset_id    = "${replace(local.prefix, "-", "_")}_gold"
  friendly_name = "Gold Analytics"
  description   = "Dataset analítico Gold del proyecto E-Commerce."

  location = "US"

  labels = local.common_labels
}