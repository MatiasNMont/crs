output "web_url" {
  description = "URL de la aplicacion web de referencia."
  value       = "https://${aws_cloudfront_distribution.web.domain_name}"
}

output "api_url" {
  description = "Endpoint REST API consumido por web y mobile."
  value       = aws_api_gateway_stage.main.invoke_url
}

output "cognito_user_pool_id" {
  value = aws_cognito_user_pool.users.id
}

output "cognito_client_id" {
  value = aws_cognito_user_pool_client.applications.id
}

output "cognito_hosted_ui_domain" {
  value = "https://${aws_cognito_user_pool_domain.main.domain}.auth.${var.aws_region}.amazoncognito.com"
}

output "policy_documents_bucket" {
  value = aws_s3_bucket.documents.id
}

output "policy_generation_state_machine_arn" {
  value = aws_sfn_state_machine.policy_generation.arn
}
