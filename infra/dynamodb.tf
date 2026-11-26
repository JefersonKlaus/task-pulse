# One table for everything (backend/core/pulse_core/adapters/dynamo_repository.py):
# PK = OWNER#<user>, SK = COMPANY#<id> | PROJECT#<id> | TASK#<project id>#<id> | PAY#<project id>#<id>.
resource "aws_dynamodb_table" "data" {
  name         = "${local.prefix}-data"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  deletion_protection_enabled = var.environment == "prod"
}
