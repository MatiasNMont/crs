# CRS - Code Relationship System

CRS is a local graph-memory and analysis tool for Terraform repositories. It scans infrastructure code, builds a dependency graph, and gives coding agents focused architectural context before they search through the full repository.

CRS is designed for impact analysis, failure reasoning, Terraform change validation, compact LLM context, and repeatable comparisons between agent workflows with and without graph memory.

> Current status: **Beta**, version **0.5.0**. Terraform/HCL is supported today. The scanner is intentionally lightweight and heuristic.

## Why CRS

Infrastructure questions often force an agent to inspect many files before it can identify the relevant resources and dependencies. CRS indexes those relationships once and stores them locally under `.crs/`.

Agents can then ask questions such as:

```text
What is affected if I delete the domain DynamoDB tables?
What can fail if this component becomes unavailable?
Which resources depend on this KMS key?
```

Instead of loading the entire repository, the agent receives a bounded subgraph with node IDs, relationships, risks, and source locations.

## Features

- **Terraform graph indexing**: detects resources, data sources, modules, variables, outputs, providers, references, and explicit dependencies.
- **Impact analysis**: traces direct dependencies and downstream components affected by a change.
- **Failure analysis**: models failure propagation and adds domain-specific risk guidance.
- **Natural-language queries**: `crs ask` detects the requested operation and resolves the relevant graph node.
- **Agent command alias**: `crs agent` provides the same workflow as `crs ask`.
- **Compact LLM context**: exports `minimal`, `summary`, or `full` graph context with precise file and line references.
- **Automatic agent integration**: `crs init` installs CRS-first instructions for Codex and Claude Code.
- **Optional agent integrations**: repository rules can also be installed for Cursor and Windsurf.
- **CodeLoom integration**: CodeLoom is installed with CRS and used as the default memory integration.
- **Terraform preflight checks**: compares current source with stored graph memory and calculates the blast radius of changes.
- **Token benchmarking**: estimates the context reduction achieved by CRS compared with reading all Terraform files.
- **Interactive visualization**: generates a self-contained HTML dependency graph.
- **Chaos experiment generation**: creates graph-aware experiment plans in JSON, Markdown, and HTML.
- **Postmortem drafts**: generates a starting document from graph-based failure analysis.
- **Local operation**: graph memory and generated reports remain inside the target repository.
- **Secret redaction**: sensitive literal values are redacted before they are persisted in graph memory.
- **Clean control testing**: `crs disable` removes managed agent rules, and `--remove-memory` also removes generated CRS data.

## Installation

CRS requires Python 3.10 or newer.

```bash
git clone https://github.com/matiasnmont/crs.git
cd crs
python -m pip install -e .
```

This installs the `crs` command and the compatible CodeLoom dependency.

Verify the installation:

```bash
crs --help
```

## Quick Start

Initialize CRS inside a Terraform repository:

```bash
crs init ./aws-reference-example
```

Initialization performs three operations:

1. Scans the Terraform source and builds graph memory under `.crs/`.
2. Synchronizes the configured memory backend, with CodeLoom as the default integration.
3. Installs managed repository instructions for Codex and Claude Code.

Start a new agent session after initialization so the generated `AGENTS.md` or `CLAUDE.md` instructions are loaded.

Explore the graph:

```bash
crs summary ./aws-reference-example
crs search ./aws-reference-example dynamodb
```

Ask an architecture question:

```bash
crs ask ./aws-reference-example \
  "What is affected if I delete the domain DynamoDB tables?" \
  --json
```

Run the same query with a canonical node ID:

```bash
crs impact ./aws-reference-example \
  root::aws_dynamodb_table.domain \
  --depth 3
```

## Agent Integrations

Codex and Claude Code are installed automatically by `crs init`.

```bash
crs install-agent ./aws-reference-example
```

Additional integrations can be installed explicitly:

```bash
crs install-agent ./aws-reference-example --target cursor
crs install-agent ./aws-reference-example --target windsurf
crs install-agent ./aws-reference-example --target all
```

Supported targets are `base`, `codex`, `claude`, `cursor`, `windsurf`, and `all`. The default `base` target installs Codex and Claude Code.

CRS manages only its own marked sections and preserves unrelated content in existing agent instruction files.

## Main Commands

| Command | Purpose |
| --- | --- |
| `crs init <project>` | Index Terraform, persist graph memory, and install base agent rules. |
| `crs summary <project>` | Show graph statistics by node kind and domain. |
| `crs search <project> <term>` | Find nodes by name, canonical ID, file, or domain. |
| `crs impact <project> <node>` | Trace dependencies and downstream change impact. |
| `crs failure <project> <node>` | Trace failure propagation and inferred risks. |
| `crs context <project> <node>` | Produce bounded JSON context for an LLM. |
| `crs ask <project> <question>` | Resolve a natural-language question and run a graph query. |
| `crs agent ...` | Alias for `crs ask`. |
| `crs preflight <project>` | Compare current Terraform with stored graph memory. |
| `crs graph-html <project>` | Generate an interactive HTML graph. |
| `crs chaos <project> <node>` | Generate a graph-aware chaos experiment plan. |
| `crs postmortem <project> <node>` | Generate a Markdown postmortem draft. |
| `crs benchmark-tokens <project> <question>` | Compare raw repository and CRS context size. |
| `crs backend-status <project>` | Display JSON and CodeLoom backend status. |
| `crs install-agent <project>` | Install or update repository-local agent instructions. |
| `crs disable <project>` | Remove CRS-managed agent instructions and helper scripts. |

Use `--json` for structured output, `--depth N` to control graph traversal, and `--detail minimal|summary|full` to control context size.

## Terraform Preflight

After changing Terraform source, CRS can compare the new graph with the stored snapshot:

```bash
crs preflight ./aws-reference-example --max-affected 10
terraform plan
```

Preflight returns exit code `2` when the affected-node threshold is exceeded, making it suitable for CI gates.

CRS analyzes structural source relationships. It does not replace `terraform plan`, provider validation, or deployed-state inspection.

## Reference Benchmark

The included `aws-reference-example` models a serverless insurance platform using Cognito, CloudFront, S3, WAF, API Gateway, Lambda, Step Functions, DynamoDB, EventBridge, SQS, SNS, KMS, Secrets Manager, CloudWatch, and X-Ray.

Measured graph:

- 11 Terraform files
- 96 CRS nodes
- 151 relationships
- 11 downstream nodes affected by removal of the domain DynamoDB tables

Measured context estimate:

| Context mode | Estimated tokens | Reduction vs. raw repository |
| --- | ---: | ---: |
| Raw Terraform repository | 7,481 | - |
| CRS `minimal` | 1,892 | 74.71% |
| CRS `summary` | 2,063 | 72.42% |
| CRS `full` | 3,774 | 49.55% |

The built-in benchmark estimates tokens as `ceil(characters / 4)`. Provider-reported usage should be used for billing-grade measurements.

## Disable CRS

Remove managed agent instructions while preserving graph memory:

```bash
crs disable ./aws-reference-example
```

Remove agent instructions, graph memory, helper scripts, and generated reports for a clean control test:

```bash
crs disable ./aws-reference-example --remove-memory
```

Start a new agent session after disabling CRS so the comparison does not reuse previously loaded repository instructions.

## Architecture and Security

CRS uses a lightweight HCL scanner, graph indexer, bounded breadth-first queries, JSON persistence, and CodeLoom synchronization. It never executes Terraform or HCL expressions.

The indexer ignores files that resolve outside the project root and redacts sensitive literal attributes such as passwords, tokens, secrets, private keys, and credentials. Generated HTML content is escaped. Configured external synchronization commands run without a shell.

The `.crs/` directory can still reveal infrastructure topology, resource names, paths, and configuration metadata. Add it to `.gitignore` when that information should not be committed.

## Current Limitations

- Terraform/HCL is the only supported infrastructure format.
- The HCL scanner is heuristic rather than a complete Terraform parser.
- Complex dynamic blocks, deeply nested expressions, or advanced `for_each` patterns may produce incomplete relationships.
- Natural-language intent and component resolution are heuristic.
- CRS analyzes source structure, not deployed Terraform state.
- Agent rules are loaded when an agent session starts; an existing session may not see newly installed instructions.

## Documentation

English:

- [Usage guide](docs/usage-guide.md)
- [CLI reference](docs/cli-reference.md)
- [Agent behavior](docs/agents.md)
- [Local agent integration](docs/local-agents.md)
- [Codex integration](docs/codex-integration.md)
- [Terraform preflight](docs/terraform-preflight.md)
- [Token benchmark](docs/token-benchmark.md)
- [Insurance platform test case](docs/insurance-dynamodb-test-case.md)
- [Insurance platform benchmark](docs/insurance-dynamodb-benchmark.md)

Spanish:

- [Spanish documentation index](docs/es/README.md)
- [Insurance platform test case](docs/es/caso-prueba-dynamodb-seguros.md)
- [Insurance platform benchmark](docs/es/benchmark-eliminacion-dynamodb-seguros.md)

## Project Status

CRS is currently a beta project. The core indexing, graph queries, local agent integrations, CodeLoom backend, reports, token benchmark, and preflight workflow are implemented and covered by the repository smoke test.

The next development areas include formal HCL parsing, Terraform plan JSON integration, additional infrastructure-as-code formats, and richer semantic search.

## Contributing

Contributions, bug reports, Terraform fixtures, and reproducible agent comparisons are welcome. Keep changes focused, include verification for behavioral changes, and avoid committing generated `.crs/` memory unless it is an intentional test fixture.

## License

MIT
