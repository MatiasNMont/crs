# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.1.0/). Versionado [SemVer](https://semver.org/lang/es/).

## [Unreleased]

### Seguridad

- **Inyección de comandos**: `CRS_CODELOOM_SYNC_COMMAND` ya no se ejecuta con shell ni se interpola con `.format()`. El template se tokeniza, los placeholders (`{project}`, `{graph}`, `{codeloom_dir}`) se sustituyen por token y el subproceso corre con `shell=False` y timeout de 600 s.
- **Redacción de secretos**: los valores literales de atributos sensibles (`password`, `secret`, `token`, `api_key`, `private_key`, `access_key`, `credential`, y `default`/`value` de bloques con nombre sensible) se reemplazan por `***REDACTED***` al indexar y en el prompt raw del benchmark. Las referencias `var.x` se conservan.
- **Contención de archivos**: el indexador y el benchmark ignoran symlinks y archivos que resuelvan fuera de la raíz del proyecto.
- **Sanitización de nombres de archivo**: el slug de los planes de chaos usa whitelist y truncado (antes permitía `:` y otros caracteres problemáticos en NTFS); los archivos por nodo agregan sufijo hash SHA-256 para evitar colisiones.

### Corregido

- El scanner HCL tolera BOM UTF-8 (antes se perdía el primer bloque del archivo) y archivos con encoding inválido ya no interrumpen `crs init`.

### Agregado

- **Ahorro de contexto** (ver [features-ahorro-contexto.md](features-ahorro-contexto.md)):
  - Niveles de detalle `--detail {minimal,summary,full}` en `context`, `ask`/`agent` y `benchmark-tokens`: controlan cuánta config HCL viaja a la LLM (default `summary` = config solo del nodo foco).
  - `crs ask --json` emite un payload podado por defecto; `--full-payload` vuelve al payload completo. En el caso actual de eliminar las tablas DynamoDB, `summary` reduce el contexto de 7.481 a 2.063 tokens estimados (72,42 %).
  - Salida JSON determinista (claves y nodos ordenados) y pregunta al final del prompt en el benchmark, para habilitar prompt caching del proveedor (~0,1× en lecturas de prefijo cacheado).
- `crs ask` ahora detecta intención de **eliminación** (`eliminar`, `borrar`, `quitar`, `destruir`, `delete`, `remove`, `destroy`, `drop`) y la trata como análisis de impacto; antes estas preguntas caían en modo `context`.
- Guia de benchmark con el caso de eliminar las tablas DynamoDB de la plataforma de seguros ([benchmark-eliminacion-dynamodb-seguros.md](benchmark-eliminacion-dynamodb-seguros.md)).
- Documentación pública: README renovado, referencia CLI completa, arquitectura interna, `CONTRIBUTING.md`, `SECURITY.md` y este changelog.

## [0.4.0]

### Agregado

- `crs preflight`: diff de grafo y blast radius antes de `terraform apply`, con umbral `--max-affected` (exit code `2`), reportes JSON/MD/HTML y prompt listo para LLM.
- `crs chaos`: planes de Chaos Engineering por dominio con hipótesis, señales, guardrails y condiciones de aborto.
- `crs benchmark-tokens`: medición de ahorro de tokens entre contexto raw y contexto CRS.
- `crs graph-html`: visualización interactiva del grafo en HTML autocontenido.
- `crs install-agent`: reglas locales para Codex (`AGENTS.md`) y Claude Code (`CLAUDE.md`) sin MCP.
- Backend CodeLoom como default, con export `.crs/codeloom/` y sincronización opcional vía librería o comando externo.

## [0.3.0] y anteriores

- Indexación de Terraform (`crs init`), grafo de relaciones, consultas `impact`/`failure`/`context`, agente `crs ask`, `summary`, `search` y `postmortem`.
