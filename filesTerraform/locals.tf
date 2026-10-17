###############################################################################
# Valores calculados y nombres de recursos
###############################################################################

locals {
  prefix = "${var.name_prefix}-${var.environment}"

  common_labels = {
    environment = var.environment
    managed_by  = "terraform"
    application = var.name_prefix
  }

  vpc_name                        = "${local.prefix}-${var.vpc_name}"
  subnet_name                     = "${local.prefix}-${var.subnet_name}"
  instance_name                   = "${local.prefix}-${var.instance_name}"
  pubsub_topic_name               = "${local.prefix}-${var.pubsub_topic_name}"
  pubsub_batch_subscription_name  = "${local.prefix}-${var.pubsub_batch_subscription_name}"
  pubsub_stream_subscription_name = "${local.prefix}-${var.pubsub_stream_subscription_name}"
}
