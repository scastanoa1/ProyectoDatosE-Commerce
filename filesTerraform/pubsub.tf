###############################################################################
# Servicio: Pub/Sub
###############################################################################

resource "google_pubsub_topic" "events" {
  name    = local.pubsub_topic_name
  project = var.project_id
  labels  = local.common_labels

  depends_on = [google_project_service.this]
}

resource "google_pubsub_subscription" "events_batch" {
  name                       = local.pubsub_batch_subscription_name
  project                    = var.project_id
  topic                      = google_pubsub_topic.events.id
  labels                     = local.common_labels
  ack_deadline_seconds       = 60
  message_retention_duration = "604800s"
  retain_acked_messages      = false
  filter                     = "attributes.batch = \"true\""

  expiration_policy {
    ttl = ""
  }
}

resource "google_pubsub_subscription" "events_streaming" {
  name                       = local.pubsub_stream_subscription_name
  project                    = var.project_id
  topic                      = google_pubsub_topic.events.id
  labels                     = local.common_labels
  ack_deadline_seconds       = 60
  message_retention_duration = "604800s"
  retain_acked_messages      = false
  filter                     = "attributes.streaming = \"true\""

  expiration_policy {
    ttl = ""
  }
}

resource "google_pubsub_topic_iam_member" "publishers" {
  
  for_each = setunion(
    toset(var.pubsub_publisher_members),
    toset(["serviceAccount:${google_service_account.compute.email}"]),
  )

  project = var.project_id
  topic   = google_pubsub_topic.events.name
  role    = "roles/pubsub.publisher"
  member  = each.value
}

resource "google_pubsub_subscription_iam_member" "batch_subscribers" {
  for_each = toset(var.pubsub_batch_subscriber_members)

  project      = var.project_id
  subscription = google_pubsub_subscription.events_batch.name
  role         = "roles/pubsub.subscriber"
  member       = each.value
}

resource "google_pubsub_subscription_iam_member" "stream_subscribers" {
  for_each = toset(var.pubsub_stream_subscriber_members)

  project      = var.project_id
  subscription = google_pubsub_subscription.events_streaming.name
  role         = "roles/pubsub.subscriber"
  member       = each.value
}
