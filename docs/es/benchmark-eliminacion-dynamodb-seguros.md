# Benchmark: eliminacion de tablas DynamoDB en la plataforma de seguros

Pregunta medida:

> ¿Que componentes se ven afectados si elimino las tablas DynamoDB de dominio?

## Proyecto

- Proyecto: `aws-reference-example`
- Archivos Terraform: 11
- Grafo CRS: 96 nodos y 151 relaciones
- Nodo foco: `root::aws_dynamodb_table.domain`
- Subgrafo enviado: 9 nodos y 9 relaciones
- Nodos afectados aguas abajo: 11

## Ejecutar

```powershell
cd aws-reference-example
crs init .
crs benchmark-tokens . "What is affected if I delete the domain DynamoDB tables?" --detail summary
```

## Resultado medido

| Modo | Tokens estimados | Reduccion | Ratio RAW/CRS |
| --- | ---: | ---: | ---: |
| Repositorio completo | 7.481 | - | - |
| CRS `minimal` | 1.892 | 74,71 % | 3,95x |
| CRS `summary` | 2.063 | 72,42 % | 3,63x |
| CRS `full` | 3.774 | 49,55 % | 1,98x |

El modo predeterminado `summary` ahorra aproximadamente 5.418 tokens de entrada y conserva la configuracion completa de DynamoDB, junto con punteros precisos a los nodos relacionados.

## Hallazgos

CRS identifica DynamoDB como dominio de datos y seguridad, KMS como dependencia directa y propagacion hacia Lambda, IAM, API Gateway y Step Functions.

## Comparacion justa con agentes

Repositorio con CRS:

```powershell
crs init .
```

Repositorio de control:

```powershell
crs disable . --remove-memory
```

Usar sesiones nuevas, mismo modelo, mismo nivel de razonamiento y la misma pregunta. Registrar tokens de entrada/salida, llamadas a herramientas, tiempo total, calidad de respuesta y dependencias omitidas.

La estimacion integrada usa `ceil(caracteres / 4)`. Para costos reales, usar los tokens reportados por el proveedor de la LLM.
