# Preflight antes de Terraform

CRS puede validar impacto antes de que Terraform ejecute cambios.

El flujo es:

```text
cambios en .tf
  â†“
crs preflight .
  â†“
regenera grafo actual
  â†“
compara contra .crs/graph.json anterior
  â†“
calcula blast radius de nodos agregados/modificados/eliminados
  â†“
genera reporte
  â†“
reciÃ©n despues terraform plan/apply
```

## Comando basico

```powershell
crs preflight <ruta-del-proyecto>
```

Genera:

```text
.crs/
  preflight/
    latest.json
    latest.md
    latest.html
    latest.prompt.md
    preflight-<timestamp>.json
    preflight-<timestamp>.md
    preflight-<timestamp>.html
    preflight-<timestamp>.prompt.md
  history/
    graph-<timestamp>.json
    preflight-candidate-<timestamp>.json
```

## Actualizar memoria si el preflight pasa

```powershell
crs preflight <ruta-del-proyecto> --update-memory
```

Esto guarda el nuevo grafo como memoria CRS.

## Bloquear por blast radius

Fallar si algun nodo cambiado afecta mas de 5 nodos:

```powershell
crs preflight <ruta-del-proyecto> --max-affected 5
```

Si se supera el umbral, CRS devuelve exit code `2`.

## Flujo recomendado local

Antes de Terraform:

```powershell
crs preflight . --max-affected 5
terraform plan
terraform apply
```

Si queres actualizar memoria despues de revisar:

```powershell
crs preflight . --update-memory
```

## Flujo recomendado CI/CD

```powershell
crs init .
crs preflight . --max-affected 10
terraform plan
```

En un pipeline real, `crs init .` deberia ejecutarse al crear baseline. Luego `crs preflight` compara contra esa memoria versionada o persistida.

## Que detecta

- recursos agregados
- recursos modificados
- recursos eliminados
- relaciones agregadas
- relaciones eliminadas
- dependencias directas
- afectados aguas abajo
- max blast radius por nodo
- dominios afectados: seguridad, datos, red, compute, mensajeria
- riesgos sugeridos por dominio
- prompt listo para pegar en Codex/Claude
- diff exacto por nodo: atributos agregados, removidos y modificados
- diff unificado de la configuracion del recurso

## Historial de grafos

CRS conserva historial en:

```powershell
.crs/history/
```

Tipos de snapshot:

- `graph-<timestamp>.json`: grafo persistido por `crs init` o `crs preflight --update-memory`.
- `preflight-candidate-<timestamp>.json`: grafo candidato generado por `crs preflight` antes de aplicar cambios.

Esto permite comparar:

- memoria anterior vs grafo candidato
- grafo candidato vs memoria nueva
- ejecuciones preflight anteriores

## Prompt para LLM

Despues de `crs preflight`, CRS genera:

```powershell
.crs/preflight/latest.prompt.md
```

Ese archivo esta pensado para pegarlo en Codex o Claude y pedir:

```text
Analiza el impacto del cambio a nivel recursos, seguridad, datos, red, compute, mensajeria y negocio.
```

El prompt incluye:

- resumen de cambios
- nodos modificados/agregados/eliminados
- blast radius
- diff exacto de atributos cambiados
- dominios afectados
- dependencias directas
- nodos aguas abajo
- instrucciones para no hacer grep completo
- formato de respuesta esperado

## Que no hace

`crs preflight` no ejecuta Terraform. Es un guard de grafo previo a Terraform.

Para combinarlo con Terraform, usalo como paso anterior a:

```powershell
terraform plan
terraform apply
```
