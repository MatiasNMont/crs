resource "aws_dynamodb_table" "domain" {
  for_each = local.tables

  name         = "${local.name}-${each.key}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.main.arn
  }

  tags = local.common_tags
}

resource "aws_s3_bucket" "documents" {
  bucket        = "${local.name}-documents-${random_id.suffix.hex}"
  force_destroy = var.force_destroy_buckets
  tags          = local.common_tags
}

resource "aws_s3_bucket_public_access_block" "documents" {
  bucket                  = aws_s3_bucket.documents.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.main.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id

  rule {
    id     = "archive-old-versions"
    status = "Enabled"

    filter {}

    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "STANDARD_IA"
    }
  }
}

resource "aws_eventbridge_bus" "insurance" {
  name = "${local.name}-events"
  tags = local.common_tags
}

resource "aws_sqs_queue" "dead_letter" {
  name                      = "${local.name}-events-dlq"
  message_retention_seconds = 1209600
  kms_master_key_id         = "alias/aws/sqs"
  tags                      = local.common_tags
}

resource "aws_sns_topic" "notifications" {
  name              = "${local.name}-notifications"
  kms_master_key_id = "alias/aws/sns"
  tags              = local.common_tags
}

resource "aws_cloudwatch_event_rule" "domain_events" {
  name           = "${local.name}-domain-events"
  description    = "Route insurance domain events to operational consumers"
  event_bus_name = aws_eventbridge_bus.insurance.name

  event_pattern = jsonencode({
    source = [{ prefix = "insurance." }]
  })

  tags = local.common_tags
}

resource "aws_cloudwatch_event_target" "dead_letter" {
  rule           = aws_cloudwatch_event_rule.domain_events.name
  event_bus_name = aws_eventbridge_bus.insurance.name
  target_id      = "domain-events-queue"
  arn            = aws_sqs_queue.dead_letter.arn
}

resource "aws_cloudwatch_event_target" "notifications" {
  rule           = aws_cloudwatch_event_rule.domain_events.name
  event_bus_name = aws_eventbridge_bus.insurance.name
  target_id      = "domain-events-notifications"
  arn            = aws_sns_topic.notifications.arn
}

data "aws_iam_policy_document" "event_queue" {
  statement {
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.dead_letter.arn]

    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [aws_cloudwatch_event_rule.domain_events.arn]
    }
  }
}

resource "aws_sqs_queue_policy" "event_queue" {
  queue_url = aws_sqs_queue.dead_letter.id
  policy    = data.aws_iam_policy_document.event_queue.json
}

data "aws_iam_policy_document" "event_notifications" {
  statement {
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.notifications.arn]

    principals {
      type        = "Service"
      identifiers = ["cloudwatch.amazonaws.com"]
    }
  }

  statement {
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.notifications.arn]

    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }

    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = [aws_cloudwatch_event_rule.domain_events.arn]
    }
  }

  statement {
    actions   = ["sns:GetTopicAttributes", "sns:SetTopicAttributes", "sns:Subscribe", "sns:Publish"]
    resources = [aws_sns_topic.notifications.arn]

    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"]
    }
  }
}

resource "aws_sns_topic_policy" "notifications" {
  arn    = aws_sns_topic.notifications.arn
  policy = data.aws_iam_policy_document.event_notifications.json
}

resource "aws_secretsmanager_secret" "payment_provider" {
  name                    = "${local.name}/payment-provider"
  description             = "Credentials for the external payment provider"
  kms_key_id              = aws_kms_key.main.arn
  recovery_window_in_days = 7
  tags                    = local.common_tags
}
