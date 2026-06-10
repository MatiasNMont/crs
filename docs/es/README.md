# CRS — Code Relationship System

> Memoria de grafo local para infraestructura Terraform, pensada para que las LLMs respondan preguntas de arquitectura, impacto y fallas **gastando la menor cantidad de tokens posible**.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Terraform](https://img.shields.io/badge/terraform-HCL-7B42BC)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-beta-orange)

CRS indexa tus archivos `.tf`, construye un grafo de componentes y relaciones, y lo guarda como memoria local (JSON + export [CodeLoom](codeloom.md)). Cuando una LLM (Claude Code, Codex, o cualquier agente) necesita razonar sobre tu infraestructura, consulta el grafo en lugar de leer todo el repositorio: **menos contexto, menos tokens, respuestas más precisas**.

```text
Pregunta: "¿Que se ve afectado si elimino las tablas DynamoDB de dominio?"

  Sin CRS  →  la LLM lee N archivos .tf completos        (miles de tokens)
  Con CRS  →  la LLM recibe el subgrafo relevante         (cientos de tokens)
              nodos afectados + relaciones + riesgos
```

---

## Tabla de contenidos

- [Características](#características)
- [Cómo funciona](#cómo-funciona)
- [Instalación](#instalación)
- [Inicio rápido](#inicio-rápido)
- [Comandos](#comandos)
- [Integración con agentes LLM](#integración-con-agentes-llm)
- [Seguridad](#seguridad)
- [Documentación](#documentación)
- [Limitaciones](#limitaciones)
- [Roadmap](#roadmap)
- [Contribuir](#contribuir)
- [Licencia](#licencia)

---

## Características

- 🧠 **Memoria de grafo local**: indexa Terraform y persiste nodos, relaciones y configuración en `.crs/`. Sin servicios remotos, sin MCP, sin telemetría.
- 🔍 **Consultas de impacto**: *"si cambio A, ¿qué afecta?"* (`crs impact`).
- 💥 **Análisis de fallas**: *"si se cae A, ¿qué problemas puede tener?"* (`crs failure`), con riesgos inferidos por dominio (datos, red, seguridad, compute, mensajería, negocio).
- 🤖 **Agente de lenguaje natural**: `crs ask "¿Que se ve afectado si elimino las tablas DynamoDB de dominio?"` detecta la intención, resuelve el componente y ejecuta el comando correcto.
- ✂️ **Contexto compacto para LLM**: `crs context` devuelve solo el subgrafo relevante en JSON, listo para inyectar en un prompt.
- 🚦 **Preflight antes de `terraform apply`**: compara el grafo nuevo contra la memoria, calcula el blast radius de cada cambio y falla (exit code `2`) si supera un umbral. Ideal para CI.
- 🔥 **Chaos Engineering**: genera planes de experimentos (hipótesis, señales, guardrails, condiciones de aborto) basados en el blast radius real del grafo.
- 📊 **Benchmark de tokens**: mide cuántos tokens ahorra usar CRS frente a leer todo el repositorio.
- 🕸️ **Visualización interactiva**: `crs graph-html` genera un grafo navegable (filtros, zoom, detalle por nodo) en un único archivo HTML sin dependencias externas.
- 📝 **Postmortems**: borrador automático de postmortem a partir del análisis de falla.
- 🔌 **Integración con Codex y Claude Code sin MCP**: `crs install-agent` instala reglas locales (`AGENTS.md` / `CLAUDE.md`) para que los agentes consulten CRS antes de hacer grep.

## Cómo funciona

```text
            ┌───────────────┐
  *.tf ───▶ │  hcl_scanner  │  bloques resource/module/data/variable/output/locals
            └──────┬────────┘
                   ▼
            ┌───────────────┐
            │    indexer    │  nodos + relaciones (references, depends_on,
            └──────┬────────┘  contains, exposes, uses_variable, module_source)
                   ▼
            ┌───────────────┐     ┌──────────────────────────────┐
            │    memoria    │ ──▶ │ .crs/graph.json              │
            │ (json/codeloom)│    │ .crs/nodes/*.json            │
            └──────┬────────┘     │ .crs/codeloom/*.jsonl        │
                   ▼              └──────────────────────────────┘
   ┌────────────────────────────────────────────┐
   │  consultas: ask · impact · failure ·       │
   │  context · chaos · preflight · postmortem  │
   └────────────────────────────────────────────┘
```

1. **Indexación** (`crs init`): un scanner HCL liviano (sin dependencias) detecta bloques, atributos y referencias, infiere tags de dominio y arma el grafo.
2. **Persistencia**: el grafo se guarda como JSON local con snapshots históricos en `.crs/history/`. Si la librería `codeloom` está instalada, también se sincroniza con su pipeline.
3. **Consulta**: los comandos recorren el grafo (BFS con profundidad configurable) en lugar de releer el código. La LLM recibe solo nodos y relaciones relevantes, con punteros a archivo y líneas por si necesita abrir algo puntual.

Los IDs de nodo incluyen el scope de carpeta para evitar colisiones entre módulos:

```text
root::module.data
modules/data::aws_rds_cluster.this
modules/eks::aws_eks_cluster.this
```

## Instalación

Requiere Python 3.10+. Sin dependencias obligatorias.

```bash
git clone https://github.com/<tu-org>/crs.git
cd crs
python -m pip install -e .
```

CodeLoom se instala automaticamente y es el backend predeterminado:

```bash
python -m pip install -e .
```

Verificar:

```bash
crs --help
```

También funciona sin instalar: `python -m crs --help` (con `src/` en `PYTHONPATH`).

## Inicio rápido

```bash
# 1. Indexar tu proyecto Terraform
crs init ./mi-infraestructura

# 2. Ver qué detectó
crs summary ./mi-infraestructura
crs search ./aws-reference-example dynamodb

# 3. Preguntar en lenguaje natural
crs ask ./aws-reference-example "What is affected if I delete the domain DynamoDB tables?"
crs ask ./mi-infraestructura "¿qué afecta cambiar el módulo de red?" --json

# 4. Validar impacto antes de aplicar cambios
crs preflight ./mi-infraestructura --max-affected 5

# 5. Visualizar el grafo
crs graph-html ./mi-infraestructura
```

## Comandos

| Comando | Descripción |
| --- | --- |
| `crs init <proyecto>` | Indexa el Terraform y crea/actualiza la memoria en `.crs/`. |
| `crs summary <proyecto>` | Resumen del grafo: nodos, relaciones, dominios. |
| `crs search <proyecto> <término>` | Busca nodos por nombre, archivo o dominio. |
| `crs impact <proyecto> <nodo>` | Si cambio A, qué partes afecta (dependencias + aguas abajo). |
| `crs failure <proyecto> <nodo>` | Si se cae A, qué problemas puede tener + riesgos por dominio. |
| `crs ask <proyecto> "<pregunta>"` | Agente: detecta intención y ejecuta `context` + `impact`/`failure`. |
| `crs context <proyecto> <nodo>` | Subgrafo compacto en JSON para inyectar a una LLM. |
| `crs postmortem <proyecto> <nodo>` | Borrador de postmortem basado en el grafo. |
| `crs chaos <proyecto> <nodo>` | Plan de Chaos Engineering con blast radius real (JSON/MD/HTML). |
| `crs preflight <proyecto>` | Diff de grafo + blast radius antes de `terraform apply`. Exit `2` si supera `--max-affected`. |
| `crs benchmark-tokens <proyecto> "<pregunta>"` | Compara tokens estimados con y sin CRS. |
| `crs graph-html <proyecto>` | Grafo interactivo en un HTML autocontenido. |
| `crs install-agent <proyecto>` | Instala reglas CRS para Codex (`AGENTS.md`) y Claude Code (`CLAUDE.md`). |
| `crs backend-status <proyecto>` | Estado de los backends de memoria. |

Opciones comunes: `--depth N` (profundidad del recorrido, default 3), `--json` (salida estructurada), `--backend json|codeloom`.

Referencia completa con todos los flags, variables de entorno y exit codes: [referencia-cli.md](referencia-cli.md).

## Integración con agentes LLM

CRS está diseñado para el flujo *"grafo primero, archivos después"*:

```bash
crs install-agent ./mi-infraestructura
```

Esto agrega bloques a `AGENTS.md` (Codex) y `CLAUDE.md` (Claude Code) con la regla central:

> Antes de hacer grep o exploración amplia, ejecutá `crs ask . "<pregunta>" --json` y usá `decision`, `context` y `result` como fuente primaria. Abrí solo los archivos listados en `context.nodes`.

La salida `--json` de `crs ask` incluye:

- `decision`: intención detectada, nodo resuelto y confianza heurística.
- `context`: nodos y relaciones que conviene pasarle a la LLM.
- `result`: resultado estructurado de `impact`/`failure`.
- `rendered`: respuesta legible para humanos.

En proyectos de prueba, el modo CRS reduce el contexto necesario en más de un 90 % frente a leer todos los `.tf` (medilo en tu repo con `crs benchmark-tokens`).

## Seguridad

CRS es **100 % local**: no hace llamadas de red, no envía datos a ningún servicio y no requiere credenciales.

- **Redacción de secretos**: al indexar, los valores literales de atributos sensibles (`password`, `secret`, `token`, `api_key`, `private_key`, `access_key`, `credential`, y `default`/`value` de bloques con nombre sensible) se reemplazan por `***REDACTED***` antes de persistir o enviar a una LLM. Las referencias (`var.x`) se conservan para no romper el grafo.
- **Sin shell**: la sincronización externa con CodeLoom (`CRS_CODELOOM_SYNC_COMMAND`) se ejecuta sin shell, con sustitución segura de placeholders y timeout.
- **Contención de archivos**: el indexador ignora symlinks y archivos que resuelvan fuera de la raíz del proyecto.
- ⚠️ **Aún así**: los archivos `.tf` y la memoria `.crs/` pueden contener información sensible de tu infraestructura (CIDRs, nombres de recursos, topología). Agregá `.crs/` a tu `.gitignore` si no querés versionar la memoria, y tratá el contenido de los `.tf` de terceros como datos no confiables al pasarlos a una LLM.

Para reportar vulnerabilidades: [SECURITY.md](SECURITY.md).

## Documentación

| Guía | Contenido |
| --- | --- |
| [Guía de uso](guia-uso.md) | Recorrido completo comando por comando. |
| [Referencia CLI](referencia-cli.md) | Todos los flags, variables de entorno y exit codes. |
| [Arquitectura](arquitectura.md) | Diseño interno: scanner, indexer, grafo, backends. |
| [Agentes CRS](agentes.md) | Cómo funciona la detección de intención de `crs ask`. |
| [Backend CodeLoom](codeloom.md) | Integración con la librería y CLI de CodeLoom. |
| [Agentes locales sin MCP](local-agents.md) | Reglas para Codex y Claude Code. |
| [Integración con Codex](codex-integration.md) | Flujo detallado con Codex. |
| [Chaos Engineering](chaos-engineering.md) | Escenarios disponibles y cómo extenderlos. |
| [Preflight de Terraform](preflight-terraform.md) | Gate de impacto para CI/CD. |
| [Benchmark de tokens](token-benchmark.md) | Metodología de medición de ahorro. |
| [Benchmark: eliminar DynamoDB](benchmark-eliminacion-dynamodb-seguros.md) | Medicion real de tokens sobre la plataforma de seguros. |
| [Features de ahorro de contexto](features-ahorro-contexto.md) | Cómo gastan menos tokens los niveles de detalle, la poda del payload y el orden estable para caching. |
| [Caso de prueba: DynamoDB](caso-prueba-dynamodb-seguros.md) | Ejemplo end-to-end con las tablas de dominio de la aseguradora. |

## Limitaciones

- El scanner HCL es **heurístico** (regex + balanceo de llaves), no un parser HCL formal. Cubre los patrones comunes de Terraform; expresiones muy dinámicas (`for_each` complejos, `dynamic` anidados) pueden generar relaciones incompletas.
- No reemplaza `terraform graph` ni `terraform plan`: CRS analiza relaciones estructurales del código, no el estado real desplegado.
- Soporte actual: **Terraform/HCL**. Otros IaC (CloudFormation, Pulumi, CDK) están en el roadmap.
- La detección de intención de `crs ask` es heurística (patrones ES/EN); para preguntas complejas usá los comandos explícitos.

## Roadmap

- [ ] Parser HCL formal opcional (Tree-sitter / `hcl2json`).
- [ ] Integración con `terraform plan -json` para enriquecer el preflight con cambios reales.
- [ ] Soporte multi-IaC (CloudFormation, Pulumi).
- [ ] Embeddings opcionales vía CodeLoom para búsqueda semántica.
- [ ] GitHub Action oficial para el gate de preflight.

## Contribuir

¡Las contribuciones son bienvenidas! Leé [CONTRIBUTING.md](CONTRIBUTING.md) para el flujo de trabajo, estilo de código y cómo correr las pruebas.

Si encontrás un bug o tenés una idea, abrí un [issue](../../issues).

## Licencia

MIT © Boxum
