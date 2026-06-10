# Local Agent Installation

`crs init` automatically installs repository-local instructions for Codex and Claude Code. You can also update them explicitly:

```bash
crs install-agent .
```

Targets can be selected explicitly:

```bash
crs install-agent . --target codex
crs install-agent . --target claude
crs install-agent . --target cursor
crs install-agent . --target windsurf
```

The default target is `base`, which expands to Codex and Claude. `--target` is repeatable, and `--target all` installs every supported integration.

CRS writes managed blocks to `AGENTS.md` and/or `CLAUDE.md`, Cursor rules to `.cursor/rules/crs.mdc`, Windsurf rules to `.windsurf/rules/crs.md`, and shared helper scripts under `.crs/agents/`. Re-running the command updates managed blocks without duplicating them.

No MCP server or remote service is required. The installed rules tell the agent to call `crs ask` before broad repository exploration.

## Session Reload Requirement

Codex and Claude Code load repository instructions when a session starts. After running `crs install-agent`, start a new session in the target repository. An already-open session may continue using the instruction set it loaded before `AGENTS.md` or `CLAUDE.md` was updated.

## Verification

Verify the integration in the target Terraform repository:

```powershell
crs --help
Test-Path AGENTS.md
Test-Path .crs/graph.json
```

If graph memory is missing, run `crs init .`. The target repository, not the CRS source repository, must contain the generated `AGENTS.md`.

## Disable CRS for Comparisons

Remove all CRS-managed agent rules while keeping graph memory:

```bash
crs disable .
```

For a completely clean comparison without agent rules, graph memory, or generated reports:

```bash
crs disable . --remove-memory
```

The command preserves any non-CRS content in `AGENTS.md` and `CLAUDE.md`. Start a new agent session after disabling CRS.
