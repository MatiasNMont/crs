# Contribuir a CRS

¡Gracias por tu interés en mejorar CRS! Este documento explica cómo proponer cambios.

## Cómo empezar

```bash
git clone https://github.com/matiasnmont/crs.git
cd crs
python -m pip install -e .
crs --help
```

Requisitos: Python 3.10+. El core no tiene dependencias obligatorias; mantenelo así salvo justificación fuerte.

## Flujo de trabajo

1. Abrí un **issue** describiendo el bug o la propuesta antes de invertir tiempo en un PR grande.
2. Creá una rama desde `main`: `feature/<nombre>` o `fix/<nombre>`.
3. Hacé cambios chicos y enfocados; un PR = un tema.
4. Verificá que todo compile y que el smoke test pase (ver abajo).
5. Abrí el PR explicando el problema, la solución y cómo lo probaste.

## Smoke test manual

Mientras no haya suite de tests automatizada, validá tus cambios contra un proyecto Terraform de prueba:

```bash
crs init <proyecto-terraform>
crs summary <proyecto-terraform>
crs ask <proyecto-terraform> "que pasa si se cae <componente>?"
crs preflight <proyecto-terraform>
crs benchmark-tokens <proyecto-terraform> "impacto de cambiar <componente>"
crs graph-html <proyecto-terraform>
```

Y compilación rápida:

```bash
python -m py_compile src/crs/*.py
```

Si tu cambio toca el scanner HCL o el indexer, probá con: módulos anidados, `depends_on`, outputs, variables con `default`, comentarios `#`/`//` y strings con llaves.

## Estilo de código

- Python con type hints (`from __future__ import annotations`).
- Mantener las dependencias acotadas; CodeLoom es una dependencia requerida de la integracion principal.
- Mensajes de usuario, identificadores, código y documentación principal en inglés. La documentación española se mantiene bajo `docs/es/`.
- Los reportes HTML deben seguir siendo **autocontenidos** (sin CDNs ni llamadas de red) y todo valor dinámico debe pasar por el escapador HTML.

## Reglas de seguridad para PRs

Estas son invariantes del proyecto; los PRs que las rompan no se mergean:

- **Nada de `shell=True`** ni interpolación de rutas en comandos.
- **Nada de llamadas de red** en el core: CRS es 100 % local.
- Todo archivo que se escriba con nombre derivado de datos del usuario debe sanitizarse (whitelist + truncado).
- La redacción de secretos en la indexación no se debe debilitar; si agregás una fuente nueva de contexto para LLM, redactala también.
- El indexador no debe seguir symlinks ni leer fuera de la raíz del proyecto.

Si encontrás una vulnerabilidad, **no abras un issue público**: seguí el proceso de [SECURITY.md](SECURITY.md).

## Ideas de contribución

- Suite de tests con `pytest` (el proyecto hoy se valida con smoke tests).
- Parser HCL formal opcional (Tree-sitter, `hcl2json`).
- Nuevos dominios y escenarios de chaos (`DOMAIN_KEYWORDS`, `SCENARIOS`).
- Integración con `terraform plan -json` en el preflight.
- Soporte para otros IaC.

## Código de conducta

Sé respetuoso y constructivo. Los desacuerdos técnicos se resuelven con argumentos y evidencia, no con agresiones.
