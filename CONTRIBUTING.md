# Contributing to CRS

Thank you for helping improve CRS.

## Development Setup

Requirements: Python 3.10 or newer.

```bash
python -m pip install -e .
python -m compileall src
python -m crs --help
```

The core package intentionally has no mandatory runtime dependencies. Keep changes focused and avoid adding dependencies unless they provide clear value.

## Pull Requests

1. Open an issue before investing in a large change.
2. Create a branch from `main`, such as `feature/name` or `fix/name`.
3. Keep each pull request focused on one concern.
4. Add or update tests and documentation when behavior changes.
5. Describe the problem, solution, and verification steps in the pull request.

## Style

- Use English for code, identifiers, CLI messages, generated reports, comments, and primary documentation.
- Keep Spanish documentation under `docs/es/` and update it when public behavior changes.
- Preserve self-contained HTML reports with no CDN or network dependency.
- Escape all dynamic HTML values.
- Prefer small, explicit functions and standard-library solutions.

## Security Rules

- Never use `shell=True` for external commands.
- Sanitize filenames derived from user or repository data.
- Do not weaken secret redaction.
- Do not follow symlinks or read files outside the project root.
- Treat Terraform from untrusted repositories as untrusted input.

Report vulnerabilities privately using [SECURITY.md](SECURITY.md).

## Code of Conduct

Be respectful, constructive, and evidence-driven. Technical disagreement is welcome; personal attacks are not.
