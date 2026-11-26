# One Lambda per business action: each folder backend/lambdas/<action>/ has its use case, its
# inbound adapter (handler.py) and a lambda.json with its route and its database access ("read" or
# "write"). Adding a folder adds the function, its route and its logs; nothing to list here.
locals {
  lambdas_dir = "${path.module}/../backend/lambdas"
  core_dir    = "${path.module}/../backend/core"
  lambdas = {
    for config in fileset(local.lambdas_dir, "*/lambda.json") :
    dirname(config) => jsondecode(file("${local.lambdas_dir}/${config}"))
  }
  core_files = fileset(local.core_dir, "pulse_core/**/*.py")
}

# Each zip = the shared core (pulse_core/) + only this Lambda's own folder.
data "archive_file" "lambda" {
  for_each    = local.lambdas
  type        = "zip"
  output_path = "${path.module}/build/${each.key}.zip"

  dynamic "source" {
    for_each = local.core_files
    content {
      content  = file("${local.core_dir}/${source.value}")
      filename = source.value
    }
  }

  dynamic "source" {
    for_each = fileset("${local.lambdas_dir}/${each.key}", "*.py")
    content {
      content  = file("${local.lambdas_dir}/${each.key}/${source.value}")
      filename = "${each.key}/${source.value}"
    }
  }
}

data "aws_iam_policy_document" "lambda_trust" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# Lambdas that change data ("write" in lambda.json).
resource "aws_iam_role" "lambda" {
  name               = "${local.prefix}-lambda"
  assume_role_policy = data.aws_iam_policy_document.lambda_trust.json
}

# Lambdas that only read ("read" in lambda.json): they cannot write even if their code tried to.
resource "aws_iam_role" "lambda_read" {
  name               = "${local.prefix}-lambda-read"
  assume_role_policy = data.aws_iam_policy_document.lambda_trust.json
}

# Only what the functions use: read, write and delete items in this table (BatchWriteItem: every task
# of a payment at once). No Scan, no other tables.
data "aws_iam_policy_document" "lambda_access" {
  statement {
    actions   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:BatchWriteItem"]
    resources = [aws_dynamodb_table.data.arn]
  }
}

data "aws_iam_policy_document" "lambda_read_access" {
  statement {
    actions   = ["dynamodb:GetItem", "dynamodb:Query"]
    resources = [aws_dynamodb_table.data.arn]
  }
}

resource "aws_iam_role_policy" "lambda_data" {
  name   = "data"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.lambda_access.json
}

resource "aws_iam_role_policy" "lambda_read_data" {
  name   = "read"
  role   = aws_iam_role.lambda_read.id
  policy = data.aws_iam_policy_document.lambda_read_access.json
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  for_each   = { write = aws_iam_role.lambda.name, read = aws_iam_role.lambda_read.name }
  role       = each.value
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_cloudwatch_log_group" "lambda" {
  for_each          = local.lambdas
  name              = "/aws/lambda/${local.prefix}-${replace(each.key, "_", "-")}"
  retention_in_days = var.log_retention_days
}

resource "aws_lambda_function" "action" {
  for_each         = local.lambdas
  function_name    = "${local.prefix}-${replace(each.key, "_", "-")}"
  role             = each.value.database == "read" ? aws_iam_role.lambda_read.arn : aws_iam_role.lambda.arn
  runtime          = "python3.12"
  architectures    = ["arm64"]
  handler          = "${each.key}.handler.lambda_handler"
  filename         = data.archive_file.lambda[each.key].output_path
  source_code_hash = data.archive_file.lambda[each.key].output_base64sha256
  # Lambda gives CPU in proportion to memory: 512 MB starts a cold function (Python + boto3)
  # noticeably faster than 256 MB. Billed per ms used: at this traffic, still cents a month.
  memory_size = 512
  timeout     = 10

  environment {
    variables = { TABLE_NAME = aws_dynamodb_table.data.name }
  }

  depends_on = [aws_cloudwatch_log_group.lambda, aws_iam_role_policy_attachment.lambda_logs]
}
