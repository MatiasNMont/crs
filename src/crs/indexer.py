from __future__ import annotations

import re
import sys
from pathlib import Path

from .hcl_scanner import extract_attributes, extract_references, is_sensitive_block, is_sensitive_key, redact_block, scan_file
from .models import Graph, Node, Relation


DOMAIN_KEYWORDS = {
    "network": ["vpc", "subnet", "route", "nat", "internet_gateway", "endpoint"],
    "security": ["iam", "kms", "waf", "security_group", "secret", "policy"],
    "compute": ["eks", "node_group", "kubernetes_deployment", "helm_release"],
    "data": ["rds", "aurora", "dynamodb", "elasticache", "s3", "db_"],
    "messaging": ["sqs", "event_bus", "eventbridge", "sns", "msk"],
    "observability": ["cloudwatch", "prometheus", "grafana", "otel", "opentelemetry"],
    "transactional": ["transaction", "payment", "order", "checkout", "invoice", "booking", "claim", "policy", "fulfillment", "reservation"],
}


def discover_tf_files(project_root: Path) -> list[Path]:
    ignored = {".terraform", ".git", ".crs"}
    root = project_root.resolve()
    files = []
    for path in root.rglob("*.tf"):
        if any(part in ignored for part in path.parts):
            continue
        # Do not follow symlinks or files that resolve outside the project.
        if path.is_symlink():
            continue
        try:
            path.resolve(strict=True).relative_to(root)
        except (OSError, ValueError):
            continue
        files.append(path)
    return sorted(files)


def scope_for_file(relative_file: Path) -> str:
    parent = relative_file.parent.as_posix()
    return "root" if parent == "." else parent


def scoped_id(scope: str, base_id: str) -> str:
    return f"{scope}::{base_id}"


def infer_domain_tags(node_id: str, config: str) -> list[str]:
    haystack = f"{node_id}\n{config}".lower()
    tags = []
    for tag, keywords in DOMAIN_KEYWORDS.items():
        if any(keyword in haystack for keyword in keywords):
            tags.append(tag)
    return tags


def normalize_reference(ref: str, node_ids: set[str], scope: str) -> str | None:
    if ref in node_ids:
        return ref

    local_ref = scoped_id(scope, ref)
    if local_ref in node_ids:
        return local_ref

    root_ref = scoped_id("root", ref)
    if root_ref in node_ids:
        return root_ref

    parts = ref.split(".")
    if len(parts) >= 2:
        candidate = ".".join(parts[:2])
        local_candidate = scoped_id(scope, candidate)
        if local_candidate in node_ids:
            return local_candidate
        root_candidate = scoped_id("root", candidate)
        if root_candidate in node_ids:
            return root_candidate
    if len(parts) >= 3 and parts[0] == "data":
        candidate = ".".join(parts[:3])
        local_candidate = scoped_id(scope, candidate)
        if local_candidate in node_ids:
            return local_candidate
        root_candidate = scoped_id("root", candidate)
        if root_candidate in node_ids:
            return root_candidate
    return None


def extract_depends_on(config: str) -> list[str]:
    match = re.search(r"depends_on\s*=\s*\[(.*?)\]", config, flags=re.DOTALL)
    if not match:
        return []
    return [item.strip().strip('"') for item in match.group(1).split(",") if item.strip()]


def build_graph(project_root: Path) -> Graph:
    root = project_root.resolve()
    graph = Graph.empty(root)

    for tf_file in discover_tf_files(root):
        # One malformed or hostile file must not abort the whole indexing run.
        try:
            blocks = scan_file(tf_file, root)
        except (ValueError, OSError) as exc:
            print(f"crs warning: skipping {tf_file.relative_to(root)} ({exc})", file=sys.stderr)
            continue
        for block in blocks:
            scope = scope_for_file(block.file)
            node_id = scoped_id(scope, block.id)
            attrs = extract_attributes(block.body)
            block_sensitive = is_sensitive_block(block.raw, block.labels)
            for key, value in attrs.items():
                sensitive = is_sensitive_key(key) or (block_sensitive and key in {"default", "value"})
                if sensitive and value.strip().startswith('"'):
                    attrs[key] = '"***REDACTED***"'
            refs = extract_references(block.body)
            node = Node(
                id=node_id,
                kind=block.kind,
                labels=block.labels,
                file=block.file.as_posix(),
                start_line=block.start_line,
                end_line=block.end_line,
                config=redact_block(block.raw, block.labels),
                attributes={**attrs, "crs_scope": scope, "terraform_address": block.id},
                references=refs,
                domain_tags=infer_domain_tags(node_id, block.raw),
            )
            graph.nodes[node.id] = node

    node_ids = set(graph.nodes)
    seen_relations: set[tuple[str, str, str]] = set()

    def add_relation(source: str, target: str, kind: str, evidence: str) -> None:
        key = (source, target, kind)
        if source == target or target not in graph.nodes or key in seen_relations:
            return
        seen_relations.add(key)
        source_node = graph.nodes[source]
        graph.relations.append(
            Relation(
                source=source,
                target=target,
                kind=kind,
                evidence=evidence,
                file=source_node.file,
                line=source_node.start_line,
            )
        )

    for node in graph.nodes.values():
        scope = node.attributes.get("crs_scope", "root")
        for ref in node.references:
            target = normalize_reference(ref, node_ids, scope)
            if target:
                target_address = graph.nodes[target].attributes.get("terraform_address", target)
                relation_kind = "uses_variable" if target_address.startswith("var.") else "references"
                add_relation(node.id, target, relation_kind, ref)

        for dep in extract_depends_on(node.config):
            target = normalize_reference(dep, node_ids, scope)
            if target:
                add_relation(node.id, target, "depends_on", dep)

        if node.kind == "output":
            for ref in node.references:
                target = normalize_reference(ref, node_ids, scope)
                if target:
                    add_relation(node.id, target, "exposes", ref)

        if node.kind == "module":
            source = node.attributes.get("source")
            if source and source.strip('"').startswith(("./", "../")):
                add_relation(node.id, node.id, "module_source", source)

    add_directory_containment(graph)
    return graph


def add_directory_containment(graph: Graph) -> None:
    module_nodes = [node for node in graph.nodes.values() if node.kind == "module"]
    seen = {(rel.source, rel.target, rel.kind) for rel in graph.relations}

    for module in module_nodes:
        source = module.attributes.get("source", "").strip('"')
        if not source.startswith("./"):
            continue
        # Node file paths are stored POSIX-style, so compare in POSIX form.
        module_dir = source[2:].replace("\\", "/").strip("/")
        for node in graph.nodes.values():
            if node.id == module.id:
                continue
            if node.file.startswith(module_dir + "/"):
                key = (module.id, node.id, "contains")
                if key in seen:
                    continue
                seen.add(key)
                graph.relations.append(
                    Relation(
                        source=module.id,
                        target=node.id,
                        kind="contains",
                        evidence=f"source={source}",
                        file=module.file,
                        line=module.start_line,
                    )
                )
