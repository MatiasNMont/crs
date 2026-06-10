variable "project" {
  description = "Nombre del proyecto, usado como prefijo de recursos."
  type        = string
  default     = "insurance"
}

variable "environment" {
  description = "Entorno de despliegue (dev, staging, prod)."
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "Region de AWS."
  type        = string
  default     = "us-east-1"
}

variable "lambda_runtime" {
  description = "Runtime de las funciones Lambda."
  type        = string
  default     = "python3.12"
}

variable "cognito_mfa_configuration" {
  description = "Configuracion MFA de Cognito: OFF u OPTIONAL."
  type        = string
  default     = "OPTIONAL"

  validation {
    condition     = contains(["OFF", "OPTIONAL"], var.cognito_mfa_configuration)
    error_message = "El valor debe ser OFF u OPTIONAL."
  }
}

variable "cognito_callback_urls" {
  description = "URLs de callback OAuth para las apps mobile/web."
  type        = list(string)
  default     = ["https://localhost/callback"]
}

variable "cognito_logout_urls" {
  description = "URLs de logout OAuth para las apps mobile/web."
  type        = list(string)
  default     = ["https://localhost/logout"]
}

variable "api_allowed_origins" {
  description = "Origenes CORS permitidos para API Gateway."
  type        = list(string)
  default     = ["https://localhost"]

  validation {
    condition     = length(var.api_allowed_origins) > 0
    error_message = "Debe configurarse al menos un origen CORS."
  }
}

variable "api_throttling_burst_limit" {
  description = "Pico maximo de solicitudes API."
  type        = number
  default     = 100
}

variable "api_throttling_rate_limit" {
  description = "Solicitudes sostenidas por segundo."
  type        = number
  default     = 50
}

variable "log_retention_days" {
  description = "Retencion de logs en CloudWatch."
  type        = number
  default     = 30
}

variable "cloudfront_price_class" {
  description = "Clase de precio de CloudFront."
  type        = string
  default     = "PriceClass_100"
}

variable "force_destroy_buckets" {
  description = "Permite eliminar buckets con contenido. Usar false en produccion."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags adicionales aplicados a todos los recursos."
  type        = map(string)
  default     = {}
}
