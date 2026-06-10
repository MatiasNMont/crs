# Arquitectura AWS

```mermaid
flowchart TB
  user["Usuario"]
  mobile["Aplicacion mobile"]
  web["Aplicacion web"]
  cf["Amazon CloudFront"]
  webS3["Amazon S3 - frontend"]
  cognito["Amazon Cognito - registro, login y MFA"]
  waf["AWS WAF"]
  api["Amazon API Gateway REST API"]

  subgraph services["Servicios de negocio"]
    policies["Lambda - consulta de polizas"]
    generator["Step Functions + Lambda - generar poliza"]
    payments["Lambda - pagar poliza"]
    claims["Lambda - denunciar siniestro"]
    debts["Lambda - deudas impagas"]
  end

  subgraph data["Datos y documentos"]
    dynamo["Amazon DynamoDB - polizas, pagos, siniestros y deudas"]
    docs["Amazon S3 - documentos de poliza"]
    secrets["AWS Secrets Manager - proveedor de pagos"]
  end

  subgraph events["Integracion y operacion"]
    eb["Amazon EventBridge"]
    sqs["Amazon SQS DLQ"]
    sns["Amazon SNS - notificaciones y alarmas"]
    cw["CloudWatch + X-Ray"]
    kms["AWS KMS"]
  end

  user --> mobile
  user --> web
  web --> cf --> webS3
  mobile --> cognito
  web --> cognito
  mobile --> waf
  web --> waf
  waf --> api
  cognito -. "JWT" .-> api
  api --> policies
  api --> generator
  api --> payments
  api --> claims
  api --> debts
  policies --> dynamo
  generator --> dynamo
  generator --> docs
  payments --> dynamo
  payments --> secrets
  claims --> dynamo
  debts --> dynamo
  policies --> eb
  payments --> eb
  claims --> eb
  eb --> sqs
  eb --> sns
  api --> cw
  services --> cw
  kms -. "cifrado" .-> data
  kms -. "cifrado" .-> cw
```

## Relacion con las features

| Feature | Componentes principales |
|---|---|
| Aplicacion mobile | Cognito, API Gateway, CloudFront para contenido compartido si aplica |
| Aplicacion web | S3 privado, CloudFront, Cognito |
| Registro y login | Cognito User Pool, OAuth 2.0 Authorization Code + PKCE, MFA opcional |
| Pago de polizas | API Gateway, Lambda Payments, Secrets Manager, DynamoDB, EventBridge |
| Generacion de poliza | Step Functions, Lambda, DynamoDB y S3 para PDF/documentos |
| Denuncia de siniestro | API Gateway, Lambda Claims, DynamoDB, EventBridge |
| Deudas impagas | API Gateway, Lambda Debts y DynamoDB |

## Decisiones

- El backend es serverless para reducir operacion y escalar por demanda.
- API Gateway valida JWT emitidos por Cognito antes de invocar las Lambdas.
- DynamoDB usa modo on-demand, cifrado KMS y point-in-time recovery.
- Los documentos son privados, versionados y cifrados en S3.
- EventBridge permite integrar notificaciones, cobranzas, fraude y sistemas legacy sin acoplarlos a la API.
- El proveedor de pagos es externo; Terraform solo crea el secreto donde se cargan sus credenciales. No almacena datos de tarjeta.
