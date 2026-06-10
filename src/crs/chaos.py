from __future__ import annotations

import html
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .query import failure, impact, resolve_node


@dataclass(frozen=True)
class ChaosScenario:
    id: str
    title: str
    domain: str
    fault: str
    parameters: dict[str, Any]
    hypothesis: str
    signals: list[str]
    guardrails: list[str]
    abort_conditions: list[str]


SCENARIOS = [
    ChaosScenario(
        id="data-outage",
        title="Persistence outage",
        domain="data",
        fault="outage",
        parameters={"duration_minutes": 10, "error_rate": 1.0},
        hypothesis="Dependent services should degrade gracefully, retry, or open a circuit breaker without losing traceability.",
        signals=["5xx", "p95/p99 latency", "connection errors", "rollback/retry", "audit events"],
        guardrails=["do not run in production without a change window", "validated backup", "tested rollback"],
        abort_conditions=["data loss", "sustained write errors", "critical SLO exceeded"],
    ),
    ChaosScenario(
        id="data-latency",
        title="Elevated database/cache latency",
        domain="data",
        fault="latency",
        parameters={"duration_minutes": 15, "latency_ms": 750},
        hypothesis="The platform should enforce controlled timeouts and prevent cascading failures toward the API and frontend.",
        signals=["database latency", "timeouts", "pool saturation", "queue depth", "API p95"],
        guardrails=["duration limit", "active alerts", "immediate rollback"],
        abort_conditions=["pool saturation > 90%", "error rate > 5%", "critical queue growing"],
    ),
    ChaosScenario(
        id="network-packet-loss",
        title="Partial network packet loss",
        domain="network",
        fault="packet_loss",
        parameters={"duration_minutes": 10, "packet_loss_percent": 20},
        hypothesis="Services should tolerate partial packet loss with bounded retries and no traffic storm.",
        signals=["retries", "timeouts", "TCP resets", "inter-service latency", "DNS errors"],
        guardrails=["do not affect all public traffic", "limit subnets/targets", "observability ready"],
        abort_conditions=["complete connectivity loss", "error rate > 10%", "NotReady nodes"],
    ),
    ChaosScenario(
        id="compute-pod-kill",
        title="Pod/node termination",
        domain="compute",
        fault="pod_kill",
        parameters={"replicas_terminated": 1, "interval_seconds": 60},
        hypothesis="Deployments should recover capacity and maintain availability through replicas.",
        signals=["restart count", "readiness", "HPA", "pending pods", "API latency"],
        guardrails=["at least 2 replicas", "configured PDB", "available cluster capacity"],
        abort_conditions=["available replicas < 1", "pods Pending > 5m", "service without endpoints"],
    ),
    ChaosScenario(
        id="messaging-backlog",
        title="Messaging backlog",
        domain="messaging",
        fault="queue_backlog",
        parameters={"duration_minutes": 20, "consumer_pause_percent": 50},
        hypothesis="Consumers should process the backlog without duplicate effects or broken idempotency.",
        signals=["queue depth", "oldest message age", "DLQ count", "idempotency conflicts"],
        guardrails=["active DLQ", "validated idempotency", "defined replay plan"],
        abort_conditions=["rapid DLQ growth", "oldest message age > SLO", "duplicate business effects"],
    ),
    ChaosScenario(
        id="security-secret-deny",
        title="Unavailable secrets or KMS",
        domain="security",
        fault="access_denied",
        parameters={"duration_minutes": 5, "deny_percent": 100},
        hypothesis="Services should fail closed, emit alerts, and never expose secrets or sensitive data.",
        signals=["AccessDenied", "KMS errors", "pod crashloop", "auth failures", "audit trail"],
        guardrails=["do not rotate real secrets", "controlled environment", "defined break-glass procedure"],
        abort_conditions=["secret exposure", "global authentication outage", "critical services without fallback"],
    ),
    ChaosScenario(
        id="transaction-processing-degradation",
        title="Transaction processing degradation",
        domain="transactional",
        fault="processing_degradation",
        parameters={"duration_minutes": 10, "operation_error_rate": 0.05},
        hypothesis="The workflow should preserve valid state transitions, idempotency, auditability, and recoverability during partial failures.",
        signals=["failed operations", "retry rate", "stuck workflows", "state inconsistencies", "audit gaps"],
        guardrails=["use synthetic data", "post-experiment state validation", "operation volume limits"],
        abort_conditions=["data corruption", "audit trail loss", "duplicate side effects"],
    ),
]


def choose_scenarios(node: dict[str, Any], count: int, requested: list[str] | None = None) -> list[ChaosScenario]:
    if requested:
        by_id = {scenario.id: scenario for scenario in SCENARIOS}
        missing = [scenario_id for scenario_id in requested if scenario_id not in by_id]
        if missing:
            raise ValueError(f"Unknown scenarios: {', '.join(missing)}")
        return [by_id[scenario_id] for scenario_id in requested][:count]

    tags = set(node.get("domain_tags", []))
    ranked = sorted(
        SCENARIOS,
        key=lambda scenario: (
            0 if scenario.domain in tags else 1,
            scenario.domain,
            scenario.id,
        ),
    )
    return ranked[:count]


def build_chaos_plan(
    graph: dict[str, Any],
    component: str,
    count: int,
    depth: int,
    requested_scenarios: list[str] | None = None,
) -> dict[str, Any]:
    node_id = resolve_node(graph, component)
    node = graph["nodes"][node_id]
    scenarios = choose_scenarios(node, count, requested_scenarios)
    impact_result = impact(graph, node_id, depth)
    failure_result = failure(graph, node_id, depth)

    experiments = []
    for index, scenario in enumerate(scenarios, start=1):
        affected = failure_result["affected"]
        experiments.append(
            {
                "number": index,
                "scenario": scenario.__dict__,
                "target": {
                    "node_id": node_id,
                    "file": node["file"],
                    "start_line": node["start_line"],
                    "end_line": node["end_line"],
                    "domain_tags": node.get("domain_tags", []),
                },
                "blast_radius": {
                    "affected_count": len(affected),
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
                        for item in impact_result["direct_dependencies"]
                    ],
                },
                "pre_checks": [
                    "crs init completed and memory updated",
                    "dashboards and alerts active",
                    "rollback or abort plan defined",
                    "experiment approved for the environment",
                ],
            }
        )

    return {
        "component": node_id,
        "component_metadata": node,
        "depth": depth,
        "scenario_count": len(experiments),
        "experiments": experiments,
        "impact": impact_result,
        "failure": failure_result,
    }


def render_chaos_markdown(plan: dict[str, Any]) -> str:
    lines = [
        f"# Chaos Plan - {plan['component']}",
        "",
        f"File: `{plan['component_metadata']['file']}:{plan['component_metadata']['start_line']}`",
        f"Tags: `{', '.join(plan['component_metadata'].get('domain_tags', [])) or 'no tags'}`",
        f"Impact depth: `{plan['depth']}`",
        "",
        "## Blast-radius summary",
        "",
        f"- Detected dependents: {len(plan['failure']['affected'])}",
        f"- Direct dependencies: {len(plan['impact']['direct_dependencies'])}",
        "",
    ]

    for experiment in plan["experiments"]:
        scenario = experiment["scenario"]
        lines.extend(
            [
                f"## Experiment {experiment['number']}: {scenario['title']}",
                "",
                f"- ID: `{scenario['id']}`",
                f"- Domain: `{scenario['domain']}`",
                f"- Fault: `{scenario['fault']}`",
                f"- Parameters: `{json.dumps(scenario['parameters'], ensure_ascii=False)}`",
                f"- Hypothesis: {scenario['hypothesis']}",
                "",
                "Signals to observe:",
            ]
        )
        lines.extend(f"- {signal}" for signal in scenario["signals"])
        lines.extend(["", "Guardrails:"])
        lines.extend(f"- {guardrail}" for guardrail in scenario["guardrails"])
        lines.extend(["", "Abort conditions:"])
        lines.extend(f"- {condition}" for condition in scenario["abort_conditions"])
        lines.extend(["", "Affected nodes:"])
        if experiment["blast_radius"]["affected_nodes"]:
            for affected in experiment["blast_radius"]["affected_nodes"]:
                lines.append(f"- depth {affected['depth']}: `{affected['node']}` via `{affected['relation']}`")
        else:
            lines.append("- No dependents were detected.")
        lines.append("")

    return "\n".join(lines)


def render_chaos_html(plan: dict[str, Any]) -> str:
    payload = json.dumps(plan, ensure_ascii=False).replace("</", "<\\/")
    title = html.escape(f"Chaos Plan - {plan['component']}")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    body {{ margin: 0; font-family: Segoe UI, Arial, sans-serif; background: #f6f8fb; color: #18202f; }}
    header {{ padding: 24px 32px; background: #0f766e; color: white; }}
    main {{ padding: 24px 32px; max-width: 1200px; margin: 0 auto; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; }}
    h2 {{ margin-top: 28px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }}
    .card {{ background: white; border: 1px solid #d8dee9; border-radius: 8px; padding: 16px; box-shadow: 0 8px 24px rgba(24,32,47,.08); }}
    .pill {{ display: inline-block; margin: 2px 4px 2px 0; padding: 3px 8px; border-radius: 999px; background: #e6f4f1; color: #0f766e; font-size: 12px; }}
    code {{ background: #edf2f7; padding: 2px 5px; border-radius: 4px; }}
    pre {{ white-space: pre-wrap; background: #101828; color: #e4e7ec; padding: 12px; border-radius: 8px; overflow: auto; }}
    ul {{ padding-left: 20px; }}
    .danger {{ color: #b42318; }}
  </style>
</head>
<body>
  <header>
    <h1>Chaos Plan</h1>
    <div>{html.escape(plan['component'])}</div>
  </header>
  <main id="app"></main>
  <script id="plan" type="application/json">{payload}</script>
  <script>
    const plan = JSON.parse(document.getElementById("plan").textContent);
    const app = document.getElementById("app");
    const esc = value => String(value).replace(/[&<>"']/g, c => ({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}}[c]));
    app.innerHTML = `
      <section class="card">
        <h2>Component</h2>
        <p><code>${{esc(plan.component)}}</code></p>
        <p>${{esc(plan.component_metadata.file)}}:${{plan.component_metadata.start_line}}</p>
        <p>${{(plan.component_metadata.domain_tags || []).map(t => `<span class="pill">${{esc(t)}}</span>`).join("")}}</p>
      </section>
      <h2>Experimentos</h2>
      <div class="grid">
        ${{plan.experiments.map(exp => `
          <article class="card">
            <h3>${{exp.number}}. ${{esc(exp.scenario.title)}}</h3>
            <p><code>${{esc(exp.scenario.id)}}</code> · ${{esc(exp.scenario.domain)}} · ${{esc(exp.scenario.fault)}}</p>
            <p>${{esc(exp.scenario.hypothesis)}}</p>
            <h4>Parametros</h4>
            <pre>${{esc(JSON.stringify(exp.scenario.parameters, null, 2))}}</pre>
            <h4>Blast radius</h4>
            <p class="danger">${{exp.blast_radius.affected_count}} affected nodes detected</p>
            <ul>${{exp.blast_radius.affected_nodes.map(n => `<li>depth ${{n.depth}}: <code>${{esc(n.node)}}</code> via ${{esc(n.relation)}}</li>`).join("") || "<li>No dependents were detected.</li>"}}</ul>
            <h4>Abort when</h4>
            <ul>${{exp.scenario.abort_conditions.map(x => `<li>${{esc(x)}}</li>`).join("")}}</ul>
          </article>
        `).join("")}}
      </div>
    `;
  </script>
</body>
</html>
"""
