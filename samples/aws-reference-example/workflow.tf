data "aws_iam_policy_document" "step_functions_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "step_functions" {
  name               = "${local.name}-policy-workflow"
  assume_role_policy = data.aws_iam_policy_document.step_functions_assume.json
  tags               = local.common_tags
}

data "aws_iam_policy_document" "step_functions" {
  statement {
    actions   = ["lambda:InvokeFunction"]
    resources = [aws_lambda_function.feature["policy_generation"].arn]
  }
}

resource "aws_iam_role_policy" "step_functions" {
  role   = aws_iam_role.step_functions.id
  policy = data.aws_iam_policy_document.step_functions.json
}

data "aws_iam_policy_document" "start_policy_workflow" {
  statement {
    actions   = ["states:StartExecution"]
    resources = [aws_sfn_state_machine.policy_generation.arn]
  }
}

resource "aws_iam_role_policy" "start_policy_workflow" {
  name   = "start-policy-generation"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.start_policy_workflow.json
}

resource "aws_sfn_state_machine" "policy_generation" {
  name     = "${local.name}-policy-generation"
  role_arn = aws_iam_role.step_functions.arn

  definition = jsonencode({
    Comment = "Generate and persist an insurance policy document"
    StartAt = "GeneratePolicy"
    States = {
      GeneratePolicy = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.feature["policy_generation"].arn
          "Payload.$" = "$"
        }
        Retry = [{
          ErrorEquals     = ["Lambda.ServiceException", "Lambda.TooManyRequestsException"]
          IntervalSeconds = 2
          MaxAttempts     = 3
          BackoffRate     = 2
        }]
        End = true
      }
    }
  })

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "api_errors" {
  alarm_name          = "${local.name}-api-5xx"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "5XXError"
  namespace           = "AWS/ApiGateway"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "API Gateway is returning elevated 5xx errors"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.notifications.arn]

  dimensions = {
    ApiName = aws_api_gateway_rest_api.main.name
    Stage   = aws_api_gateway_stage.main.stage_name
  }

  tags = local.common_tags
}
