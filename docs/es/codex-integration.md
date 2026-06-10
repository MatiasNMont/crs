# Integrar CRS con Codex

La idea es que Codex no lea todo el repositorio al recibir una pregunta. CRS debe actuar como memoria previa: resuelve la pregunta, consulta el grafo y produce un contexto acotado.

## Instalacion recomendada

CRS liviano:

```powershell
cd <ruta-de-crs>
python -m pip install -e .
```

CRS incluye CodeLoom por defecto:

```powershell
cd <ruta-de-crs>
python -m pip install -e .
```

## Flujo recomendado

1. Inicializar memoria.

```powershell
crs init <ruta-del-proyecto>
```

2. Hacer la pregunta a CRS.

```powershell
crs ask <ruta-del-proyecto> "What is affected if I delete the domain DynamoDB tables?" --json
```

3. Enviar a Codex solo estos campos:

- `decision`
- `agents`
- `context`
- `result`

4. Pedirle a Codex que use esos nodos antes de abrir archivos.

## Prompt recomendado para Codex

```text
Pregunta del usuario:
<pregunta original>

Contexto CRS:
<pegar JSON de crs ask --json, o al menos decision/context/result>

Instrucciones:
- Usa primero la memoria CRS.
- No hagas grep completo del repositorio.
- Si necesitas leer archivos, lee solo los archivos y rangos mencionados en context.nodes.
- Para impacto de cambios, usa result.affected y result.direct_dependencies.
- Para incidentes, usa result.risks y result.affected.
- Si el contexto no alcanza, explica que nodo o archivo adicional necesitas.
```

## Ejemplo impacto

Comando:

```powershell
crs ask <ruta-del-proyecto> "What is affected if I delete the domain DynamoDB tables?" --json
```

Codex deberia recibir que CRS detecto:

```text
intent: impact
node_id: modules/data::aws_rds_cluster.this
```

Y deberia responder usando:

- dependencias directas de las tablas DynamoDB
- componentes afectados aguas abajo
- archivos y lineas de los nodos relacionados

## Ejemplo falla

Comando:

```powershell
crs ask <ruta-del-proyecto> "What happens if the domain DynamoDB tables fail?" --json
```

Codex deberia recibir que CRS detecto:

```text
intent: failure
node_id: modules/data::aws_rds_cluster.this
```

Y deberia responder usando:

- riesgos probables
- dependientes detectados
- dominio inferido: data, network, security
- posible borrador de postmortem si se pide

## Wrapper simple para Codex

Un wrapper externo puede hacer:

```powershell
$repo = "<ruta-del-proyecto>"
$question = "What is affected if I delete the domain DynamoDB tables?"
$context = crs ask $repo $question --json
```

Luego mandar a Codex:

```text
Usa este contexto CRS:
<contenido de $context>
```

## Integracion local sin MCP, recomendada

Instala reglas persistentes en el repo:

```powershell
crs install-agent <ruta-del-proyecto> --target codex
```

Esto crea/actualiza:

```text
AGENTS.md
.crs/agents/ask-crs.ps1
.crs/agents/crs-agent-prompt.md
```

Cuando preguntes algo como:

```text
Que pasa si cambio este componente?
```

Codex debe leer `AGENTS.md` y ejecutar:

```powershell
crs ask . "Que pasa si cambio este componente?" --json
```

No requiere MCP ni servicios remotos.

## Relacion CRS, CodeLoom y Codex

```text
CodeLoom = memoria/grafo consultable
CRS = orquestador de preguntas operativas sobre Terraform
Codex = razonamiento y edicion usando contexto reducido
```

## Prompt para Codex usando CRS + CodeLoom

```text
Primero usa CRS:
crs ask <repo> "<pregunta>" --json

Si CRS resuelve el nodo, usa decision/context/result.
Si necesitas mas busqueda semantica o estructural, usa los archivos locales .crs/codeloom/ y .crs/codeloom-native/.
No hagas grep completo salvo que CRS y CodeLoom no alcancen.
```

## Regla operativa

Antes de usar busqueda amplia:

```powershell
crs ask <repo> "<pregunta>" --json
```

Solo si CRS no puede resolver el nodo o el contexto no alcanza, Codex deberia pedir busqueda adicional.

## Integracion ideal por tool

Si Codex puede llamar herramientas locales, exponer estas operaciones:

```text
crs_search(term)
crs_context(node)
crs_impact(node)
crs_failure(node)
crs_ask(question)
```

Politica:

- Toda pregunta en repo con `.crs/graph.json` debe llamar primero a `crs_ask`.
- Si `intent=impact`, usar `result` de impacto.
- Si `intent=failure`, usar `result` de falla.
- Si `intent=context`, usar `context` y pedir mas detalle solo si hace falta.
