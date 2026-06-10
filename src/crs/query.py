from __future__ import annotations

from collections import deque
from typing import Any


def resolve_node(graph: dict[str, Any], query: str) -> str:
    nodes = graph["nodes"]
    if query in nodes:
        return query

    matches = [node_id for node_id in nodes if query.lower() in node_id.lower()]
    if not matches:
        raise ValueError(f"No node found for '{query}'. Use 'crs search <project> {query}'.")
    if len(matches) > 1:
        sample = ", ".join(matches[:10])
        raise ValueError(f"'{query}' is ambiguous. Matches: {sample}")
    return matches[0]


def relation_maps(graph: dict[str, Any]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    outgoing = graph.get("outgoing", {})
    incoming = graph.get("incoming", {})
    return outgoing, incoming


def walk(
    graph: dict[str, Any],
    start: str,
    direction: str,
    depth: int = 3,
) -> list[dict[str, Any]]:
    outgoing, incoming = relation_maps(graph)
    relation_source = incoming if direction == "dependents" else outgoing
    visited = {start}
    queue = deque([(start, 0)])
    results: list[dict[str, Any]] = []

    while queue:
        node_id, level = queue.popleft()
        if level >= depth:
            continue

        for relation in relation_source.get(node_id, []):
            next_node = relation["source"] if direction == "dependents" else relation["target"]
            if next_node in visited:
                continue
            visited.add(next_node)
            result = {
                "node": next_node,
                "depth": level + 1,
                "relation": relation,
                "metadata": graph["nodes"].get(next_node, {}),
            }
            results.append(result)
            queue.append((next_node, level + 1))

    return results


def impact(graph: dict[str, Any], node_id: str, depth: int = 3) -> dict[str, Any]:
    affected = walk(graph, node_id, "dependents", depth)
    dependencies = walk(graph, node_id, "dependencies", 1)
    return {
        "node": node_id,
        "changed_component": graph["nodes"][node_id],
        "direct_dependencies": dependencies,
        "affected": affected,
    }


def failure(graph: dict[str, Any], node_id: str, depth: int = 3) -> dict[str, Any]:
    affected = walk(graph, node_id, "dependents", depth)
    dependencies = walk(graph, node_id, "dependencies", 2)
    node = graph["nodes"][node_id]
    risks = infer_risks(node, affected)
    return {
        "node": node_id,
        "failed_component": node,
        "dependencies": dependencies,
        "affected": affected,
        "risks": risks,
    }


def infer_risks(node: dict[str, Any], affected: list[dict[str, Any]]) -> list[str]:
    tags = set(node.get("domain_tags", []))
    node_id = node["id"].lower()
    risks: list[str] = []

    if "data" in tags or any(word in node_id for word in ["rds", "aurora", "dynamodb", "redis", "s3"]):
        risks.append("Persistence loss or degradation, slow queries, timeouts, and transactional errors.")
    if "network" in tags:
        risks.append("Service connectivity interruption, loss of ingress/egress, or subnet isolation.")
    if "security" in tags:
        risks.append("Authentication/authorization failures, inaccessible secrets, or unavailable encryption services.")
    if "compute" in tags or "eks" in node_id or "kubernetes" in node_id:
        risks.append("Unschedulable pods, restarts, insufficient capacity, or partial cluster downtime.")
    if "messaging" in tags or "sqs" in node_id or "event" in node_id:
        risks.append("Event backlog, duplication, delayed reconciliation, or lost asynchronous processing.")
    if "transactional" in tags:
        risks.append("Functional impact on transaction processing, state transitions, idempotency, reconciliation, or auditing.")
    if affected:
        risks.append(f"Propagation to {len(affected)} dependent component(s) detected in the graph.")
    if not risks:
        risks.append("Impact was not classified automatically; review incoming and outgoing node relationships.")
    return risks


DETAIL_LEVELS = ("minimal", "summary", "full")


def node_view(node_id: str, node: dict[str, Any], detail: str, is_focus: bool) -> dict[str, Any]:
    """Project a node according to the requested detail level.

    - minimal: structure only (id, type, location, tags). No configuration.
    - summary: structure plus full configuration for the focus node only.
    - full: structure plus full configuration for all nodes.
    """
    view = {
        "id": node_id,
        "kind": node.get("kind"),
        "file": node.get("file"),
        "start_line": node.get("start_line"),
        "end_line": node.get("end_line"),
        "domain_tags": node.get("domain_tags", []),
        "terraform_address": node.get("attributes", {}).get("terraform_address"),
    }
    if detail == "full" or (detail == "summary" and is_focus):
        view["config"] = node.get("config", "")
        view["references"] = node.get("references", [])
    return view


def compact_context(graph: dict[str, Any], node_id: str, depth: int = 2, detail: str = "summary") -> dict[str, Any]:
    if detail not in DETAIL_LEVELS:
        raise ValueError(f"detail debe ser uno de: {', '.join(DETAIL_LEVELS)}")

    impacted = impact(graph, node_id, depth)
    related_ids = {node_id}
    related_ids.update(item["node"] for item in impacted["affected"])
    related_ids.update(item["node"] for item in impacted["direct_dependencies"])

    nodes = {
        related_id: node_view(related_id, graph["nodes"][related_id], detail, related_id == node_id)
        for related_id in sorted(related_ids)
    }
    # Compact relationships into deterministic [source, target, kind] tuples.
    # Keep only relationships whose endpoints are both present in the context.
    relations = sorted(
        {
            (relation["source"], relation["target"], relation["kind"])
            for relation in graph["relations"]
            if relation["source"] in related_ids and relation["target"] in related_ids
        }
    )
    return {
        "focus": node_id,
        "detail": detail,
        "instruction": "CRS structural context. Full configuration is included only for the focus node; request other node configuration by file:lines only when needed.",
        "nodes": nodes,
        "relations": [list(relation) for relation in relations],
        "relations_legend": ["source", "target", "kind"],
    }
