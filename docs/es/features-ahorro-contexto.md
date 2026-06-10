# Features de ahorro de contexto en CRS

Este documento explica, en lenguaje claro, las tres features que CRS incorpora para gastar menos tokens **sin** perder la información que la LLM necesita para responder bien. Las tres atacan el mismo problema desde ángulos distintos:

> Cada token de contexto que le mandás a una LLM se paga (en dinero y en latencia). CRS ya recortaba el contexto a un subgrafo; estas features recortan **dentro** de ese subgrafo lo que no aporta.

Resumen de una línea por feature:

| Feature | Qué hace | Resultado medido (caso "eliminar DynamoDB") |
| --- | --- | --- |
| 1. Niveles de detalle | Decide cuánta configuración HCL viaja a la LLM | `minimal` / `summary` / `full` — de 5.200 a 3.650 tokens |
| 3. Poda del payload | Borra del JSON los campos que la LLM no usa | `ask --json` pasó de **10.263 → 3.941 tokens (−62 %)** |
| 6. Orden estable | Hace el contexto byte-idéntico entre consultas | Habilita prompt caching (~0,1× en lecturas) |

(La numeración 1/3/6 viene de la lista original de ideas; se implementaron estas tres.)

---

## El concepto base: qué le manda CRS a la LLM

Cuando preguntás algo, CRS no manda todo el Terraform. Manda un **payload**: un JSON con el subgrafo relevante. Tiene esta forma:

```jsonc
{
  "decision":  { "intencion": "impact", "nodo": "...", "confianza": 0.52 },
  "command":   "impact",
  "context": {
    "focus": "modules/data::aws_rds_cluster.this",  // el nodo de la pregunta
    "detail": "summary",
    "nodes":  { ... },        // el nodo foco + sus vecinos
    "relations": [ ... ]      // las aristas entre ellos
  },
  "result": {
    "affected": [ ... ],      // qué se rompe aguas abajo
    "risks":    [ ... ]       // riesgos por dominio
  }
}
```

Las tres features deciden **qué tan gordo es ese JSON** y **qué tan repetible es** entre consultas.

---

## Feature 1 — Niveles de detalle (`--detail`)

### El problema

El campo mas pesado de cada nodo es su `config`: el bloque HCL completo del recurso. En el caso DynamoDB de `aws-reference-example`, el subgrafo tiene 9 nodos. La LLM normalmente necesita la configuracion completa del nodo foco y ubicaciones precisas para sus vecinos.

### Qué hace la feature

Un flag `--detail` con tres niveles, que controla cuánta config viaja:

| Nivel | Qué incluye cada nodo | Cuándo usarlo |
| --- | --- | --- |
| `minimal` | Solo estructura: id, tipo, archivo, líneas, tags de dominio. **Cero config.** | Máximo ahorro. Cuando la LLM solo necesita el mapa de dependencias, no el contenido. |
| `summary` *(default)* | Estructura de todos + **config completa solo del nodo foco**. | El equilibrio. La LLM ve en detalle el recurso que preguntaste y tiene punteros a los vecinos. |
| `full` | Estructura + config completa de **todos** los nodos. | Cuando querés que la LLM razone sobre el contenido de todo el subgrafo sin pedir nada más. |

### Cómo se ve

Pregunta: *"¿Que se afecta si elimino las tablas DynamoDB de dominio?"* — nodo foco `aws_dynamodb_table.domain`, vecinos Lambda, IAM, API Gateway y Step Functions.

```
--detail minimal     focus: {id, tipo, archivo, líneas}        vecino: {id, tipo, archivo, líneas}
--detail summary     focus: {... + config HCL completa}        vecino: {id, tipo, archivo, líneas}   ← config solo del foco
--detail full        focus: {... + config HCL completa}        vecino: {... + config HCL completa}
```

### La idea clave

> El default `summary` se apoya en que CRS **siempre incluye archivo:líneas** de cada nodo. Si la LLM necesita la config de un vecino, la pide por esa ubicación exacta. Es "carga diferida": pagás tokens solo por lo que realmente se usa.

Medido en el caso de seguros: `minimal` 1.892, `summary` 2.063 y `full` 3.774 tokens, frente a 7.481 tokens del repositorio completo.

---

## Feature 3 — Poda del payload

### El problema

Antes, `crs ask --json` devolvía la estructura interna **completa** de la herramienta. Esa estructura sirve para imprimir el reporte humano (`rendered`) y para depurar, pero contenía mucho que a la LLM no le aporta nada y solo gasta tokens:

- `agents`: metadata de qué agentes internos corrieron y con qué propósito.
- `rendered`: el reporte ya formateado en texto (la LLM va a redactar su propia respuesta, no necesita la nuestra).
- El **nodo-componente duplicado**: el recurso afectado venía completo dentro de `result`, **y otra vez** dentro de `context.nodes`.
- En cada nodo afectado, un objeto `relation` con `source`/`target`/`evidence` que repetían información ya implícita en la arista padre→hijo.

### Qué hace la feature

`crs ask --json` ahora emite, por defecto, un **payload podado**: solo `decision`, `command`, `context` y un `result` adelgazado. Cada nodo afectado se reduce a lo esencial:

```jsonc
// Antes (por afectado):                  // Ahora (por afectado):
{                                          {
  "node": "...",                             "node": "...",
  "depth": 2,                                "depth": 2,
  "relation": {                              "via": "references",
    "kind": "references",                    "evidence": "aws_rds_cluster.this"
    "source": "...",                       }
    "target": "...",
    "evidence": "..."
  },
  "file": "...",            ← ya está en context.nodes por id
  "domain_tags": [...]      ← ya está en context.nodes por id
}
```

Las relaciones del contexto pasaron de objetos a **tuplas** `[source, target, kind]` con una leyenda única al lado, en vez de repetir las claves `"source":`, `"target":`, `"kind":` en cada una.

### El resultado

Esta es la feature que mas ahorro. La salida real para el caso DynamoDB reduce el modo `summary` un 72,42 %.

```
Antes (payload completo):   10.263 tokens
Ahora (payload podado):      3.941 tokens     ← −62 %
```

Si necesitás el payload completo para depurar, está el flag `--full-payload` que vuelve al comportamiento anterior.

### La idea clave

> "No mandes dos veces lo mismo." El nodo afectado ya está descrito en `context.nodes` (indexado por su id); en la lista de afectados alcanza con el id, la profundidad y por qué relación se llega. Todo lo demás es redundante.

---

## Feature 6 — Orden estable (prompt caching)

### El problema

Los proveedores de LLM (Anthropic, OpenAI) ofrecen **prompt caching**: si dos requests comparten exactamente el mismo prefijo de texto, el segundo paga ~0,1× por esa parte en lugar del precio completo. Pero el caching es por **coincidencia exacta de bytes**: si una sola coma se mueve, el caché se invalida y pagás todo de nuevo.

Si CRS generara el JSON con las claves o los nodos en orden distinto en cada corrida, el prefijo nunca coincidiría y el caching jamás se activaría.

### Qué hace la feature

Tres garantías de determinismo, para que el contexto sea **byte-idéntico** entre consultas sobre el mismo grafo:

1. **Nodos ordenados** por id, **relaciones ordenadas** como tuplas — siempre en el mismo orden.
2. **Claves del JSON ordenadas** alfabéticamente (`sort_keys=True`) en `ask --json` y `context`.
3. **La pregunta variable va al final** del prompt, no al principio. Así el bloque grande y estable (el contexto del grafo) queda como prefijo cacheable, y lo único que cambia entre preguntas (la pregunta misma) no rompe ese prefijo.

```
┌─────────────────────────────────────────┐
│  Contexto CRS  (estable, byte-idéntico)  │  ← prefijo cacheable: se paga ~0,1× la 2da vez
├─────────────────────────────────────────┤
│  Instrucciones (fijas)                   │
├─────────────────────────────────────────┤
│  Pregunta del usuario (variable)         │  ← lo único que cambia; va al final
└─────────────────────────────────────────┘
```

### El resultado

Verificado: dos corridas de `crs ask --json` sobre el mismo grafo producen una salida **byte-idéntica**. Eso es la precondición para que el caché del proveedor se active.

### La idea clave

> Esta feature no recorta tokens por sí sola; **multiplica el ahorro de las otras dos**. Si hacés varias preguntas sobre la misma infraestructura (lo normal en un troubleshooting), a partir de la segunda el contexto compartido se cobra a una décima parte. Es el ahorro recurrente.

---

## Cómo se combinan

Las tres trabajan juntas en una sola consulta:

```powershell
crs ask <proyecto> "What is affected if I delete the domain DynamoDB tables?" --json --detail summary
```

1. **Feature 1** decide que solo DynamoDB lleva su config completa (los 8 vecinos van como estructura).
2. **Feature 3** poda el JSON: sin `agents`, sin `rendered`, sin nodos duplicados, relaciones como tuplas.
3. **Feature 6** ordena todo de forma determinista y deja la pregunta al final, listo para cachear.

Resultado neto en el caso medido: de **10.263 tokens** (salida vieja de `ask --json`) a **3.941 tokens**, y a partir de la segunda pregunta sobre el mismo grafo, el contexto se cobra a ~0,1×.

## Resumen para elegir el nivel

- **Querés el máximo ahorro y la LLM solo necesita el mapa de dependencias** → `--detail minimal`.
- **Caso normal** (la LLM razona sobre el recurso que tocás, con punteros a los vecinos) → `--detail summary` *(default)*.
- **Querés que la LLM tenga todo el contenido sin pedir nada más** → `--detail full`.
- **Vas a hacer varias preguntas sobre el mismo Terraform** → no hacés nada especial: el orden estable (feature 6) ya está activo y el caching se aprovecha solo.
