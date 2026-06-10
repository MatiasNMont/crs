# Política de seguridad

## Versiones soportadas

| Versión | Soporte |
| --- | --- |
| 0.4.x | ✅ |
| < 0.4 | ❌ |

## Reportar una vulnerabilidad

**No abras un issue público** para vulnerabilidades. Usá una de estas vías:

1. **GitHub Security Advisories** (preferido): pestaña *Security* → *Report a vulnerability* en este repositorio.
2. Contacto directo con los mantenedores (ver perfil de la organización).

Incluí: versión afectada, pasos de reproducción, impacto estimado y, si tenés, una propuesta de fix. Respondemos lo antes posible y coordinamos la divulgación responsable.

## Modelo de amenazas

CRS es una herramienta **local de línea de comandos**: no expone servicios de red, no recibe tráfico y no envía datos a ningún lado. Las superficies de ataque relevantes son:

1. **Repositorios Terraform no confiables**: indexar un repo de terceros implica parsear sus `.tf`. El scanner no ejecuta HCL, no sigue symlinks fuera del proyecto y sanitiza los nombres de archivo que genera.
2. **Variables de entorno de integración** (`CRS_CODELOOM_SYNC_COMMAND`, `CRS_CODELOOM_BIN`): definen un comando que CRS ejecuta. Se tokenizan y ejecutan sin shell, pero **configurarlas equivale a ejecutar ese programa**: usá solo binarios confiables.
3. **Salidas para LLM**: el grafo, los prompts y los reportes pueden contener detalles de tu infraestructura. CRS redacta valores literales de atributos sensibles (passwords, tokens, keys), pero la topología (recursos, CIDRs, nombres) sigue presente.

## Protecciones implementadas

- Ejecución de comandos externos sin shell (`shell=False`), con sustitución segura de placeholders y timeout.
- Redacción de secretos literales (`password`, `secret`, `token`, `api_key`, `private_key`, `access_key`, `credential` y `default`/`value` de bloques con nombre sensible) antes de persistir o componer prompts.
- El indexador ignora symlinks y archivos que resuelven fuera de la raíz del proyecto.
- Nombres de archivo generados sanitizados por whitelist, con hash anti-colisión y truncado.
- Reportes HTML autocontenidos, sin CDNs, con escape de todo valor dinámico.

## Recomendaciones para usuarios

- Agregá `.crs/` a tu `.gitignore` si no querés versionar la memoria del grafo (contiene configuración de tu infraestructura, aunque redactada).
- Tratá el contenido de `.tf` de terceros como **datos no confiables** al pasarlo a una LLM: puede contener intentos de prompt injection.
- No uses secretos literales en Terraform: la redacción de CRS es una red de seguridad, no un reemplazo de `variable` + secret managers.
- Si instalás el extra `codeloom`, verificá la procedencia del paquete (o pinealo a una versión/fuente conocida) antes de instalarlo.
