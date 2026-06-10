# Workflow CRS + LLM

CRS esta pensado como una memoria previa a la conversacion con una LLM.

## Flujo recomendado

1. Indexar el proyecto Terraform.

```powershell
crs init C:\ruta\al\terraform
```

2. Cuando el usuario pregunte por un componente, buscar el nodo.

```powershell
crs search C:\ruta\al\terraform dynamodb
```

3. Generar contexto acotado.

```powershell
crs context C:\ruta\al\terraform modules/data::aws_rds_cluster.this
```

4. Enviar a la LLM solo:

- El JSON de `crs context`.
- Los archivos y rangos indicados por los nodos relacionados, si hace falta editar.
- La pregunta del usuario.

## Pregunta: si cambio A, que afecta

```powershell
crs impact C:\ruta\al\terraform A
```

La salida separa:

- Dependencias directas que conviene revisar antes de cambiar A.
- Componentes aguas abajo que pueden verse afectados.
- Tipo de relacion y evidencia.

## Pregunta: si se cae A, que problematicas puede tener

```powershell
crs failure C:\ruta\al\terraform A
```

La salida combina:

- Relaciones entrantes del grafo.
- Tags de dominio inferidos.
- Riesgos probables.

## Postmortem

```powershell
crs postmortem C:\ruta\al\terraform A --out incidente-A.md
```

El documento generado es un borrador. Debe completarse con evidencia real: metricas, logs, timeline, alertas, cambios recientes y decisiones del equipo.

## Regla para agentes

Antes de leer archivos Terraform completos, ejecutar:

```powershell
crs context <project> <node>
```

Solo si el contexto no alcanza, leer los archivos indicados por los nodos relacionados.
