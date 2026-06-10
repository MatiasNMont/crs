# Benchmark de tokens CRS vs lectura completa

CRS puede generar un benchmark para mostrar cuanto contexto se ahorra usando memoria/grafo en vez de mandar todos los `.tf` a una LLM.

## Comando

```powershell
crs benchmark-tokens <ruta-del-proyecto> "What is affected if I delete the domain DynamoDB tables?"
```

Genera:

```text
.crs/
  benchmarks/
    latest.json
    latest.md
    latest.html
    benchmark-<timestamp>.raw-prompt.txt
    benchmark-<timestamp>.crs-prompt.txt
```

## Que compara

### Sin CRS

Simula mandar a la LLM:

- pregunta del usuario
- todos los archivos `.tf`
- instrucciones genericas

Ignora:

- `.git`
- `.crs`
- `.terraform`

### Con CRS

Simula mandar a la LLM:

- pregunta del usuario
- salida compacta derivada de `crs ask --json`
- `decision`
- `context` sin configuraciones completas
- `result` con blast radius y archivos/lÃ­neas

No incluye la configuracion completa de todos los nodos. Esa configuracion se pide despues solo si hace falta.

## Estimacion de tokens

Usa una aproximacion simple:

```text
tokens ~= ceil(caracteres / 4)
```

Es suficiente para presentar comparativas relativas.

## Salida esperada

```text
CRS token benchmark completo
- Sin CRS: 12000 tokens estimados (24 archivos)
- Con CRS: 2500 tokens estimados (17 nodos)
- Ahorro: 9500 tokens
- Reduccion: 79.16%
- Ratio bruto/CRS: 4.8x
```

## Como presentarlo

Usar:

```powershell
start .crs/benchmarks/latest.html
```

O:

```powershell
code .crs/benchmarks/latest.md
```

La presentacion deberia destacar:

- menos tokens
- menos archivos leidos
- contexto mas dirigido
- decision automatica `impact/failure/context`
- menos riesgo de que la LLM razone sobre partes irrelevantes

## Buenas preguntas para comparar

```powershell
crs benchmark-tokens . "What is affected if I delete the domain DynamoDB tables?"
crs benchmark-tokens . "si se cae el modulo data que problemas puede tener?"
crs benchmark-tokens . "que impacto tiene cambiar KMS?"
crs benchmark-tokens . "que pasa si modifico EKS?"
```
