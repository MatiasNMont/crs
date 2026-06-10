resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/apigateway/${local.name}"
  retention_in_days = var.log_retention_days
  tags              = local.common_tags
}

data "aws_iam_policy_document" "api_gateway_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["apigateway.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "api_gateway_logs" {
  name               = "${local.name}-api-gateway-logs"
  assume_role_policy = data.aws_iam_policy_document.api_gateway_assume.json
  tags               = local.common_tags
}

resource "aws_iam_role_policy_attachment" "api_gateway_logs" {
  role       = aws_iam_role.api_gateway_logs.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
}

resource "aws_api_gateway_account" "main" {
  cloudwatch_role_arn = aws_iam_role.api_gateway_logs.arn
}

resource "aws_api_gateway_rest_api" "main" {
  name        = "${local.name}-api"
  description = "Insurance APIs consumed by web and mobile applications"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = local.common_tags
}

resource "aws_api_gateway_authorizer" "cognito" {
  name          = "cognito"
  rest_api_id   = aws_api_gateway_rest_api.main.id
  type          = "COGNITO_USER_POOLS"
  provider_arns = [aws_cognito_user_pool.users.arn]
}

resource "aws_api_gateway_resource" "policies" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "policies"
}

resource "aws_api_gateway_resource" "policy_generation" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.policies.id
  path_part   = "generate"
}

resource "aws_api_gateway_resource" "payments" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "payments"
}

resource "aws_api_gateway_resource" "claims" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "claims"
}

resource "aws_api_gateway_resource" "debts" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "debts"
}

locals {
  api_resource_ids = {
    policies          = aws_api_gateway_resource.policies.id
    policy_generation = aws_api_gateway_resource.policy_generation.id
    payments          = aws_api_gateway_resource.payments.id
    claims            = aws_api_gateway_resource.claims.id
    debts             = aws_api_gateway_resource.debts.id
  }
}

resource "aws_api_gateway_method" "feature" {
  for_each = local.api_features

  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = local.api_resource_ids[each.key]
  http_method   = each.value.method
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id
}

resource "aws_api_gateway_method" "cors" {
  for_each = local.api_features

  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = local.api_resource_ids[each.key]
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "cors" {
  for_each = local.api_features

  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = local.api_resource_ids[each.key]
  http_method = aws_api_gateway_method.cors[each.key].http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = jsonencode({ statusCode = 200 })
  }
}

resource "aws_api_gateway_method_response" "cors" {
  for_each = local.api_features

  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = local.api_resource_ids[each.key]
  http_method = aws_api_gateway_method.cors[each.key].http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "cors" {
  for_each = local.api_features

  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = local.api_resource_ids[each.key]
  http_method = aws_api_gateway_method.cors[each.key].http_method
  status_code = aws_api_gateway_method_response.cors[each.key].status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'authorization,content-type,x-request-id'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'${var.api_allowed_origins[0]}'"
  }
}

resource "aws_api_gateway_integration" "feature" {
  for_each = local.api_features

  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = local.api_resource_ids[each.key]
  http_method             = aws_api_gateway_method.feature[each.key].http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.feature[each.key].invoke_arn
}

resource "aws_lambda_permission" "api" {
  for_each = local.api_features

  statement_id  = "AllowApiGateway-${each.key}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.feature[each.key].function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/${each.value.method}${each.value.path}"
}

resource "aws_api_gateway_deployment" "main" {
  rest_api_id = aws_api_gateway_rest_api.main.id

  triggers = {
    redeployment = sha1(jsonencode({
      methods      = [for method in aws_api_gateway_method.feature : method.id]
      integrations = [for integration in aws_api_gateway_integration.feature : integration.id]
      cors_methods = [for method in aws_api_gateway_method.cors : method.id]
      cors_integrations = [for integration in aws_api_gateway_integration.cors : integration.id]
    }))
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [aws_api_gateway_integration_response.cors]
}

resource "aws_api_gateway_stage" "main" {
  deployment_id = aws_api_gateway_deployment.main.id
  rest_api_id   = aws_api_gateway_rest_api.main.id
  stage_name    = var.environment

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api.arn
    format = jsonencode({
      requestId        = "$context.requestId"
      requestTime      = "$context.requestTime"
      httpMethod       = "$context.httpMethod"
      resourcePath     = "$context.resourcePath"
      status           = "$context.status"
      responseLength   = "$context.responseLength"
      integrationError = "$context.integrationErrorMessage"
    })
  }

  xray_tracing_enabled = true
  tags                 = local.common_tags

  depends_on = [aws_api_gateway_account.main]
}

resource "aws_api_gateway_method_settings" "all" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  stage_name  = aws_api_gateway_stage.main.stage_name
  method_path = "*/*"

  settings {
    metrics_enabled        = true
    logging_level          = "INFO"
    data_trace_enabled     = false
    throttling_burst_limit = var.api_throttling_burst_limit
    throttling_rate_limit  = var.api_throttling_rate_limit
  }
}
