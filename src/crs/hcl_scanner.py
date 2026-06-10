from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


BLOCK_RE = re.compile(r'(?m)^\s*(resource|data|module|variable|output|locals)\s*(?:"([^"]+)")?\s*(?:"([^"]+)")?\s*\{')
ATTRIBUTE_RE = re.compile(r'(?m)^\s*([A-Za-z0-9_-]+)\s*=\s*(.+?)\s*$')
SENSITIVE_NAME_RE = re.compile(
    r"(?i)(password|passwd|secret|token|api_?key|private_key|access_key|client_secret|credential)"
)
SENSITIVE_LITERAL_RE = re.compile(
    r'(?im)^(\s*)([A-Za-z0-9_-]*'
    r'(?:password|passwd|secret|token|api_?key|private_key|access_key|client_secret|credential)'
    r'[A-Za-z0-9_-]*)(\s*=\s*)"([^"\n]*)"(.*)$'
)
REDACTED_VALUE = "***REDACTED***"
REFERENCE_RE = re.compile(
    r"\b("
    r"(?:data\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)"
    r"|(?:module\.[A-Za-z0-9_-]+)"
    r"|(?:var\.[A-Za-z0-9_-]+)"
    r"|(?:local\.[A-Za-z0-9_-]+)"
    r"|(?:[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)"
    r")\b"
)


@dataclass
class HclBlock:
    kind: str
    labels: list[str]
    file: Path
    start_line: int
    end_line: int
    body: str
    raw: str

    @property
    def id(self) -> str:
        if self.kind == "resource":
            return ".".join(self.labels)
        if self.kind == "data":
            return "data." + ".".join(self.labels)
        if self.kind == "module":
            return "module." + self.labels[0]
        if self.kind == "variable":
            return "var." + self.labels[0]
        if self.kind == "output":
            return "output." + self.labels[0]
        return f"locals.{self.file.stem}.{self.start_line}"


def strip_comments(text: str) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("//"):
            lines.append("")
        else:
            lines.append(line)
    return "\n".join(lines)


def find_matching_brace(text: str, open_index: int) -> int:
    depth = 0
    in_string = False
    escape = False

    for index in range(open_index, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index

    raise ValueError("HCL block closing brace was not found")


def line_number_at(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def scan_file(path: Path, root: Path) -> list[HclBlock]:
    text = path.read_text(encoding="utf-8", errors="replace").lstrip("﻿")
    blocks: list[HclBlock] = []

    for match in BLOCK_RE.finditer(text):
        open_index = text.find("{", match.start())
        close_index = find_matching_brace(text, open_index)
        raw = text[match.start() : close_index + 1]
        body = text[open_index + 1 : close_index]
        labels = [label for label in [match.group(2), match.group(3)] if label]
        blocks.append(
            HclBlock(
                kind=match.group(1),
                labels=labels,
                file=path.relative_to(root),
                start_line=line_number_at(text, match.start()),
                end_line=line_number_at(text, close_index),
                body=body,
                raw=raw,
            )
        )

    return blocks


def extract_attributes(body: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for match in ATTRIBUTE_RE.finditer(strip_comments(body)):
        key = match.group(1)
        value = match.group(2).strip().rstrip(",")
        if key not in attrs:
            attrs[key] = value
    return attrs


DEFAULT_LITERAL_RE = re.compile(r'(?im)^(\s*)(default|value)(\s*=\s*)"([^"\n]*)"(.*)$')
SENSITIVE_FLAG_RE = re.compile(r"(?im)^\s*sensitive\s*=\s*true\b")


def is_sensitive_key(key: str) -> bool:
    return bool(SENSITIVE_NAME_RE.search(key))


def is_sensitive_block(raw: str, labels: list[str]) -> bool:
    """A block is sensitive when its name matches sensitive keywords
    (e.g. variable "db_password") or when it carries Terraform's own
    `sensitive = true` marker regardless of its name."""
    if labels and is_sensitive_key(".".join(labels)):
        return True
    return bool(SENSITIVE_FLAG_RE.search(raw))


def redact_block(raw: str, labels: list[str]) -> str:
    """Redact the complete block; when the block is sensitive (by name or by
    `sensitive = true`), also redact literal default/value assignments."""
    text = redact_sensitive(raw)
    if is_sensitive_block(raw, labels):
        text = DEFAULT_LITERAL_RE.sub(
            lambda m: f'{m.group(1)}{m.group(2)}{m.group(3)}"{REDACTED_VALUE}"{m.group(5)}',
            text,
        )
    return text


def redact_sensitive(text: str) -> str:
    """Reemplaza valores literales de atributos sensibles (passwords, tokens, keys).

    Only literal strings are redacted; references such as var.x or data sources
    are preserved so the dependency graph remains intact.
    """
    return SENSITIVE_LITERAL_RE.sub(
        lambda m: f'{m.group(1)}{m.group(2)}{m.group(3)}"{REDACTED_VALUE}"{m.group(5)}',
        text,
    )


def extract_references(text: str) -> list[str]:
    refs = set()
    for match in REFERENCE_RE.finditer(strip_comments(text)):
        ref = match.group(1).rstrip(".,)")
        if ref.startswith(("each.", "count.", "path.", "terraform.", "aws.")):
            continue
        if "amazonaws" in ref:
            continue
        if re.fullmatch(r"\d+(?:\.\d+)+", ref):
            continue
        refs.add(ref)
    return sorted(refs)
