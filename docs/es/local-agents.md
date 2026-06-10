# Agentes locales CRS sin MCP

`crs init` instala automaticamente reglas locales para que Codex y Claude Code usen la memoria CRS/CodeLoom sin MCP ni servicios remotos.

## Instalar agentes en un repo

```powershell
crs install-agent <ruta-del-proyecto>
```

Esto crea o actualiza:

```text
AGENTS.md
CLAUDE.md
.crs/
  agents/
    crs-agent-prompt.md
    ask-crs.ps1
    ask-crs.sh
```

Para solo Codex:

```powershell
crs install-agent <ruta-del-proyecto> --target codex
```

Para solo Claude:

```powershell
crs install-agent <ruta-del-proyecto> --target claude
```

Agentes opcionales:

```powershell
crs install-agent <ruta-del-proyecto> --target cursor
crs install-agent <ruta-del-proyecto> --target windsurf
crs install-agent <ruta-del-proyecto> --target cursor --target windsurf
```

El target por defecto es `base` (Codex + Claude). `--target all` instala todas las integraciones soportadas.

## Desactivar CRS para una comparacion

```powershell
crs disable <ruta-del-proyecto>
```

Esto elimina las reglas de agentes pero conserva la memoria. Para una prueba completamente limpia:

```powershell
crs disable <ruta-del-proyecto> --remove-memory
```

El comando conserva contenido ajeno a CRS en `AGENTS.md` y `CLAUDE.md`. Inicia una sesion nueva del agente despues de desactivarlo.

## Como funciona

Los archivos `AGENTS.md` y `CLAUDE.md` contienen reglas persistentes:

```text
Si existe .crs/graph.json, antes de responder preguntas de arquitectura, impacto, dependencias, fallas o incidentes, ejecutar:

crs ask . "<pregunta del usuario>" --json
```

Esto hace que el agente use:

- `context-agent`
- `impact-agent`
- `failure-agent`
- memoria local `.crs/graph.json`
- export local `.crs/codeloom/`
- grafo nativo `.crs/codeloom-native/`

## No usa MCP

Este flujo no requiere:

- MCP
- servidores locales
- conexiones a internet
- configuraciones globales de Claude/Codex

Todo queda dentro del repo.

## Uso esperado

Usuario pregunta:

```text
Que pasa si cambio este componente?
```

Codex/Claude lee `AGENTS.md` o `CLAUDE.md` y debe ejecutar:

```powershell
crs ask . "Que pasa si cambio este componente?" --json
```

Luego responde usando `decision`, `context` y `result`.

## Helper local

Tambien queda disponible:

```powershell
.\.crs\agents\ask-crs.ps1 "What is affected if I delete the domain DynamoDB tables?"
```

En Unix:

```sh
./.crs/agents/ask-crs.sh "What is affected if I delete the domain DynamoDB tables?"
```

## Regla importante

Si CRS no puede resolver el componente, entonces el agente puede usar:

```powershell
crs search . "<termino>"
```

Solo despues de eso deberia abrir archivos.
