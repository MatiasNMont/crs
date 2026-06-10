# Agentes CRS

Desde la version `0.2.0`, CRS incluye una capa de agentes para responder preguntas en lenguaje natural usando la memoria del grafo. Desde `0.4.0`, esos agentes usan `codeloom` como backend default.

## Agentes incluidos

### context-agent

Se ejecuta siempre antes de responder una pregunta.

Accion equivalente:

```powershell
crs context <project> <node>
```

Objetivo:

- Reducir el contexto para la LLM.
- Pasar solo nodos relacionados.
- Evitar leer todo el repositorio con `grep`.

### impact-agent

Se ejecuta cuando la pregunta parece hablar de cambios.

Ejemplos:

- "Que pasa si elimino las tablas DynamoDB?"
- "Si modifico EKS, que afecta?"
- "What happens if Redis changes?"

Accion equivalente:

```powershell
crs impact <project> <node>
```

### failure-agent

Se ejecuta cuando la pregunta parece hablar de caidas, fallas o incidentes.

Ejemplos:

- "Si falla DynamoDB, que problematica puede tener?"
- "Que pasa si falla EKS?"
- "What happens if Redis is down?"

Accion equivalente:

```powershell
crs failure <project> <node>
```

## Comando principal

```powershell
crs ask <project> "<pregunta>"
```

CodeLoom es el backend default:

```powershell
crs ask <project> "<pregunta>"
```

Alias:

```powershell
crs agent <project> "<pregunta>"
```

## Ejemplo: impacto

```powershell
crs ask <ruta-del-proyecto> "What is affected if I delete the domain DynamoDB tables?"
```

CRS hace:

1. Detecta intencion `impact`.
2. Detecta nodo `modules/data::aws_rds_cluster.this`.
3. Ejecuta `context-agent`.
4. Ejecuta `impact-agent`.
5. Devuelve impacto y dependencias.

## Ejemplo: falla

```powershell
crs ask <ruta-del-proyecto> "What happens if the domain DynamoDB tables fail?"
```

CRS hace:

1. Detecta intencion `failure`.
2. Detecta nodo `modules/data::aws_rds_cluster.this`.
3. Ejecuta `context-agent`.
4. Ejecuta `failure-agent`.
5. Devuelve riesgos y componentes afectados.

## JSON para integrar con una LLM

```powershell
crs ask <project> "What is affected if I delete the domain DynamoDB tables?" --json
```

La salida incluye:

- `decision`: intencion, nodo y confianza.
- `agents`: agentes ejecutados.
- `context`: nodos y relaciones que deberian enviarse a la LLM.
- `result`: resultado estructurado de `impact`, `failure` o `context`.
- `rendered`: respuesta humana.

## Reglas de comportamiento

- Si detecta cambio, ejecuta `impact`.
- Si detecta falla/caida, ejecuta `failure`.
- Si no detecta ninguna de esas intenciones, ejecuta solo `context`.
- Siempre ejecuta `context-agent` primero.
- Si el componente es ambiguo o no se encuentra, pide usar `crs search`.

## Limitaciones

La deteccion es heuristica y local, sin llamar a una LLM. Es intencional: CRS debe poder funcionar offline. Para mayor precision se puede agregar un clasificador configurable o alias manuales por dominio.
