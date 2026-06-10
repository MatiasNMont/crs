# Codex Integration

## Setup

```bash
python -m pip install -e .
crs init .
```

CodeLoom is installed automatically as a required CRS dependency and is used as the default memory backend.

`crs init` generates an `AGENTS.md` block that directs Codex to query CRS graph memory before reading the repository broadly. Run `crs install-agent . --target codex --force` when you need to refresh it explicitly.

Start a new Codex thread after installation. Repository instructions are loaded at thread startup, so an existing thread may not see a newly created or updated `AGENTS.md`.

## Recommended Prompt Flow

```bash
crs ask . "What is affected if I delete the domain DynamoDB tables?" --json
```

Codex should use the selected node, bounded context, affected nodes, risks, and file pointers. It should open additional source only when the graph context does not answer the question.

After Terraform changes, run:

```bash
crs preflight . --max-affected 10
terraform plan
```

CRS provides structural impact; Terraform remains the authority for the execution plan.
