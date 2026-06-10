from __future__ import annotations

import hashlib
import html
import json
from difflib import unified_diff
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import Graph
from .query import impact
from .storage import write_graph_snapshot


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def node_hash(node: dict[str, Any]) -> str:
    payload = {
        "kind": node.get("kind"),
        "labels": node.get("labels"),
        "file": node.get("file"),
        "config": node.get("config"),
        "attributes": node.get("attributes", {}),
        "references": node.get("references", []),
        "domain_tags": node.get("domain_tags", []),
    }
    return stable_hash(json.dumps(payload, sort_keys=True, ensure_ascii=False))


def relation_key(relation: dict[str, Any]) -> str:
    return "|".join(
        [
            relation.get("source", ""),
            relation.get("target", ""),
            relation.get("kind", ""),
            relation.get("evidence", ""),
        ]
    )


def graph_to_payload(graph: Graph) -> dict[str, Any]:
    return graph.to_dict()


def build_preflight_report(
    old_graph: dict[str, Any] | None,
    new_graph: dict[str, Any],
    max_affected: int | None = None,
) -> dict[str, Any]:
    old_nodes = old_graph.get("nodes", {}) if old_graph else {}
    new_nodes = new_graph.get("nodes", {})

    old_ids = set(old_nodes)
    new_ids = set(new_nodes)
    added = sorted(new_ids - old_ids)
    removed = sorted(old_ids - new_ids)
    common = old_ids & new_ids
    modified = sorted(node_id for node_id in common if node_hash(old_nodes[node_id]) != node_hash(new_nodes[node_id]))

    old_relations = {relation_key(relation) for relation in old_graph.get("relations", [])} if old_graph else set()
    new_relations = {relation_key(relation) for relation in new_graph.get("relations", [])}

    node_reports = []
    for change_type, node_ids, source_graph in [
        ("added", added, new_graph),
        ("modified", modified, new_graph),
        ("removed", removed, old_graph),
    ]:
        if not source_graph:
            continue
        for node_id in node_ids:
            impact_result = impact(source_graph, node_id, depth=3) if node_id in source_graph.get("nodes", {}) else None
            affected = impact_result.get("affected", []) if impact_result else []
            affected_domains = summarize_domains(source_graph, affected)
            previous_node = old_nodes.get(node_id)
            current_node = new_nodes.get(node_id)
            exact_diff = exact_node_diff(previous_node, current_node)
            node_reports.append(
                {
                    "change_type": change_type,
                    "node_id": node_id,
                    "file": source_graph["nodes"].get(node_id, {}).get("file"),
                    "start_line": source_graph["nodes"].get(node_id, {}).get("start_line"),
                    "domain_tags": source_graph["nodes"].get(node_id, {}).get("domain_tags", []),
                    "affected_count": len(affected),
                    "affected_domains": affected_domains,
                    "exact_diff": exact_diff,
                    "risk_summary": risk_summary(source_graph["nodes"].get(node_id, {}), affected_domains, len(affected)),
                    "affected_nodes": [
                        {
                            "node": item["node"],
                            "depth": item["depth"],
                            "relation": item["relation"]["kind"],
                            "file": item["metadata"].get("file"),
                        }
                        for item in affected
                    ],
                    "direct_dependencies": [
                        {
                            "node": item["node"],
                            "relation": item["relation"]["kind"],
                            "file": item["metadata"].get("file"),
                        }
                        for item in impact_result.get("direct_dependencies", [])
                    ]
                    if impact_result
                    else [],
                }
            )

    total_affected = sum(report["affected_count"] for report in node_reports)
    max_node_affected = max((report["affected_count"] for report in node_reports), default=0)
    threshold_exceeded = max_affected is not None and max_node_affected > max_affected

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_root": new_graph.get("project_root"),
        "baseline_exists": old_graph is not None,
        "summary": {
            "added": len(added),
            "modified": len(modified),
            "removed": len(removed),
            "relations_added": len(new_relations - old_relations),
            "relations_removed": len(old_relations - new_relations),
            "total_affected_references": total_affected,
            "max_node_affected": max_node_affected,
            "max_affected_threshold": max_affected,
            "threshold_exceeded": threshold_exceeded,
        },
        "changed_nodes": node_reports,
        "relation_diff": {
            "added": sorted(new_relations - old_relations),
            "removed": sorted(old_relations - new_relations),
        },
        "recommendation": recommendation(node_reports, threshold_exceeded),
        "llm_prompt": render_preflight_prompt(
            {
                "project_root": new_graph.get("project_root"),
                "changed_nodes": node_reports,
                "summary": {
                    "added": len(added),
                    "modified": len(modified),
                    "removed": len(removed),
                    "relations_added": len(new_relations - old_relations),
                    "relations_removed": len(old_relations - new_relations),
                    "max_node_affected": max_node_affected,
                    "threshold_exceeded": threshold_exceeded,
                },
            }
        ),
    }


def summarize_domains(graph: dict[str, Any], affected: list[dict[str, Any]]) -> dict[str, int]:
    domains: dict[str, int] = {}
    for item in affected:
        node = graph["nodes"].get(item["node"], {})
        tags = node.get("domain_tags", []) or ["unclassified"]
        for tag in tags:
            domains[tag] = domains.get(tag, 0) + 1
    return dict(sorted(domains.items()))


def exact_node_diff(old_node: dict[str, Any] | None, new_node: dict[str, Any] | None) -> dict[str, Any]:
    old_node = old_node or {}
    new_node = new_node or {}
    old_attrs = old_node.get("attributes", {}) or {}
    new_attrs = new_node.get("attributes", {}) or {}
    old_attr_keys = set(old_attrs)
    new_attr_keys = set(new_attrs)

    modified_attrs = {}
    for key in sorted(old_attr_keys & new_attr_keys):
        if old_attrs.get(key) != new_attrs.get(key):
            modified_attrs[key] = {
                "before": old_attrs.get(key),
                "after": new_attrs.get(key),
            }

    config_diff = list(
        unified_diff(
            (old_node.get("config") or "").splitlines(),
            (new_node.get("config") or "").splitlines(),
            fromfile="before",
            tofile="after",
            lineterm="",
        )
    )

    return {
        "attribute_changes": {
            "added": {key: new_attrs[key] for key in sorted(new_attr_keys - old_attr_keys)},
            "removed": {key: old_attrs[key] for key in sorted(old_attr_keys - new_attr_keys)},
            "modified": modified_attrs,
        },
        "reference_changes": {
            "added": sorted(set(new_node.get("references", [])) - set(old_node.get("references", []))),
            "removed": sorted(set(old_node.get("references", [])) - set(new_node.get("references", []))),
        },
        "domain_tag_changes": {
            "added": sorted(set(new_node.get("domain_tags", [])) - set(old_node.get("domain_tags", []))),
            "removed": sorted(set(old_node.get("domain_tags", [])) - set(new_node.get("domain_tags", []))),
        },
        "config_unified_diff": config_diff,
    }


def risk_summary(node: dict[str, Any], affected_domains: dict[str, int], affected_count: int) -> list[str]:
    tags = set(node.get("domain_tags", []))
    risks: list[str] = []
    if "security" in tags or affected_domains.get("security"):
        risks.append("Security/IAM/KMS/Secrets: validate permissions, encryption, secret access, and role blast radius.")
    if "data" in tags or affected_domains.get("data"):
        risks.append("Data/persistence: validate replacements, backups, restores, migrations, consistency, and downtime.")
    if "network" in tags or affected_domains.get("network"):
        risks.append("Network/connectivity: validate subnets, security groups, routes, endpoints, DNS, and traffic scope.")
    if "compute" in tags or affected_domains.get("compute"):
        risks.append("Compute/EKS/Kubernetes: validate scheduling, replicas, readiness, ALB/Ingress, and capacity.")
    if "messaging" in tags or affected_domains.get("messaging"):
        risks.append("Messaging/events: validate DLQs, idempotency, backlog, replay, and duplication.")
    if "transactional" in tags or affected_domains.get("transactional"):
        risks.append("Transactional workflows: validate state transitions, idempotency, retries, reconciliation, auditing, and functional impact.")
    if affected_count >= 5:
        risks.append(f"Large blast radius: {affected_count} dependent nodes detected.")
    if not risks:
        risks.append("Risk was not classified automatically: review direct dependencies and affected nodes.")
    return risks


def recommendation(node_reports: list[dict[str, Any]], threshold_exceeded: bool) -> str:
    if not node_reports:
        return "No structural changes were detected in the CRS graph."
    if threshold_exceeded:
        return "Review impact before terraform apply: the blast radius exceeds the configured threshold."
    high = [report for report in node_reports if report["affected_count"] >= 5]
    if high:
        return "Review nodes with a large blast radius before terraform apply."
    return "Detected impact is within the threshold. Review the report before continuing with terraform plan/apply."


def render_preflight_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# CRS Preflight Impact Report",
        "",
        f"Project: `{report['project_root']}`",
        f"Generated: `{report['generated_at']}`",
        "",
        "## Summary",
        "",
        f"- Added nodes: {summary['added']}",
        f"- Modified nodes: {summary['modified']}",
        f"- Removed nodes: {summary['removed']}",
        f"- Added relationships: {summary['relations_added']}",
        f"- Removed relationships: {summary['relations_removed']}",
        f"- Maximum blast radius per node: {summary['max_node_affected']}",
        f"- Threshold exceeded: {summary['threshold_exceeded']}",
        "",
        f"Recommendation: {report['recommendation']}",
        "",
        "## Detected changes",
        "",
    ]

    if not report["changed_nodes"]:
        lines.append("No structural changes were detected.")
        return "\n".join(lines)

    for item in report["changed_nodes"]:
        lines.extend(
            [
                f"### {item['change_type']}: `{item['node_id']}`",
                "",
                f"- File: `{item['file']}:{item['start_line']}`",
                f"- Tags: `{', '.join(item['domain_tags']) or 'no tags'}`",
                f"- Affected nodes: {item['affected_count']}",
                f"- Affected domains: `{json.dumps(item['affected_domains'], ensure_ascii=False)}`",
                "",
                "Exact node diff:",
                "",
                f"- Added attributes: `{json.dumps(item['exact_diff']['attribute_changes']['added'], ensure_ascii=False)}`",
                f"- Removed attributes: `{json.dumps(item['exact_diff']['attribute_changes']['removed'], ensure_ascii=False)}`",
                f"- Modified attributes: `{json.dumps(item['exact_diff']['attribute_changes']['modified'], ensure_ascii=False)}`",
                f"- Added references: `{json.dumps(item['exact_diff']['reference_changes']['added'], ensure_ascii=False)}`",
                f"- Removed references: `{json.dumps(item['exact_diff']['reference_changes']['removed'], ensure_ascii=False)}`",
                "",
                "Suggested risks:",
            ]
        )
        lines.extend(f"- {risk}" for risk in item["risk_summary"])
        lines.extend(
            [
                "",
                "Direct dependencies:",
            ]
        )
        if item["direct_dependencies"]:
            lines.extend(f"- `{dep['node']}` via `{dep['relation']}`" for dep in item["direct_dependencies"])
        else:
            lines.append("- None detected.")
        lines.append("")
        lines.append("Affected downstream nodes:")
        if item["affected_nodes"]:
            lines.extend(
                f"- depth {affected['depth']}: `{affected['node']}` via `{affected['relation']}`"
                for affected in item["affected_nodes"]
            )
        else:
            lines.append("- None detected.")
        lines.append("")

    return "\n".join(lines)


def render_preflight_prompt(report: dict[str, Any]) -> str:
    lines = [
        "# LLM Prompt - Terraform Impact Analysis with CRS",
        "",
        "Analyze the impact of Terraform changes using only the following CRS context.",
        "Do not grep the complete repository. Open only the listed files and line ranges when needed.",
        "",
        "## Objective",
        "",
        "Explain change impact across resources, security, data, network, compute, messaging, and functional domains.",
        "Identify risks, pre-apply validations, open questions, and a go/no-go recommendation.",
        "",
        "## CRS summary",
        "",
        f"- Project: `{report['project_root']}`",
        f"- Added nodes: {report['summary']['added']}",
        f"- Modified nodes: {report['summary']['modified']}",
        f"- Removed nodes: {report['summary']['removed']}",
        f"- Added relationships: {report['summary']['relations_added']}",
        f"- Removed relationships: {report['summary']['relations_removed']}",
        f"- Max blast radius: {report['summary']['max_node_affected']}",
        f"- Threshold exceeded: {report['summary']['threshold_exceeded']}",
        "",
        "## Changes detected by CRS",
        "",
    ]

    if not report["changed_nodes"]:
        lines.extend(
            [
                "No structural changes were detected in the CRS graph.",
                "",
                "State that the graph shows no new blast radius and still recommend reviewing `terraform plan`.",
            ]
        )
        return "\n".join(lines)

    for item in report["changed_nodes"]:
        lines.extend(
            [
                f"### {item['change_type']}: `{item['node_id']}`",
                "",
                f"- File: `{item['file']}:{item['start_line']}`",
                f"- Node tags: `{', '.join(item['domain_tags']) or 'no tags'}`",
                f"- Downstream affected node count: {item['affected_count']}",
                f"- Affected domains: `{json.dumps(item['affected_domains'], ensure_ascii=False)}`",
                "",
                "Exact node diff:",
                f"- Added attributes: `{json.dumps(item['exact_diff']['attribute_changes']['added'], ensure_ascii=False)}`",
                f"- Removed attributes: `{json.dumps(item['exact_diff']['attribute_changes']['removed'], ensure_ascii=False)}`",
                f"- Modified attributes: `{json.dumps(item['exact_diff']['attribute_changes']['modified'], ensure_ascii=False)}`",
                f"- Added references: `{json.dumps(item['exact_diff']['reference_changes']['added'], ensure_ascii=False)}`",
                f"- Removed references: `{json.dumps(item['exact_diff']['reference_changes']['removed'], ensure_ascii=False)}`",
                "",
                "Unified configuration diff:",
                "```diff",
                "\n".join(item["exact_diff"]["config_unified_diff"][:80]) or "no configuration diff",
                "```",
                "",
                "Preliminary CRS risks:",
            ]
        )
        lines.extend(f"- {risk}" for risk in item["risk_summary"])
        lines.extend(["", "Direct dependencies:"])
        if item["direct_dependencies"]:
            lines.extend(f"- `{dep['node']}` via `{dep['relation']}` in `{dep['file']}`" for dep in item["direct_dependencies"])
        else:
            lines.append("- None detected.")

        lines.extend(["", "Affected downstream nodes:"])
        if item["affected_nodes"]:
            lines.extend(
                f"- depth {affected['depth']}: `{affected['node']}` via `{affected['relation']}` in `{affected['file']}`"
                for affected in item["affected_nodes"]
            )
        else:
            lines.append("- None detected.")
        lines.append("")

    lines.extend(
        [
            "## Expected response",
            "",
            "Return an English response with these sections:",
            "",
            "1. Executive summary of the change.",
            "2. Blast radius by resource/component.",
            "3. Domain impact: security, data, network, compute, messaging, and business.",
            "4. Risks before `terraform apply`.",
            "5. Concrete validations against `terraform plan`.",
            "6. Files worth opening and why.",
            "7. Go/no-go recommendation.",
            "",
            "Do not invent resources outside the CRS context. If information is missing, state exactly which file or data you need.",
        ]
    )
    return "\n".join(lines)


def render_preflight_html(report: dict[str, Any]) -> str:
    payload = json.dumps(report, ensure_ascii=False).replace("</", "<\\/")
    title = html.escape("CRS Preflight Impact Report")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    body {{ margin: 0; font-family: Segoe UI, Arial, sans-serif; background: #f7f8fb; color: #18202f; }}
    header {{ padding: 24px 32px; background: #1d4ed8; color: white; }}
    main {{ max-width: 1200px; margin: 0 auto; padding: 24px 32px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }}
    .card {{ background: white; border: 1px solid #d8dee9; border-radius: 8px; padding: 16px; box-shadow: 0 8px 24px rgba(24,32,47,.08); }}
    .danger {{ color: #b42318; }}
    code {{ background: #edf2f7; padding: 2px 5px; border-radius: 4px; }}
    ul {{ padding-left: 20px; }}
  </style>
</head>
<body>
  <header>
    <h1>CRS Preflight Impact Report</h1>
    <div>{html.escape(report.get('project_root') or '')}</div>
  </header>
  <main id="app"></main>
  <script id="report" type="application/json">{payload}</script>
  <script>
    const report = JSON.parse(document.getElementById("report").textContent);
    const esc = value => String(value).replace(/[&<>"']/g, c => ({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}}[c]));
    const s = report.summary;
    document.getElementById("app").innerHTML = `
      <section class="grid">
        <div class="card"><h3>Added</h3><strong>${{s.added}}</strong></div>
        <div class="card"><h3>Modified</h3><strong>${{s.modified}}</strong></div>
        <div class="card"><h3>Removed</h3><strong>${{s.removed}}</strong></div>
        <div class="card"><h3>Max blast radius</h3><strong class="${{s.threshold_exceeded ? 'danger' : ''}}">${{s.max_node_affected}}</strong></div>
      </section>
      <section class="card"><h2>Recommendation</h2><p>${{esc(report.recommendation)}}</p></section>
      <h2>Changes</h2>
      ${{report.changed_nodes.map(item => `
        <article class="card">
          <h3>${{esc(item.change_type)}}: <code>${{esc(item.node_id)}}</code></h3>
          <p>${{esc(item.file)}}:${{item.start_line || ""}}</p>
          <p>Affected nodes: <strong>${{item.affected_count}}</strong></p>
          <h4>Affected downstream nodes</h4>
          <ul>${{item.affected_nodes.map(n => `<li>depth ${{n.depth}}: <code>${{esc(n.node)}}</code> via ${{esc(n.relation)}}</li>`).join("") || "<li>None detected.</li>"}}</ul>
        </article>
      `).join("") || '<section class="card">No structural changes were detected.</section>'}}
    `;
  </script>
</body>
</html>
"""


def save_preflight_report(project_root: Path, report: dict[str, Any], candidate_graph: dict[str, Any] | None = None) -> dict[str, Path]:
    output_dir = project_root / ".crs" / "preflight"
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    paths = {
        "json": output_dir / f"preflight-{stamp}.json",
        "markdown": output_dir / f"preflight-{stamp}.md",
        "html": output_dir / f"preflight-{stamp}.html",
        "prompt": output_dir / f"preflight-{stamp}.prompt.md",
        "latest_json": output_dir / "latest.json",
        "latest_markdown": output_dir / "latest.md",
        "latest_html": output_dir / "latest.html",
        "latest_prompt": output_dir / "latest.prompt.md",
    }
    json_text = json.dumps(report, indent=2, ensure_ascii=False)
    markdown_text = render_preflight_markdown(report)
    html_text = render_preflight_html(report)
    prompt_text = report["llm_prompt"]
    if candidate_graph:
        candidate_text = json.dumps(candidate_graph, indent=2, sort_keys=True, ensure_ascii=False)
        paths["candidate_graph"] = write_graph_snapshot(project_root, candidate_text, prefix="preflight-candidate")
        report["candidate_graph_snapshot"] = str(paths["candidate_graph"])
        json_text = json.dumps(report, indent=2, ensure_ascii=False)
        markdown_text = render_preflight_markdown(report)
        html_text = render_preflight_html(report)
        prompt_text = report["llm_prompt"]
    paths["json"].write_text(json_text, encoding="utf-8")
    paths["markdown"].write_text(markdown_text, encoding="utf-8")
    paths["html"].write_text(html_text, encoding="utf-8")
    paths["prompt"].write_text(prompt_text, encoding="utf-8")
    paths["latest_json"].write_text(json_text, encoding="utf-8")
    paths["latest_markdown"].write_text(markdown_text, encoding="utf-8")
    paths["latest_html"].write_text(html_text, encoding="utf-8")
    paths["latest_prompt"].write_text(prompt_text, encoding="utf-8")
    return paths
