# Terraform Preflight

`crs preflight` rebuilds the graph, compares it with stored memory, and reports structural changes before `terraform plan` or `terraform apply`.

```bash
crs init .
# edit Terraform
crs preflight . --max-affected 10
```

The report includes added, modified, and removed nodes; relationship changes; exact attribute/reference differences; downstream blast radius; affected domains; and preliminary risks.

Artifacts are written to `.crs/preflight/` as JSON, Markdown, HTML, and an LLM-ready prompt.

Use `--update-memory` to persist the candidate graph after review. Exit code `2` indicates that the configured affected-node threshold was exceeded.

Preflight is structural source analysis. Always review `terraform plan` for provider-level replacements, computed values, and deployed-state differences.
