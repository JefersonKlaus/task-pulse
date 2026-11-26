variable "name" {
  description = "Short name of the system, used as the prefix of the resources."
  type        = string
  default     = "task-pulse"
}

variable "environment" {
  description = "prod, dev..."
  type        = string
  default     = "prod"
}

variable "region" {
  type    = string
  default = "sa-east-1"
}

variable "extra_cors_origins" {
  description = "Other origins allowed to call the API (e.g. http://localhost:8765 in tests)."
  type        = list(string)
  default     = []
}

variable "log_retention_days" {
  type    = number
  default = 14
}

variable "rate_limit_per_second" {
  description = "Requests per second allowed across the whole API (protection against abuse and cost)."
  type        = number
  default     = 20
}

variable "burst_limit" {
  type    = number
  default = 40
}

locals {
  prefix  = "${var.name}-${var.environment}"
  account = data.aws_caller_identity.current.account_id
}
