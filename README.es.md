# CRS - Code Relationship System

CRS es una herramienta local de memoria de grafo y análisis para repositorios Terraform. Examina el código de infraestructura, construye un grafo de dependencias y brinda a los agentes de programación contexto arquitectónico específico antes de que exploren el repositorio completo.

CRS está diseñado para análisis de impacto, razonamiento sobre fallas, validación de cambios de Terraform, generación de contexto compacto para LLM y comparaciones reproducibles entre flujos de agentes con y sin memoria de grafo.

> Estado actual: **Beta**, versión **0.5.0**. Actualmente soporta Terraform/HCL. El scanner es intencionalmente liviano y heurístico.

## Por qué usar CRS

Las consultas sobre infraestructura suelen obligar a un agente a inspeccionar muchos archivos antes de identificar los recursos y dependencias relevantes. CRS indexa esas relaciones una vez y las guarda localmente en `.crs/`.

Luego, los agentes pueden realizar preguntas como:

```text
¿Qué se ve afectado si elimino las tablas DynamoDB de dominio?
¿Qué puede fallar si este componente deja de estar disponible?
¿Qué recursos dependen de esta clave KMS?
```

En lugar de cargar el repositorio completo, el agente recibe un subgrafo acotado con IDs de nodos, relaciones, riesgos y ubicaciones en el código fuente.

## Características

- **Indexación del grafo Terraform**: detecta recursos, fuentes de datos, módulos, variables, outputs, providers, referencias y dependencias explícitas.
- **Análisis de impacto**: rastrea dependencias directas y componentes aguas abajo afectados por un cambio.
- **Análisis de fallas**: modela la propagación de fallas y agrega recomendaciones de riesgo específicas por dominio.
- **Consultas en lenguaje natural**: `crs ask` detecta la operación solicitada y resuelve el nodo relevante del grafo.
- **Alias para agentes**: `crs agent` ofrece el mismo flujo que `crs ask`.
- **Contexto compacto para LLM**: exporta contexto `minimal`, `summary` o `full` con referencias precisas a archivos y líneas.
- **Integración automática con agentes**: `crs init` instala instrucciones CRS-first para Codex y Claude Code.
- **Integraciones opcionales**: también permite instalar reglas de repositorio para Cursor y Windsurf.
- **Integración con CodeLoom**: CodeLoom se instala con CRS y se utiliza como integración de memoria predeterminada.
- **Validaciones preflight de Terraform**: compara el código actual con la memoria del grafo y calcula el radio de impacto de los cambios.
- **Benchmark de tokens**: estima la reducción de contexto obtenida con CRS frente a leer todos los archivos Terraform.
- **Visualización interactiva**: genera un grafo de dependencias HTML autocontenido.
- **Generación de experimentos de caos**: crea planes basados en el grafo en JSON, Markdown y HTML.
- **Borradores de postmortem**: genera un documento inicial a partir del análisis de fallas del grafo.
- **Operación local**: la memoria del grafo y los reportes generados permanecen dentro del repositorio analizado.
- **Redacción de secretos**: los valores literales sensibles se ocultan antes de persistirlos en la memoria.
- **Pruebas de control limpias**: `crs disable` elimina las reglas administradas y `--remove-memory` también elimina los datos generados por CRS.

## Instalación

CRS requiere Python 3.10 o una versión posterior.

```bash
git clone https://github.com/matiasnmont/crs.git
cd crs
python -m pip install -e .
```

Esto instala el comando `crs` y una versión compatible de CodeLoom.

Verificar la instalación:

```bash
crs --help
```

## Inicio rápido

Inicializar CRS dentro de un repositorio Terraform:

```bash
crs init ./aws-reference-example
```

La inicialización realiza tres operaciones:

1. Examina el código Terraform y construye la memoria del grafo en `.crs/`.
2. Sincroniza el backend de memoria configurado, usando CodeLoom como integración predeterminada.
3. Instala instrucciones administradas para Codex y Claude Code en el repositorio.

Después de inicializar, se debe abrir una nueva sesión del agente para que cargue las instrucciones generadas en `AGENTS.md` o `CLAUDE.md`.

Explorar el grafo:

```bash
crs summary ./aws-reference-example
crs search ./aws-reference-example dynamodb
```

Realizar una consulta de arquitectura:

```bash
crs ask ./aws-reference-example \
  "¿Qué se ve afectado si elimino las tablas DynamoDB de dominio?" \
  --json
```

Ejecutar la misma consulta con un ID de nodo canónico:

```bash
crs impact ./aws-reference-example \
  root::aws_dynamodb_table.domain \
  --depth 3
```

## Integraciones con agentes

Codex y Claude Code se instalan automáticamente mediante `crs init`.

```bash
crs install-agent ./aws-reference-example
```

Las integraciones adicionales se pueden instalar explícitamente:

```bash
crs install-agent ./aws-reference-example --target cursor
crs install-agent ./aws-reference-example --target windsurf
crs install-agent ./aws-reference-example --target all
```

Los targets disponibles son `base`, `codex`, `claude`, `cursor`, `windsurf` y `all`. El target predeterminado `base` instala Codex y Claude Code.

CRS administra únicamente sus propias secciones marcadas y conserva el contenido no relacionado de los archivos de instrucciones existentes.

## Comandos principales

| Comando | Propósito |
| --- | --- |
| `crs init <proyecto>` | Indexa Terraform, persiste la memoria e instala las reglas base de agentes. |
| `crs summary <proyecto>` | Muestra estadísticas del grafo por tipo de nodo y dominio. |
| `crs search <proyecto> <término>` | Busca nodos por nombre, ID canónico, archivo o dominio. |
| `crs impact <proyecto> <nodo>` | Rastrea dependencias e impacto de cambios aguas abajo. |
| `crs failure <proyecto> <nodo>` | Rastrea propagación de fallas y riesgos inferidos. |
| `crs context <proyecto> <nodo>` | Produce contexto JSON acotado para una LLM. |
| `crs ask <proyecto> <pregunta>` | Resuelve una consulta en lenguaje natural y ejecuta una consulta de grafo. |
| `crs agent ...` | Alias de `crs ask`. |
| `crs preflight <proyecto>` | Compara el Terraform actual con la memoria guardada. |
| `crs graph-html <proyecto>` | Genera un grafo HTML interactivo. |
| `crs chaos <proyecto> <nodo>` | Genera un plan de experimento de caos basado en el grafo. |
| `crs postmortem <proyecto> <nodo>` | Genera un borrador de postmortem en Markdown. |
| `crs benchmark-tokens <proyecto> <pregunta>` | Compara el tamaño del repositorio completo con el contexto CRS. |
| `crs backend-status <proyecto>` | Muestra el estado de los backends JSON y CodeLoom. |
| `crs install-agent <proyecto>` | Instala o actualiza instrucciones locales para agentes. |
| `crs disable <proyecto>` | Elimina instrucciones y scripts auxiliares administrados por CRS. |

Usar `--json` para obtener salida estructurada, `--depth N` para controlar el recorrido del grafo y `--detail minimal|summary|full` para controlar el tamaño del contexto.

## Preflight de Terraform

Después de modificar el código Terraform, CRS puede comparar el nuevo grafo con el snapshot almacenado:

```bash
crs preflight ./aws-reference-example --max-affected 10
terraform plan
```

Preflight devuelve el exit code `2` cuando se supera el límite de nodos afectados, por lo que puede utilizarse como gate de CI.

CRS analiza relaciones estructurales del código fuente. No reemplaza `terraform plan`, la validación de providers ni la inspección del estado desplegado.

## Benchmark de referencia

El proyecto incluido `aws-reference-example` representa una plataforma serverless de seguros construida con Cognito, CloudFront, S3, WAF, API Gateway, Lambda, Step Functions, DynamoDB, EventBridge, SQS, SNS, KMS, Secrets Manager, CloudWatch y X-Ray.

Grafo medido:

- 11 archivos Terraform
- 96 nodos CRS
- 151 relaciones
- 11 nodos aguas abajo afectados por la eliminación de las tablas DynamoDB de dominio

Estimación de contexto medida:

| Modo de contexto | Tokens estimados | Reducción frente al repositorio completo |
| --- | ---: | ---: |
| Repositorio Terraform completo | 7.481 | - |
| CRS `minimal` | 1.892 | 74,71 % |
| CRS `summary` | 2.063 | 72,42 % |
| CRS `full` | 3.774 | 49,55 % |

El benchmark integrado estima los tokens mediante `ceil(caracteres / 4)`. Para mediciones de facturación se deben utilizar los valores reportados por el proveedor de la LLM.

## Deshabilitar CRS

Eliminar las instrucciones administradas para agentes y conservar la memoria del grafo:

```bash
crs disable ./aws-reference-example
```

Eliminar instrucciones, memoria, scripts auxiliares y reportes generados para realizar una prueba de control limpia:

```bash
crs disable ./aws-reference-example --remove-memory
```

Después de deshabilitar CRS, se debe abrir una nueva sesión del agente para que la comparación no reutilice instrucciones cargadas previamente.

## Arquitectura y seguridad

CRS utiliza un scanner HCL liviano, un indexador de grafos, consultas BFS acotadas, persistencia JSON y sincronización con CodeLoom. Nunca ejecuta Terraform ni expresiones HCL.

El indexador ignora archivos que resuelven fuera de la raíz del proyecto y oculta atributos literales sensibles, como contraseñas, tokens, secretos, claves privadas y credenciales. El contenido HTML generado se escapa. Los comandos externos de sincronización configurados se ejecutan sin shell.

El directorio `.crs/` puede revelar la topología de la infraestructura, nombres de recursos, rutas y metadatos de configuración. Se recomienda agregarlo a `.gitignore` cuando esa información no deba versionarse.

## Limitaciones actuales

- Terraform/HCL es el único formato de infraestructura soportado actualmente.
- El scanner HCL es heurístico y no un parser completo de Terraform.
- Los bloques dinámicos complejos, expresiones profundamente anidadas o patrones avanzados de `for_each` pueden producir relaciones incompletas.
- La detección de intención en lenguaje natural y la resolución de componentes son heurísticas.
- CRS analiza la estructura del código fuente, no el estado Terraform desplegado.
- Las reglas de agentes se cargan al iniciar una sesión; una sesión existente podría no detectar instrucciones recién instaladas.

## Documentación

En español:

- [Guía de uso](guia-uso.md)
- [Referencia CLI](referencia-cli.md)
- [Comportamiento de agentes](agentes.md)
- [Integración con agentes locales](local-agents.md)
- [Integración con Codex](codex-integration.md)
- [Preflight de Terraform](preflight-terraform.md)
- [Benchmark de tokens](token-benchmark.md)
- [Caso de prueba de la plataforma de seguros](caso-prueba-dynamodb-seguros.md)
- [Benchmark de la plataforma de seguros](benchmark-eliminacion-dynamodb-seguros.md)

En inglés:

- [README principal](../../README.md)
- [Guía de uso](../usage-guide.md)
- [Referencia CLI](../cli-reference.md)
- [Arquitectura](../architecture.md)
- [Caso de prueba de la plataforma de seguros](../insurance-dynamodb-test-case.md)
- [Benchmark de la plataforma de seguros](../insurance-dynamodb-benchmark.md)

## Estado del proyecto

CRS es actualmente un proyecto beta. La indexación principal, las consultas de grafo, las integraciones locales con agentes, el backend CodeLoom, los reportes, el benchmark de tokens y el flujo preflight están implementados y cubiertos por el smoke test del repositorio.

Las próximas áreas de desarrollo incluyen parsing HCL formal, integración con el JSON de `terraform plan`, soporte para otros formatos de infraestructura como código y búsqueda semántica más avanzada.

## Contribuir

Se aceptan contribuciones, reportes de errores, fixtures Terraform y comparaciones reproducibles entre agentes. Los cambios deben mantenerse enfocados, incluir validación cuando modifican el comportamiento y evitar versionar la memoria generada en `.crs/`, salvo que sea un fixture de prueba intencional.

## Licencia

MIT
