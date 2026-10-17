
variable "aws_region" {
  description = "Región de AWS donde se desplegará la infraestructura."
  type        = string
  default     = "us-east-2"
}

variable "environment" {
  description = "Entorno de despliegue."
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Nombre del proyecto."
  type        = string
  default     = "ecommerce"
}
