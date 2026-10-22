
# Rol de ejecución para los jobs de AWS Glue
resource "aws_iam_role" "glue_job" {
  name = "${var.project_name}-${var.environment}-glue-job-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Effect = "Allow"

        Principal = {
          Service = "glue.amazonaws.com"
        }

        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name  = "${var.project_name}-${var.environment}-glue-job-role"
    Layer = "processing"
  }
}

# Permisos administrados de AWS para ejecución básica de Glue
resource "aws_iam_role_policy_attachment" "glue_service_role" {
  role       = aws_iam_role.glue_job.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

# Permisos de lectura y escritura sobre el bucket del proyecto
resource "aws_iam_role_policy" "glue_s3_access" {
  name = "${var.project_name}-${var.environment}-glue-s3-access"
  role = aws_iam_role.glue_job.id

  policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Effect = "Allow"

        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]

        Resource = [
          aws_s3_bucket.lakehouse.arn
        ]
      },
      {
        Effect = "Allow"

        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]

        Resource = [
          "${aws_s3_bucket.lakehouse.arn}/*"
        ]
      }
    ]
  })
}
