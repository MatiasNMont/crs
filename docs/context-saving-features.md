# Context-Saving Features

CRS reduces LLM context in three complementary ways.

## Detail Levels

- `minimal`: node identity, type, location, and tags; no HCL configuration.
- `summary`: full configuration for the focus node only. This is the default.
- `full`: full configuration for every node in the bounded subgraph.

## Payload Pruning

`crs ask --json` omits internal agent metadata, rendered duplicate text, and repeated node fields. Use `--full-payload` for debugging.

## Stable Ordering

Nodes, relationships, and JSON keys are sorted deterministically. Benchmark prompts place stable graph context before the variable user question, improving compatibility with provider prompt caching.

All context nodes include file and line pointers, allowing agents to load additional configuration only when needed.

## Measured Insurance Example

For `aws-reference-example` and the question "What is affected if I delete the domain DynamoDB tables?":

| Detail | Estimated tokens | Reduction vs raw |
| --- | ---: | ---: |
| Raw repository | 7,481 | - |
| `minimal` | 1,892 | 74.71% |
| `summary` | 2,063 | 72.42% |
| `full` | 3,774 | 49.55% |
