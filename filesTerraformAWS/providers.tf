provider "aws" {
  region  = var.aws_region
  profile = "terraform-personal"

  default_tags {
    tags = {
      Environment = var.environment
      ManagedBy   = "Terraform"
      Project     = "E-Commerce"
    }
  }
}

