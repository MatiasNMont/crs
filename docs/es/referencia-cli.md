# Referencia CLI de CRS

Referencia completa de comandos, flags, variables de entorno y exit codes.

Convenciones:

- `<proyecto>`: carpeta raíz del proyecto Terraform (debe existir).
- `<nodo>`: ID canonico (`root::aws_dynamodb_table.domain`) o fragmento no ambiguo (`dynamodb`).
- CodeLoom se instala junto con CRS y es el backend predeterminado. Todos los comandos que leen el grafo aceptan `--backend json|codeloom`.

## Opciones globales

| Flag | Default | Descripción |
| --- | --- | --- |
| `--backend {json,codeloom}` | `CRS_MEMORY_BACKEND` o `codeloom` | Backend de memoria a usar. |
| `--depth N` | `3` (`context`: `2`) | Profundidad del recorrido BFS sobre el grafo. |
| `--json` | desactivado | Salida JSON estructurada en lugar de texto. |
| `--detail {minimal,summary,full}` | `summary` | Cuánta config HCL viaja en el contexto. En `context`, `ask`/`agent`, `benchmark-tokens`. Ver [features de ahorro de contexto](features-ahorro-contexto.md). |

`--detail`: `minimal` = solo estructura (id, tipo, archivo, líneas, tags), cero config; `summary` = config completa solo del nodo foco; `full` = config de todos los nodos. La salida JSON es determinista (claves y nodos ordenados) para habilitar prompt caching del proveedor.

---

## `crs init <proyecto>`

Indexa los `.tf`, crea/actualiza la memoria en `.crs/` e instala automaticamente las reglas base para Codex (`AGENTS.md`) y Claude Code (`CLAUDE.md`).

| Flag | Descripción |
| --- | --- |
| `--strict-backend` | Falla si la sincronización con CodeLoom no es posible (sin fallback). |

Genera:

```text
.crs/
  graph.json            # grafo completo
  nodes/<id>-<hash>.json# un archivo por nodo con relaciones in/out
  history/graph-*.json  # snapshots históricos
  codeloom/             # export compatible (manifest, jsonl, índice)
```

Notas:

- Ignora `.terraform/`, `.git/` y `.crs/`.
- No sigue symlinks ni archivos fuera de la raíz del proyecto.
- Redacta valores literales de atributos sensibles antes de persistir.

## `crs summary <proyecto>`

Imprime el resumen del grafo: cantidad de nodos por tipo, relaciones y dominios detectados.

## `crs search <proyecto> <término>`

Busca nodos cuyo ID, archivo o tags de dominio contengan el término. Útil para descubrir el ID canónico antes de `impact`/`failure`.

## `crs impact <proyecto> <nodo> [--depth N] [--json]`

Responde *"si cambio A, qué partes afecta"*:

- `direct_dependencies`: qué usa el nodo (revisar antes de cambiar).
- `affected`: dependientes aguas abajo hasta `--depth`, con evidencia de la relación.

## `crs failure <proyecto> <nodo> [--depth N] [--json]`

Responde *"si se cae A, qué problemas puede tener"*:

- Dependientes afectados (igual que `impact`).
- `risks`: riesgos inferidos por dominio (datos, red, seguridad, compute, mensajería).

## `crs postmortem <proyecto> <nodo> [--depth N] [--out archivo.md]`

Genera un borrador de postmortem en Markdown a partir del análisis de falla. Sin `--out` imprime a stdout. El borrador debe completarse con evidencia real (métricas, logs, timeline).

## `crs context <proyecto> <nodo> [--depth N]`

Devuelve el subgrafo relevante en JSON: nodo foco, nodos relacionados (con archivo y rango de líneas) y relaciones. Es el payload recomendado para inyectar a una LLM.

## `crs ask <proyecto> "<pregunta>" [--depth N] [--json] [--show-context-summary]`

Agente de lenguaje natural (alias: `crs agent`):

1. Extrae términos de la pregunta y resuelve el nodo más probable (con score y confianza).
2. Detecta la intención: `impact` (cambio), `failure` (caída) o `context` (otro).
3. Ejecuta `context` + el comando correspondiente.

La salida `--json` emite por defecto un **payload podado** (`decision`, `command`, `context`, `result`) optimizado para gastar menos tokens — descarta metadata de agentes, el texto `rendered` y campos duplicados. Usá `--full-payload` para el payload completo (debug). Soporta preguntas en español e inglés.

## `crs chaos <proyecto> <componente> [opciones]`

Genera un plan de Chaos Engineering basado en el blast radius del grafo.

| Flag | Default | Descripción |
| --- | --- | --- |
| `--count N` | `3` | Cantidad de escenarios. |
| `--depth N` | `3` | Profundidad de blast radius. |
| `--scenario ID` | auto por dominio | Escenario específico; repetible. |
| `--out DIR` | `<proyecto>/.crs/chaos` | Directorio de salida. |
| `--json` | — | Imprime el plan en JSON. |

Escenarios disponibles: `data-outage`, `data-latency`, `network-packet-loss`, `compute-pod-kill`, `messaging-backlog`, `security-secret-deny`

Genera `<slug>.chaos.json`, `.md` y `.html` con hipótesis, señales, guardrails y condiciones de aborto por experimento.

## `crs preflight <proyecto> [opciones]`

Regenera el grafo, lo compara contra la memoria persistida y reporta el impacto **antes** de `terraform plan/apply`.

| Flag | Descripción |
| --- | --- |
| `--max-affected N` | Falla (exit `2`) si algún nodo cambiado afecta a más de N nodos. |
| `--update-memory` | Persiste el grafo nuevo como memoria si el preflight termina. |
| `--strict-backend` | Falla si la sincronización externa falla. |
| `--json` | Reporte completo en JSON. |

Genera en `<proyecto>/.crs/preflight/`: reporte JSON, Markdown, HTML y un **prompt listo para LLM** (`latest.prompt.md`) con el diff exacto de cada nodo, dominios afectados y riesgos.

Uso típico en CI:

```bash
crs preflight . --max-affected 5 || exit 1
```

## `crs benchmark-tokens <proyecto> "<pregunta>" [--depth N] [--json]`

Compara los tokens estimados (`ceil(caracteres/4)`) entre:

- **raw**: todos los `.tf` del proyecto como contexto.
- **CRS**: el payload compacto de `crs ask --json`.

Genera reportes en `<proyecto>/.crs/benchmarks/` (JSON, MD, HTML y ambos prompts).

## `crs graph-html <proyecto> [--out archivo.html]`

Genera una visualización interactiva del grafo en un único HTML autocontenido (sin CDNs ni dependencias): búsqueda, filtros por tipo y dominio, zoom/pan, drag de nodos y detalle de configuración por nodo.

Default: `<proyecto>/.crs/graph.html`.

## `crs install-agent <proyecto> [--target base|all|codex|claude|cursor|windsurf] [--force]`

Instala reglas locales para que los agentes usen CRS antes de explorar el repo. `--target` se puede repetir. Sin `--target`, instala `base` (Codex + Claude).

## `crs disable <proyecto> [--remove-memory]`

Elimina las reglas administradas por CRS para Codex, Claude, Cursor y Windsurf, junto con los helpers de agentes. Conserva cualquier contenido ajeno a CRS dentro de `AGENTS.md` y `CLAUDE.md`.

Por defecto mantiene `.crs/`. Con `--remove-memory` tambien elimina el grafo y los reportes para realizar una comparacion completamente limpia sin CRS. Inicia una sesion nueva del agente despues de ejecutar el comando.

- `AGENTS.md` (Codex) y/o `CLAUDE.md` (Claude Code), en bloques delimitados que se pueden re-ejecutar sin duplicar.
- Helpers en `.crs/agents/`: `crs-agent-prompt.md`, `ask-crs.ps1`, `ask-crs.sh`.

`--force` reescribe los scripts auxiliares existentes.

## `crs backend-status <proyecto>`

Muestra en JSON: backend default, disponibilidad y versión de la librería `codeloom`, variables de entorno configuradas y existencia de `graph.json` y del export CodeLoom.

---

## Variables de entorno

| Variable | Default | Descripción |
| --- | --- | --- |
| `CRS_MEMORY_BACKEND` | `codeloom` | Backend default (`json` o `codeloom`). |
| `CRS_CODELOOM_BIN` | — | Binario de CodeLoom para sincronización externa (`<bin> ingest --project ... --graph ... --out ...`). |
| `CRS_CODELOOM_SYNC_COMMAND` | — | Comando custom de sincronización. Placeholders: `{project}`, `{graph}`, `{codeloom_dir}`. Se tokeniza y ejecuta **sin shell**; los placeholders se sustituyen por token. |
| `CRS_CODELOOM_EMBED` | `0` | `1` activa embeddings en el pipeline de CodeLoom. |
| `CRS_CODELOOM_LANG` | `auto` | Lenguaje para el pipeline de CodeLoom. |
| `CRS_CODELOOM_GIT` | `0` | `1` activa integración git del pipeline de CodeLoom. |

## Exit codes

| Código | Significado |
| --- | --- |
| `0` | OK. |
| `1` | Error (nodo no encontrado, memoria inexistente, argumento inválido, etc.). El detalle sale por stderr como `crs error: ...`. |
| `2` | Solo `preflight`: el blast radius superó `--max-affected`. |

## Tipos de relaciones del grafo

| Relación | Significado |
| --- | --- |
| `references` | La configuración de un nodo menciona a otro componente. |
| `uses_variable` | Un componente usa una variable (`var.x`). |
| `depends_on` | Dependencia Terraform explícita. |
| `exposes` | Un output expone un recurso o módulo. |
| `module_source` | Un módulo apunta a una carpeta local. |
| `contains` | Un módulo contiene recursos de su carpeta. |
