# The login is the e-mail and a password. Anyone can create an account on the site (Criar conta): Cognito
# e-mails a 6-digit code and the account only logs in after it is confirmed. Each account sees only its
# own data (the API takes the user from the token). Actions -> Create user also creates one by hand.
resource "aws_cognito_user_pool" "login" {
  # The create-user workflow looks the pool up by this name.
  name                     = "${local.prefix}-login"
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]
  deletion_protection      = var.environment == "prod" ? "ACTIVE" : "INACTIVE"

  username_configuration {
    case_sensitive = false # Ana@x.com and ana@x.com are the same login
  }

  # Open sign-up from the site.
  admin_create_user_config {
    allow_admin_create_user_only = false
  }

  # Cognito's own e-mail sender: no SES to set up, but limited to about 50 e-mails a day per account. For
  # more, configure SES and set email_sending_account = "DEVELOPER" with its source_arn.
  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }

  # The e-mail with the sign-up code (also sent by "Reenviar código"), in English. {####} is the code.
  verification_message_template {
    default_email_option = "CONFIRM_WITH_CODE"
    email_subject        = "Task Pulse: your verification code"
    email_message        = "Your code to confirm your e-mail on Task Pulse is {####}. If this wasn't you, ignore this e-mail."
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
  read_attributes               = ["email", "email_verified", "name", "locale"]
  write_attributes              = ["email", "name", "locale"] # locale: the language chosen in Configurações
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
