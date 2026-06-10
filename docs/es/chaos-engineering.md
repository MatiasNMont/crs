# Chaos Engineering con CRS

CRS puede generar planes de Chaos Engineering a partir del grafo de impacto.

La idea es responder:

```text
Si inyecto una falla en este componente, que impactaria?
Que escenarios deberia probar?
Que senales, guardrails y condiciones de aborto necesito?
```

## Generar plan

```powershell
crs chaos <ruta-del-proyecto> aws_rds_cluster.this
```

Por defecto genera 3 escenarios, seleccionados segun los tags del componente.

Salida:

```text
.crs/
  chaos/
    <component>.chaos.json
    <component>.chaos.md
    <component>.chaos.html
```

## Elegir cantidad de escenarios

```powershell
crs chaos <ruta-del-proyecto> aws_rds_cluster.this --count 5
```

## Elegir profundidad de impacto

```powershell
crs chaos <ruta-del-proyecto> aws_rds_cluster.this --depth 4
```

## Elegir escenarios especificos

```powershell
crs chaos <ruta-del-proyecto> aws_rds_cluster.this --scenario data-outage --scenario data-latency
```

## Escenarios disponibles

- `data-outage`
- `data-latency`
- `network-packet-loss`
- `compute-pod-kill`
- `messaging-backlog`
- `security-secret-deny`


## Que contiene el plan

Cada experimento incluye:

- componente objetivo
- parametros del caos
- hipotesis
- senales a observar
- guardrails
- condiciones de aborto
- dependencias directas
- nodos afectados aguas abajo
- reporte Markdown
- vista HTML

## Ejemplo DynamoDB en la plataforma de seguros

```powershell
crs chaos <ruta-del-proyecto> "root::aws_dynamodb_table.domain" --count 3
```

CRS debe resolver:

```text
modules/data::aws_rds_cluster.this
```

Y priorizar escenarios de datos:

- indisponibilidad de persistencia
- latencia en base de datos/cache
- degradacion funcional bancaria si aplica por relaciones

## Uso recomendado con Codex/Claude

Primero generar el plan:

```powershell
crs chaos . "root::aws_dynamodb_table.domain" --count 3
```

Luego pedir al agente:

```text
Lee .crs/chaos/<archivo>.chaos.json y ayudame a convertirlo en experimentos seguros para staging.
```

El agente debe usar el plan CRS y abrir solo los archivos indicados por el blast radius.
