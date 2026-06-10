from __future__ import annotations

from typing import Any


def format_node_line(node: dict[str, Any]) -> str:
    tags = ", ".join(node.get("domain_tags", [])) or "no tags"
    return f"{node['id']} ({node['kind']}, {tags}) - {node['file']}:{node['start_line']}"


def render_summary(graph: dict[str, Any]) -> str:
    kinds: dict[str, int] = {}
    domains: dict[str, int] = {}
    for node in graph["nodes"].values():
        kinds[node["kind"]] = kinds.get(node["kind"], 0) + 1
        for tag in node.get("domain_tags", []):
            domains[tag] = domains.get(tag, 0) + 1

    lines = [
        "CRS graph summary",
        f"Project: {graph['project_root']}",
        f"Generated: {graph['generated_at']}",
        f"Nodes: {graph['node_count']}",
        f"Relations: {graph['relation_count']}",
        "",
        "By kind:",
    ]
    lines.extend(f"- {kind}: {count}" for kind, count in sorted(kinds.items()))
    lines.append("")
    lines.append("By domain:")
    lines.extend(f"- {domain}: {count}" for domain, count in sorted(domains.items()))
    return "\n".join(lines)


def render_search(graph: dict[str, Any], term: str) -> str:
    matches = [
        node
        for node in graph["nodes"].values()
        if term.lower() in node["id"].lower()
        or term.lower() in node["file"].lower()
        or term.lower() in " ".join(node.get("domain_tags", [])).lower()
    ]
    if not matches:
        return f"No matches found for '{term}'."
    return "\n".join(format_node_line(node) for node in sorted(matches, key=lambda item: item["id"]))


def render_impact(result: dict[str, Any]) -> str:
    lines = [
        f"Change impact: {result['node']}",
        "",
        "Component:",
        f"- {format_node_line(result['changed_component'])}",
        "",
        "Direct dependencies to review:",
    ]
    if result["direct_dependencies"]:
        for item in result["direct_dependencies"]:
            rel = item["relation"]
            lines.append(f"- {item['node']} via {rel['kind']} ({rel['evidence']})")
    else:
        lines.append("- No direct dependencies were detected.")

    lines.append("")
    lines.append("Affected downstream components:")
    if result["affected"]:
        for item in result["affected"]:
            rel = item["relation"]
            lines.append(f"- depth {item['depth']}: {item['node']} via {rel['kind']} ({rel['evidence']})")
    else:
        lines.append("- No dependents were detected.")
    return "\n".join(lines)


def render_failure(result: dict[str, Any]) -> str:
    lines = [
        f"Failure analysis: {result['node']}",
        "",
        "Failed component:",
        f"- {format_node_line(result['failed_component'])}",
        "",
        "Likely risks:",
    ]
    lines.extend(f"- {risk}" for risk in result["risks"])
    lines.append("")
    lines.append("Potentially affected components:")
    if result["affected"]:
        for item in result["affected"]:
            rel = item["relation"]
            lines.append(f"- depth {item['depth']}: {item['node']} via {rel['kind']}")
    else:
        lines.append("- No dependents were detected.")
    return "\n".join(lines)


def render_postmortem(result: dict[str, Any]) -> str:
    node = result["failed_component"]
    affected = result["affected"]
    risks = result["risks"]
    affected_lines = "\n".join(
        f"- {item['node']} through `{item['relation']['kind']}` from `{item['relation']['source']}`"
        for item in affected
    ) or "- No dependent components were detected by CRS."

    risk_lines = "\n".join(f"- {risk}" for risk in risks)

    return f"""# Postmortem - Failure in {result['node']}

## Summary

A failure was detected in `{result['node']}`. The component is defined at `{node['file']}:{node['start_line']}` and CRS classifies it with these tags: `{", ".join(node.get("domain_tags", [])) or "no tags"}`.

## Impact

{affected_lines}

## Technical and functional risks

{risk_lines}

## Initial hypothesis

The failure may have affected services that depend directly or indirectly on the component. First validate node health, metrics, logs, recent deployment events, and configuration changes.

## Timeline

- T0: Alert or incident detected.
- T0 + 5m: Affected component confirmed.
- T0 + 15m: Review CRS dependents and observability data.
- T0 + 30m: Initial mitigation or rollback.
- T0 + 60m: Functional validation with business teams.

## Suggested mitigation actions

- Confirm the resource state in AWS and Kubernetes.
- Review recent changes to `{node['file']}`.
- Validate dependents listed by CRS.
- Review latency, error, saturation, and backlog dashboards.
- Run the rollback or failover playbook when applicable.

## Preventive actions

- Add component-specific alerts.
- Add impact tests for its dependents.
- Document ownership, SLOs, and recovery procedures.
- Assess whether the dependency needs decoupling, caching, retries, a DLQ, or a circuit breaker.

## CRS evidence

```text
Node: {result['node']}
File: {node['file']}:{node['start_line']}-{node['end_line']}
Detected dependents: {len(affected)}
```
"""
