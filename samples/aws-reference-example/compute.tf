data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${local.name}-lambda"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags               = local.common_tags
}

data "aws_iam_policy_document" "lambda" {
  statement {
    actions = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${local.name}-*:*"]
  }

  statement {
    actions   = ["xray:PutTraceSegments", "xray:PutTelemetryRecords"]
    resources = ["*"]
  }

  statement {
    actions = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Query"]
    resources = [for table in aws_dynamodb_table.domain : table.arn]
  }

  statement {
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["${aws_s3_bucket.documents.arn}/*"]
  }

  statement {
    actions   = ["events:PutEvents"]
    resources = [aws_eventbridge_bus.insurance.arn]
  }

  statement {
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.notifications.arn]
  }

  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.payment_provider.arn]
  }

  statement {
    actions   = ["kms:Decrypt", "kms:Encrypt", "kms:GenerateDataKey"]
    resources = [aws_kms_key.main.arn]
  }
}

resource "aws_iam_role_policy" "lambda" {
  name   = "domain-access"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.lambda.json
}

data "archive_file" "lambda" {
  type        = "zip"
  output_path = "${path.module}/.terraform/lambda.zip"

  source {
    filename = "index.py"
    content  = <<-PY
      import json
      import os

      def handler(event, context):
          return {
              "statusCode": 501,
              "headers": {"content-type": "application/json"},
              "body": json.dumps({
                  "message": "Architecture placeholder: implement business logic",
                  "feature": os.environ.get("FEATURE")
              })
          }
    PY
  }
}

resource "aws_cloudwatch_log_group" "lambda" {
  for_each = local.api_features

  name              = "/aws/lambda/${local.name}-${replace(each.key, "_", "-")}"
  retention_in_days = var.log_retention_days
  tags              = local.common_tags
}

resource "aws_lambda_function" "feature" {
  for_each = local.api_features

  function_name    = "${local.name}-${replace(each.key, "_", "-")}"
  role             = aws_iam_role.lambda.arn
  runtime          = var.lambda_runtime
  handler          = "index.handler"
  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256
  architectures    = ["arm64"]
  memory_size      = 256
  timeout          = 15

  environment {
    variables = {
      FEATURE                 = each.key
      POLICIES_TABLE          = aws_dynamodb_table.domain["policies"].name
      PAYMENTS_TABLE          = aws_dynamodb_table.domain["payments"].name
      CLAIMS_TABLE            = aws_dynamodb_table.domain["claims"].name
      DEBTS_TABLE             = aws_dynamodb_table.domain["debts"].name
      DOCUMENTS_BUCKET        = aws_s3_bucket.documents.id
      EVENT_BUS_NAME          = aws_eventbridge_bus.insurance.name
      NOTIFICATIONS_TOPIC_ARN = aws_sns_topic.notifications.arn
      PAYMENT_SECRET_ARN      = aws_secretsmanager_secret.payment_provider.arn
    }
  }

  tracing_config {
    mode = "Active"
  }

  depends_on = [aws_cloudwatch_log_group.lambda]
  tags       = local.common_tags
}
