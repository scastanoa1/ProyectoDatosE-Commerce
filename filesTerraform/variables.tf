###############################################################################
# Variables de entrada de la raíz
###############################################################################

variable "project_id" {
  description = "ID del proyecto de GCP (no el nombre ni el número)."
  type        = string
}

variable "region" {
  description = "Región por defecto para los recursos regionales."
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "Zona donde se crea la instancia de Compute Engine. Debe pertenecer a region."
  type        = string
  default     = "us-central1-a"
}

variable "environment" {
  description = "Nombre del ambiente: dev, qa o prod."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "qa", "prod"], var.environment)
    error_message = "environment debe ser dev, qa o prod."
  }
}

variable "name_prefix" {
  description = "Prefijo aplicado al nombre de todos los recursos."
  type        = string
  default     = "demo"
}

variable "vpc_name" {
  description = "Nombre base de la VPC personalizada."
  type        = string
  default     = "data-vpc"
}

variable "subnet_name" {
  description = "Nombre base de la subred de Compute Engine."
  type        = string
  default     = "data-subnet"
}

variable "subnet_cidr" {
  description = "Rango IPv4 CIDR de la subred."
  type        = string
  default     = "10.10.0.0/24"
}

variable "instance_name" {
  description = "Nombre base de la instancia que alojará PostgreSQL posteriormente."
  type        = string
  default     = "postgresql"
}

variable "machine_type" {
  description = "Tipo de máquina de Compute Engine; e2-small equilibra coste y memoria para PostgreSQL académico."
  type        = string
  default     = "e2-small"
}

variable "boot_disk_size_gb" {
  description = "Tamaño en GB del disco de arranque persistente."
  type        = number
  default     = 30

  validation {
    condition     = var.boot_disk_size_gb >= 20
    error_message = "boot_disk_size_gb debe ser al menos 20 GB."
  }
}

variable "admin_os_login_members" {
  description = "Miembros IAM (por ejemplo user:alguien@ejemplo.com) con acceso administrativo por OS Login a la VM."
  type        = list(string)
  default     = []
}

variable "iap_tunnel_members" {
  description = "Miembros IAM autorizados a crear túneles TCP mediante IAP hacia la instancia privada."
  type        = list(string)
  default     = []
}

variable "enable_cloud_nat" {
  description = "Crea Cloud NAT para permitir salida a Internet desde la subred sin IP pública en la VM."
  type        = bool
  default     = true
}

variable "pubsub_topic_name" {
  description = "Nombre base del tópico de eventos JSON del simulador."
  type        = string
  default     = "user-events"
}

variable "pubsub_batch_subscription_name" {
  description = "Nombre base de la suscripción pull independiente para procesamiento batch."
  type        = string
  default     = "user-events-batch"
}

variable "pubsub_stream_subscription_name" {
  description = "Nombre base de la suscripción pull independiente para procesamiento streaming."
  type        = string
  default     = "user-events-streaming"
}

variable "pubsub_publisher_members" {
  description = "Miembros IAM adicionales autorizados a publicar eventos en el tópico. La service account de la VM PostgreSQL siempre se incluye automáticamente."
  type        = list(string)
  default     = []
}

variable "pubsub_batch_subscriber_members" {
  description = "Miembros IAM autorizados a consumir desde la suscripción batch."
  type        = list(string)
  default     = []
}

variable "pubsub_stream_subscriber_members" {
  description = "Miembros IAM autorizados a consumir desde la suscripción streaming."
  type        = list(string)
  default     = []
}

variable "enable_apis" {
  description = "Habilita automáticamente las APIs necesarias en el proyecto."
  type        = bool
  default     = true
}
