
# Base de datos lógica del catálogo de AWS Glue
resource "aws_glue_catalog_database" "ecommerce" {
  name        = "${var.project_name}_${var.environment}"
  description = "Catalogo de datos del proyecto E-Commerce para el entorno ${var.environment}"
}
