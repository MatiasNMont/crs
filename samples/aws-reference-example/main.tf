data "aws_caller_identity" "current" {}

data "aws_cloudfront_cache_policy" "caching_optimized" {
  name = "Managed-CachingOptimized"
}

resource "random_id" "suffix" {
  byte_length = 4
}

locals {
  name = "${var.project}-${var.environment}"

  common_tags = merge(var.tags, {
    Domain = "Insurance"
  })

  api_features = {
    policies = {
      method = "GET"
      path   = "/policies"
    }
    policy_generation = {
      method = "POST"
      path   = "/policies/generate"
    }
    payments = {
      method = "POST"
      path   = "/payments"
    }
    claims = {
      method = "POST"
      path   = "/claims"
    }
    debts = {
      method = "GET"
      path   = "/debts"
    }
  }

  tables = toset(["policies", "payments", "claims", "debts", "user-profiles"])
}

