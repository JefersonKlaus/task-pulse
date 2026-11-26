# The login is the phone number (+55 + DDD + number). Only you create the logins: Actions -> Create user.
resource "aws_cognito_user_pool" "login" {
  # The create-user workflow looks the pool up by this name.
  name                     = "${local.prefix}-login"
  username_attributes      = ["phone_number"]
  auto_verified_attributes = ["email"]
  deletion_protection      = var.environment == "prod" ? "ACTIVE" : "INACTIVE"

  # Only you create the accounts (there is no open sign-up): Actions -> Create user.
  admin_create_user_config {
    allow_admin_create_user_only = true
  }

  password_policy {
    minimum_length                   = 10
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = false
    temporary_password_validity_days = 7
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }
}

resource "aws_cognito_user_pool_client" "site" {
  name            = "${local.prefix}-site"
  user_pool_id    = aws_cognito_user_pool.login.id
  generate_secret = false # a browser app cannot keep a secret

  explicit_auth_flows = ["ALLOW_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"]

  prevent_user_existence_errors = "ENABLED"
  write_attributes              = ["email", "name"]
  enable_token_revocation       = true

  access_token_validity  = 60
  id_token_validity      = 60
  refresh_token_validity = 30

  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }
}
