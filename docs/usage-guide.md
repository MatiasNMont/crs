# Usage Guide

## Index a Project

```bash
crs init ./aws-reference-example
```

This creates `.crs/graph.json`, per-node records, snapshots, and CodeLoom exports.

It also installs the mandatory CRS-first rules for Codex and Claude Code:

- `AGENTS.md`
- `CLAUDE.md`
- `.crs/agents/` helper scripts

Start a new agent session after initialization so the generated instructions are loaded.

Optional agents can be added later:

```bash
crs install-agent ./infrastructure --target cursor
crs install-agent ./infrastructure --target windsurf
crs install-agent ./infrastructure --target cursor --target windsurf
```

## Discover Components

```bash
crs summary ./aws-reference-example
crs search ./aws-reference-example dynamodb
```

Use the canonical ID returned by `search` for precise queries.

## Analyze Change Impact

```bash
crs impact ./aws-reference-example root::aws_dynamodb_table.domain --depth 3
```

The result includes direct dependencies and downstream affected nodes.

## Analyze Failure Propagation

```bash
crs failure ./aws-reference-example root::aws_dynamodb_table.domain --depth 3
```

The result includes affected components and domain-specific risks.

## Build LLM Context

```bash
crs context ./aws-reference-example root::aws_dynamodb_table.domain --detail summary
crs ask ./aws-reference-example "What is affected if I delete the domain DynamoDB tables?" --json
```

Use `minimal` for topology only, `summary` for full focus-node configuration, and `full` for all subgraph configuration.

## Generate Artifacts

```bash
crs graph-html ./aws-reference-example
crs postmortem ./aws-reference-example root::aws_dynamodb_table.domain --out postmortem.md
crs chaos ./aws-reference-example root::aws_dynamodb_table.domain
crs benchmark-tokens ./aws-reference-example "What is affected if I delete the domain DynamoDB tables?"
```
