# Caso de prueba: tablas DynamoDB de la plataforma de seguros

Este recorrido usa `aws-reference-example`, una arquitectura serverless en Terraform para los canales web y mobile de una aseguradora.

La plataforma incluye Cognito, CloudFront, S3, WAF, API Gateway, Lambda, Step Functions, DynamoDB, EventBridge, SQS, SNS, KMS, Secrets Manager, CloudWatch y X-Ray.

## Escenario

Las polizas, pagos, siniestros, deudas y perfiles se guardan en tablas creadas por `aws_dynamodb_table.domain` en `data.tf`.

La pregunta es:

> ¿Que componentes se ven afectados si elimino las tablas DynamoDB de dominio?

## Inicializar

```powershell
cd aws-reference-example
crs init .
```

Grafo medido:

- 11 archivos Terraform
- 96 nodos CRS
- 151 relaciones

## Encontrar el componente

```powershell
crs search . dynamodb
```

Resultado esperado:

```text
root::aws_dynamodb_table.domain (resource, data, security) - data.tf:1
```

## Analizar impacto

```powershell
crs ask . "What is affected if I delete the domain DynamoDB tables?" --json --detail summary
```

CRS detecta intención `impact`, selecciona `root::aws_dynamodb_table.domain` y encuentra:

- Dependencia directa: `root::aws_kms_key.main`.
- Profundidad 1: documento IAM de Lambda y funciones Lambda de negocio.
- Profundidad 2: rol IAM, integraciones/permisos de API Gateway, politica y state machine de Step Functions.
- Profundidad 3: deployment de API Gateway, roles del workflow y outputs asociados.

Se detectan 11 nodos afectados aguas abajo. Funcionalmente, la eliminacion compromete consulta/generacion de polizas, pagos, denuncias de siniestros, deudas impagas y perfiles.

## Analizar falla

```powershell
crs failure . root::aws_dynamodb_table.domain --depth 3
```

Revisar perdida de persistencia, point-in-time recovery, cifrado KMS, permisos IAM, variables de entorno Lambda, errores de API y comportamiento de Step Functions.

## Validar cambios

```powershell
crs preflight . --max-affected 10
terraform plan
```

CRS analiza relaciones estructurales del codigo. `terraform plan` sigue siendo la autoridad para reemplazos, valores calculados y estado desplegado.

## Comparar sin CRS

```powershell
crs disable . --remove-memory
```

Luego se debe iniciar una sesion nueva del agente y repetir exactamente la misma pregunta.
