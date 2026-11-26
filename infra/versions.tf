terraform {
  required_version = ">= 1.10"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.80"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.6"
    }
  }

  # The state lives in an S3 bucket created once by the deploy workflow (see the README).
  # The values are passed to `terraform init -backend-config=...`, which is why the block is empty.
  backend "s3" {}
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project     = var.name
      Environment = var.environment
    }
  }
}

data "aws_caller_identity" "current" {}
