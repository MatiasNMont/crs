# Security Policy

## Reporting a Vulnerability

Do not open a public issue for a suspected vulnerability. Use GitHub Security Advisories or contact the maintainers privately. Include the affected version, reproduction steps, estimated impact, and any proposed fix.

## Security Model

CRS is a local command-line tool. It exposes no network service and sends no data by default. Its relevant attack surfaces are:

1. Untrusted Terraform repositories parsed as text.
2. Optional CodeLoom synchronization commands configured through environment variables.
3. Graph, prompt, and report output shared with an LLM.

## Controls

- HCL is scanned, never executed.
- Symlinks and files resolving outside the project root are ignored.
- Literal values for sensitive attributes are redacted before persistence or prompt generation.
- External synchronization uses tokenized argument lists with `shell=False` and a timeout.
- Generated filenames use allow-list sanitization, truncation, and collision-resistant hashes.
- HTML reports are self-contained and escape dynamic values.

## User Responsibilities

- Keep `.crs/` out of version control when graph topology is sensitive.
- Do not store literal secrets in Terraform.
- Review third-party Terraform before sending any extracted context to an LLM.
- Verify the source and version of optional packages such as CodeLoom.
