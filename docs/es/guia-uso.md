# Guia de uso de CRS

CRS significa `Code Relationship System`. La idea es crear una memoria de grafo para proyectos Terraform, de forma que una LLM pueda razonar sobre componentes, relaciones e impacto sin leer todo el codigo cada vez.

## 1. Instalar CRS

Desde la carpeta del proyecto:

```powershell
cd <ruta-de-crs>
python -m pip install -e .
```

Validar que quedo disponible:

```powershell
crs --help
```

Si no quieres instalarlo, puedes ejecutarlo asi:

```powershell
$env:PYTHONPATH='<ruta-de-crs>\src'
python -m crs --help
```

## 2. Inicializar memoria sobre un Terraform

Ejemplo con la arquitectura de seguros creada en este workspace:

```powershell
crs init <ruta-del-proyecto>
```

CodeLoom es el backend default:

```powershell
crs init <ruta-del-proyecto>
```

Esto crea:

```text
aws-reference-example/
  .crs/
    graph.json
    nodes/
      <node-id>.json
```

Ademas, `crs init` instala automaticamente las reglas base para Codex y Claude Code:

```text
AGENTS.md
CLAUDE.md
.crs/agents/
```

Luego de inicializar, inicia una sesion nueva del agente para que cargue esas reglas. Los agentes opcionales se pueden agregar despues:

```powershell
crs install-agent <ruta-del-proyecto> --target cursor
crs install-agent <ruta-del-proyecto> --target windsurf
```

`graph.json` es la memoria global. Cada archivo dentro de `nodes/` guarda la configuracion completa de un componente y sus relaciones entrantes/salientes.

Tambien se crea `.crs/codeloom/` con `manifest.json`, `nodes.jsonl`, `relations.jsonl` y `context-index.json`.

## 3. Ver resumen del grafo

```powershell
crs summary <ruta-del-proyecto>
```

Sirve para revisar si CRS detecto recursos, modulos, variables, outputs y relaciones.

## 4. Buscar componentes

Si no sabes el ID exacto:

```powershell
crs search <ruta-del-proyecto> dynamodb
```

Ejemplo de ID canonico:

```text
modules/data::aws_rds_cluster.this
```

CRS agrega un scope delante del recurso para evitar colisiones entre modulos:

```text
root::module.data
modules/data::aws_rds_cluster.this
modules/eks::aws_eks_cluster.this
```

## 5. Preguntar impacto de cambio

Pregunta: "si elimino las tablas DynamoDB de dominio, que afecta?"

```powershell
crs impact <ruta-del-proyecto> aws_rds_cluster.this
```

La respuesta se divide en:

- Dependencias directas que conviene revisar antes de cambiar el componente.
- Componentes aguas abajo que pueden verse afectados.
- Evidencia de la relacion detectada.

Esto le permite a una LLM leer primero el grafo y despues abrir solo los archivos relevantes.

## 6. Preguntar impacto de caida

Pregunta: "si falla DynamoDB, que problematicas puede tener?"

```powershell
crs failure <ruta-del-proyecto> aws_rds_cluster.this
```

CRS combina:

- Dependientes detectados por el grafo.
- Dominio inferido del componente: datos, red, seguridad, compute, etc.
- Riesgos probables.

## 7. Generar postmortem

```powershell
crs postmortem <ruta-del-proyecto> aws_dynamodb_table.domain --out C:\ruta\postmortem-dynamodb.md
```

El archivo generado es un borrador. Hay que completarlo con datos reales: metricas, logs, timeline, alertas, cambios recientes y decisiones del equipo.

## 8. Generar contexto acotado para una LLM

```powershell
crs context <ruta-del-proyecto> aws_rds_cluster.this
```

Ese JSON es lo que conviene pasarle a la LLM antes de pedir un cambio. La regla practica es:

1. Ejecutar `crs context`.
2. Leer solo los archivos y lineas que aparecen en los nodos relacionados.
3. Evitar `grep` completo salvo que el contexto no alcance.

## 9. Generar vista HTML del grafo

```powershell
crs graph-html <ruta-del-proyecto>
```

Por defecto genera:

```text
<ruta-del-proyecto>\.crs\graph.html
```

Tambien puedes elegir salida:

```powershell
crs graph-html <ruta-del-proyecto> --out C:\ruta\grafo-crs.html
```

La vista permite:

- Buscar nodos por nombre o archivo.
- Filtrar por tipo: `resource`, `module`, `variable`, `output`, etc.
- Filtrar por dominio inferido: `data`, `network`, `security`, etc.
- Hacer click en un nodo para ver configuracion completa.
- Ver relaciones entrantes y salientes.
- Arrastrar nodos, hacer zoom y mover el canvas.

## 10. Preguntar con agentes

CRS puede interpretar preguntas simples y ejecutar automaticamente los comandos correctos.

Impacto de cambio:

```powershell
crs ask <ruta-del-proyecto> "What is affected if I delete the domain DynamoDB tables?"
```

Falla o caida:

```powershell
crs ask <ruta-del-proyecto> "What happens if the domain DynamoDB tables fail?"
```

Salida JSON para integrar con una LLM:

```powershell
crs ask <ruta-del-proyecto> "What is affected if I delete the domain DynamoDB tables?" --json
```

Con CodeLoom, que es el backend default:

```powershell
crs ask <ruta-del-proyecto> "What is affected if I delete the domain DynamoDB tables?"
```

Regla interna:

- Siempre se ejecuta `context-agent`.
- Si detecta cambio, ejecuta `impact-agent`.
- Si detecta falla, ejecuta `failure-agent`.

## 11. Flujo recomendado para cambios

Antes de modificar Terraform:

```powershell
crs search <project> <nombre-del-componente>
crs impact <project> <node>
crs context <project> <node>
```

Despues de modificar Terraform:

```powershell
crs init <project>
crs impact <project> <node>
```

Asi la memoria queda actualizada y se puede comparar el impacto esperado.

## 12. Flujo recomendado para incidentes

Cuando falla un componente:

```powershell
crs failure <project> <node>
crs postmortem <project> <node> --out incidente.md
```

Luego completar el postmortem con evidencia real de AWS, Kubernetes, observabilidad y negocio.
