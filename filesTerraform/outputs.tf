###############################################################################
# Salidas de la raíz
###############################################################################

output "vpc_name" {
  description = "Nombre de la VPC creada."
  value       = google_compute_network.this.name
}

output "subnet_name" {
  description = "Nombre de la subred creada."
  value       = google_compute_subnetwork.this.name
}

output "instance_name" {
  description = "Nombre de la instancia de Compute Engine."
  value       = google_compute_instance.postgresql.name
}

output "instance_private_ip" {
  description = "IP privada de la instancia, asignada dentro de la subred."
  value       = google_compute_instance.postgresql.network_interface[0].network_ip
}

output "instance_zone" {
  description = "Zona de la instancia."
  value       = google_compute_instance.postgresql.zone
}

output "pubsub_topic" {
  description = "ID del tópico de eventos."
  value       = google_pubsub_topic.events.id
}

output "pubsub_batch_subscription" {
  description = "ID de la suscripción pull independiente para procesamiento batch."
  value       = google_pubsub_subscription.events_batch.id
}

output "pubsub_stream_subscription" {
  description = "ID de la suscripción pull independiente para procesamiento streaming."
  value       = google_pubsub_subscription.events_streaming.id
}
