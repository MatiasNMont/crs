# AWS Insurance Reference Architecture

Arquitectura de referencia en Terraform para los canales mobile y web de una aseguradora. Incluye identidad, APIs protegidas, pagos, generacion de polizas, denuncia de siniestros, consulta de deuda, almacenamiento, eventos, seguridad y observabilidad.

## Componentes

- Amazon Cognito para registro, login, JWT y MFA opcional.
- S3 + CloudFront para publicar la aplicacion web sin exponer el bucket.
- AWS WAF + API Gateway REST API como entrada protegida del backend.
- AWS Lambda para polizas, pagos, siniestros y deudas.
- Step Functions para orquestar la generacion de documentos de poliza.
- DynamoDB para datos operativos y S3 para documentos.
- EventBridge, SQS DLQ y SNS para integracion y notificaciones.
- KMS, Secrets Manager, CloudWatch y X-Ray para seguridad y operacion.

El diagrama y el mapeo de features estan en [architecture.md](./architecture.md).

## Estructura

```text
aws-reference-example/
  api.tf
  compute.tf
  data.tf
  frontend.tf
  security.tf
  workflow.tf
  architecture.md
  terraform.tfvars.example
```

## Despliegue

Requisitos: Terraform >= 1.6, AWS CLI autenticado y permisos para crear los servicios declarados.

```powershell
Copy-Item terraform.tfvars.example terraform.tfvars
terraform init
terraform fmt -check
terraform validate
terraform plan -out insurance.tfplan
terraform apply insurance.tfplan
```

Luego se debe cargar el build real del frontend en el bucket `web`, implementar la logica de las Lambdas y guardar las credenciales del procesador de pagos en el secreto creado. Las funciones incluidas son placeholders desplegables que responden HTTP 501.

## Consideraciones de produccion

- Usar cuentas AWS separadas para dev, staging y prod, con estado remoto S3 y locking.
- Agregar dominio propio y certificado ACM a CloudFront/API Gateway.
- Configurar WAF de CloudFront en `us-east-1` y proteccion avanzada contra bots/DDoS si corresponde.
- Revisar PCI DSS con el proveedor de pagos; usar tokenizacion y nunca enviar PAN/CVV al backend.
- Agregar controles de fraude, idempotencia de pagos, conciliacion y auditoria inmutable.
- Definir backup, recuperacion, RTO/RPO, retencion legal y residencia de datos.
- Implementar CI/CD, pruebas, escaneo IaC y aprobaciones por ambiente.

> Esta es una arquitectura de referencia, no una implementacion funcional del negocio ni una certificacion de cumplimiento.
