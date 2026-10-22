
# Job ETL inicial para el proyecto E-Commerce
resource "aws_glue_job" "ecommerce_etl" {
  name        = "${var.project_name}-${var.environment}-etl-job"
  description = "Job ETL inicial para el procesamiento de datos de E-Commerce"

  role_arn     = aws_iam_role.glue_job.arn
  glue_version = "5.0"

  worker_type       = "G.1X"
  number_of_workers = 2
  max_retries       = 0
  timeout           = 60

  command {
    name            = "glueetl"
    script_location = "s3://${aws_s3_bucket.lakehouse.bucket}/scripts/ecommerce_etl.py"
    python_version  = "3"
  }

  default_arguments = {
    "--job-language"                     = "python"
    "--TempDir"                          = "s3://${aws_s3_bucket.lakehouse.bucket}/tmp/"
    "--enable-metrics"                   = ""
    "--enable-continuous-cloudwatch-log" = "true"
  }

  execution_property {
    max_concurrent_runs = 1
  }

  tags = {
    Name  = "${var.project_name}-${var.environment}-etl-job"
    Layer = "processing"
  }
}
