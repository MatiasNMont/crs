# CLI Reference

All commands accept a Terraform project directory. CodeLoom is installed with CRS and is the default backend. Backend-aware commands support `--backend json|codeloom`.

## Core Commands

| Command | Description |
| --- | --- |
| `crs init <project>` | Scan Terraform, persist graph memory, and install Codex/Claude rules. |
| `crs summary <project>` | Print graph counts by kind and domain. |
| `crs search <project> <term>` | Find nodes by ID, file, or domain. |
| `crs impact <project> <node>` | Show direct dependencies and downstream impact. |
| `crs failure <project> <node>` | Show failure propagation and inferred risks. |
| `crs context <project> <node>` | Emit bounded JSON context. |
| `crs ask <project> <question>` | Detect intent and execute a graph query. |
| `crs agent ...` | Alias for `crs ask`. |

## Reports and Automation

| Command | Description |
| --- | --- |
| `crs postmortem` | Generate a Markdown postmortem draft. |
| `crs graph-html` | Generate a self-contained interactive graph. |
| `crs preflight` | Compare current source with stored graph memory. |
| `crs chaos` | Generate JSON, Markdown, and HTML chaos plans. |
| `crs benchmark-tokens` | Compare raw and CRS context size. |
| `crs install-agent` | Install local rules for Codex, Claude, Cursor, and Windsurf. |
| `crs disable` | Remove agent rules; optionally remove graph memory for no-CRS tests. |
| `crs backend-status` | Show backend and CodeLoom status. |

## Common Options

- `--depth N`: relationship traversal depth.
- `--json`: structured output.
- `--detail minimal|summary|full`: context configuration detail.
- `--strict-backend`: fail when external synchronization fails.
- `--full-payload`: include internal agent metadata.

`crs install-agent --target` accepts `base`, `codex`, `claude`, `cursor`, `windsurf`, or `all`. The option is repeatable. Without `--target`, `base` installs Codex and Claude.

`crs disable <project>` removes CRS-managed agent instructions and helper scripts while preserving unrelated `AGENTS.md`/`CLAUDE.md` content and graph memory. Add `--remove-memory` to also delete `.crs/` for a clean no-CRS benchmark.

Exit code `0` means success, `1` means an error, and preflight returns `2` when `--max-affected` is exceeded.
