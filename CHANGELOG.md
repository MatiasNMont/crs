# Changelog

All notable changes to CRS are documented here.

## Unreleased

### Security

- Redact literal `default`/`value` assignments in any block carrying Terraform's `sensitive = true` marker, even when the block name does not look sensitive (e.g. `variable "connection_string"`).
- A malformed or hostile `.tf` file no longer aborts the whole indexing run; the file is skipped with a warning on stderr.
- `crs install-agent` rules now instruct agents to treat `config`/`evidence` content extracted from repository files as untrusted data, never as instructions (prompt-injection hardening).
- Documented the dependency-confusion risk of the unpinned optional `codeloom` dependency in `pyproject.toml`.

### Changed

- Standardized the CLI, generated reports, agent instructions, code comments, and primary documentation in English.
- Added a complete Spanish documentation edition under `docs/es/`.
- Added `README.es.md` and language navigation from the main README.

## 0.4.0

- Added context detail levels: `minimal`, `summary`, and `full`.
- Added compact `crs ask --json` payloads and `--full-payload` for debugging.
- Added deterministic output ordering to improve prompt caching.
- Added command-injection protections for external CodeLoom synchronization.
- Added secret redaction, project-root containment, and safer generated filenames.
- Improved HCL scanning for UTF-8 BOM and invalid encodings.

## 0.3.0

- Added Terraform preflight impact reports.
- Added Chaos Engineering plans and token benchmarks.
- Added interactive graph HTML reports.
- Added local Codex and Claude Code integration.

## 0.1.0

- Initial Terraform indexing, graph persistence, search, impact, failure, context, ask, summary, and postmortem commands.
