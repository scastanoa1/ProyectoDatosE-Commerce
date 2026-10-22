
# ============================================================
# 1. Actividad reciente de usuarios
# ============================================================

resource "aws_dynamodb_table" "user_recent_activity" {
  name         = "user_recent_activity"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_key"
  range_key    = "sk"

  attribute {
    name = "user_key"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }
}

# ============================================================
# 2. Recomendaciones personalizadas
# ============================================================

resource "aws_dynamodb_table" "user_recommendations" {
  name         = "user_recommendations"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_key"
  range_key    = "placement"

  attribute {
    name = "user_key"
    type = "S"
  }

  attribute {
    name = "placement"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }
}

# ============================================================
# 3. Métricas de productos en tiempo real
# ============================================================

resource "aws_dynamodb_table" "product_realtime" {
  name         = "product_realtime"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "product_id"

  attribute {
    name = "product_id"
    type = "S"
  }
}

# ============================================================
# 4. Productos en tendencia
# ============================================================

resource "aws_dynamodb_table" "trending" {
  name         = "trending"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "scope"
  range_key    = "window"

  attribute {
    name = "scope"
    type = "S"
  }

  attribute {
    name = "window"
    type = "S"
  }
}

# ============================================================
# 5. Sesiones de checkout
# ============================================================

resource "aws_dynamodb_table" "checkout_sessions" {
  name         = "checkout_sessions"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_key"

  attribute {
    name = "user_key"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }
}

# ============================================================
# 6. Estado de riesgo de entidades
# ============================================================

resource "aws_dynamodb_table" "risk_status" {
  name         = "risk_status"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "entity"

  attribute {
    name = "entity"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }
}

# ============================================================
# 7. Evaluación de riesgo de órdenes
# ============================================================

resource "aws_dynamodb_table" "order_risk" {
  name         = "order_risk"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "order_id"

  attribute {
    name = "order_id"
    type = "S"
  }

  # Claves del índice secundario global
  attribute {
    name = "decision"
    type = "S"
  }

  attribute {
    name = "evaluated_at"
    type = "S"
  }

  global_secondary_index {
    name            = "decision-index"
    hash_key        = "decision"
    range_key       = "evaluated_at"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }
}

# ============================================================
# 8. Alertas de seguridad
# ============================================================

resource "aws_dynamodb_table" "security_alerts" {
  name         = "security_alerts"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "customer_key"
  range_key    = "sk"

  attribute {
    name = "customer_key"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  # Claves del índice secundario global
  attribute {
    name = "status"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  global_secondary_index {
    name            = "status-index"
    hash_key        = "status"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }
}
