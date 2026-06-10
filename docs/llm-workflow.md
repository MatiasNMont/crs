# LLM Workflow

CRS follows a graph-first, files-second workflow.

1. Run `crs ask . "<question>" --json`.
2. Use `decision`, `context`, and `result` as the initial evidence.
3. Open only files and line ranges listed in `context.nodes`.
4. Request additional files only when the bounded context is insufficient.
5. Validate proposed infrastructure changes with `terraform plan`.

This workflow reduces repository reads, context size, latency, and repeated token usage. CRS output describes structural source relationships, not deployed runtime state.
