# Insurance DynamoDB Deletion Benchmark

This benchmark uses `aws-reference-example` and the question:

> What is affected if I delete the domain DynamoDB tables?

## Reference Project

- Domain: serverless insurance platform
- Terraform files: 11
- CRS graph: 96 nodes and 151 relationships
- Focus node: `root::aws_dynamodb_table.domain`
- Relevant subgraph: 9 nodes and 9 relationships
- Downstream affected nodes: 11

## Run

```powershell
cd aws-reference-example
crs init .
crs benchmark-tokens . "What is affected if I delete the domain DynamoDB tables?" --detail summary
```

## Measured Result

| Mode | Estimated tokens | Reduction | Raw/CRS ratio |
| --- | ---: | ---: | ---: |
| Raw repository | 7,481 | - | - |
| CRS `minimal` | 1,892 | 74.71% | 3.95x |
| CRS `summary` | 2,063 | 72.42% | 3.63x |
| CRS `full` | 3,774 | 49.55% | 1.98x |

The default `summary` mode saves approximately 5,418 input tokens while retaining the full DynamoDB resource configuration and structural pointers for neighboring nodes.

## What CRS Identified

CRS selected `aws_dynamodb_table.domain`, classified it under data and security, identified KMS as a direct dependency, and traced impact through Lambda, IAM, API Gateway, and Step Functions.

## Fair Agent Comparison

CRS-enabled repository:

```powershell
crs init .
```

Control repository:

```powershell
crs disable . --remove-memory
```

Start clean agent sessions, use the same model and reasoning level, ask the exact same question, and record input/output tokens, tool calls, wall-clock time, answer quality, and missed dependencies.

The built-in estimate uses `ceil(characters / 4)`. Use provider-reported token usage for billing-quality results.
