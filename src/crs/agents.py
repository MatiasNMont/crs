from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .query import compact_context, failure, impact
from .render import render_failure, render_impact


CHANGE_PATTERNS = [
    r"\b(cambia|cambio|cambiar|modifica|modifico|modificar|actualiza|actualizo|actualizar|upgrade|subir|bajar)\b",
    r"\b(elimina|elimino|eliminar|borra|borro|borrar|quita|quito|quitar|destruye|destruir)\b",
    r"\b(change|changed|modify|modified|update|updated|upgrade|downgrade)\b",
    r"\b(delete|deleted|remove|removed|destroy|destroyed|drop)\b",
]

FAILURE_PATTERNS = [
    r"\b(cae|caida|cae|falla|fallo|rompe|indisponible|down|outage)\b",
    r"\b(fail|fails|failure|crash|crashes|unavailable|incident)\b",
]

STOPWORDS = {
    "que",
    "pasa",
    "si",
    "se",
    "el",
    "la",
    "los",
    "las",
    "un",
    "una",
    "de",
    "del",
    "en",
    "con",
    "por",
    "para",
    "puede",
    "tener",
    "problematica",
    "problematicas",
    "impacto",
    "cambia",
    "cambio",
    "cambiar",
    "cae",
    "falla",
    "fallo",
    "what",
    "happens",
    "if",
    "the",
    "is",
    "changed",
    "change",
    "fails",
    "failure",
}

KIND_WEIGHTS = {
    "resource": 40,
    "module": 28,
    "data": 20,
    "output": 12,
    "variable": 8,
    "locals": 4,
}

RESOURCE_HINT_WEIGHTS = {
    "aws_rds_cluster": 35,
    "aws_eks_cluster": 35,
    "aws_elasticache_replication_group": 30,
    "aws_dynamodb_table": 30,
    "aws_s3_bucket": 25,
    "aws_cloudwatch_event_bus": 25,
    "aws_sqs_queue": 25,
    "aws_vpc": 25,
    "kubernetes_deployment": 25,
    "kubernetes_service": 20,
}


@dataclass
class AgentDecision:
    question: str
    intent: str
    node_id: str
    confidence: float
    matched_terms: list[str]


def detect_intent(question: str) -> str:
    lowered = question.lower()
    if any(re.search(pattern, lowered) for pattern in FAILURE_PATTERNS):
        return "failure"
    if any(re.search(pattern, lowered) for pattern in CHANGE_PATTERNS):
        return "impact"
    return "context"


def question_terms(question: str) -> list[str]:
    normalized = re.sub(r"[^a-zA-Z0-9_.:/-]+", " ", question.lower())
    terms = []
    for term in normalized.split():
        term = term.strip("._:-/")
        if len(term) < 3 or term in STOPWORDS:
            continue
        terms.append(term)
    return sorted(set(terms), key=lambda value: (-len(value), value))


def score_node(node_id: str, node: dict[str, Any], terms: list[str]) -> tuple[int, list[str]]:
    haystack = "\n".join(
        [
            node_id,
            node.get("file", ""),
            " ".join(node.get("domain_tags", [])),
            node.get("config", ""),
        ]
    ).lower()
    score = KIND_WEIGHTS.get(node.get("kind", ""), 0)
    matched: list[str] = []

    terraform_address = node.get("attributes", {}).get("terraform_address", node_id).lower()
    for prefix, weight in RESOURCE_HINT_WEIGHTS.items():
        if terraform_address.startswith(prefix):
            score += weight

    for term in terms:
        if term not in haystack:
            continue
        matched.append(term)
        if term in node_id.lower():
            score += 45
        elif term in node.get("file", "").lower():
            score += 20
        else:
            score += 10

    if "aurora" in terms and "aws_rds_cluster" in terraform_address:
        score += 80
    if "eks" in terms and "aws_eks_cluster" in terraform_address:
        score += 80
    if "redis" in terms and "elasticache" in terraform_address:
        score += 70
    if "payment" in terms and "payment" in node_id.lower():
        score += 35
    if "ledger" in terms and "ledger" in node_id.lower():
        score += 35

    return score, matched


def resolve_question_node(graph: dict[str, Any], question: str) -> tuple[str, float, list[str]]:
    terms = question_terms(question)
    if not terms:
        raise ValueError("Could not detect a component in the question.")

    ranked: list[tuple[int, str, list[str]]] = []
    for node_id, node in graph["nodes"].items():
        score, matched = score_node(node_id, node, terms)
        if matched:
            ranked.append((score, node_id, matched))

    if not ranked:
        raise ValueError(f"No nodes were found for: {', '.join(terms)}")

    ranked.sort(key=lambda item: (-item[0], item[1]))
    best_score, best_node, matched = ranked[0]
    second_score = ranked[1][0] if len(ranked) > 1 else 0
    confidence = min(0.99, max(0.1, (best_score - second_score + best_score) / max(best_score * 2, 1)))
    return best_node, confidence, matched


def decide(graph: dict[str, Any], question: str) -> AgentDecision:
    node_id, confidence, matched = resolve_question_node(graph, question)
    return AgentDecision(
        question=question,
        intent=detect_intent(question),
        node_id=node_id,
        confidence=confidence,
        matched_terms=matched,
    )


def run_agents(graph: dict[str, Any], question: str, depth: int = 3, detail: str = "summary") -> dict[str, Any]:
    decision = decide(graph, question)
    context_payload = compact_context(graph, decision.node_id, min(depth, 2), detail)

    if decision.intent == "failure":
        command_payload = failure(graph, decision.node_id, depth)
        rendered = render_failure(command_payload)
        command = "failure"
    elif decision.intent == "impact":
        command_payload = impact(graph, decision.node_id, depth)
        rendered = render_impact(command_payload)
        command = "impact"
    else:
        command_payload = context_payload
        rendered = "The question does not appear to concern impact or failure. CRS context was generated for the LLM."
        command = "context"

    return {
        "decision": {
            "question": decision.question,
            "intent": decision.intent,
            "node_id": decision.node_id,
            "confidence": round(decision.confidence, 3),
            "matched_terms": decision.matched_terms,
        },
        "agents": [
            {
                "name": "context-agent",
                "action": "crs context",
                "status": "executed",
                "purpose": "Reduce LLM context to related nodes.",
            },
            {
                "name": f"{command}-agent",
                "action": f"crs {command}",
                "status": "executed",
                "purpose": "Answer the detected intent using the CRS graph.",
            },
        ],
        "context": context_payload,
        "command": command,
        "result": command_payload,
        "rendered": rendered,
    }


def compact_walk_item(item: dict[str, Any]) -> dict[str, Any]:
    """Compact an affected/dependent node to the minimum useful shape.

    file and domain_tags are omitted because they already exist in context.nodes;
    source/target are omitted because the parent-to-node edge is implicit.
    """
    relation = item.get("relation", {})
    return {
        "node": item.get("node"),
        "depth": item.get("depth"),
        "via": relation.get("kind"),
        "evidence": relation.get("evidence"),
    }


def compact_agent_payload(result: dict[str, Any]) -> dict[str, Any]:
    """Build a pruned payload for the LLM.

    Remove agent metadata, rendered text, and the duplicate component node.
    compact_context has already shaped context according to --detail.
    """
    command_result = result.get("result", {})
    compact_result: dict[str, Any] = {"node": command_result.get("node")}
    if "direct_dependencies" in command_result:
        compact_result["direct_dependencies"] = [compact_walk_item(item) for item in command_result["direct_dependencies"]]
    if "affected" in command_result:
        compact_result["affected"] = [compact_walk_item(item) for item in command_result["affected"]]
    if "risks" in command_result:
        compact_result["risks"] = command_result["risks"]

    return {
        "decision": result["decision"],
        "command": result.get("command"),
        "context": result.get("context", {}),
        "result": compact_result,
    }


def render_agent_result(result: dict[str, Any], include_context: bool = False) -> str:
    decision = result["decision"]
    lines = [
        "CRS Agent",
        f"- Question: {decision['question']}",
        f"- Detected intent: {decision['intent']}",
        f"- Selected node: {decision['node_id']}",
        f"- Heuristic confidence: {decision['confidence']}",
        f"- Matched terms: {', '.join(decision['matched_terms']) or 'n/a'}",
        "",
        "Executed agents:",
    ]
    for agent in result["agents"]:
        lines.append(f"- {agent['name']}: {agent['action']} ({agent['status']})")
    lines.extend(["", result["rendered"]])

    if include_context:
        related_count = len(result["context"].get("nodes", {}))
        relation_count = len(result["context"].get("relations", []))
        lines.extend(
            [
                "",
                "LLM context:",
                f"- Related nodes sent: {related_count}",
                f"- Relationships sent: {relation_count}",
                "- Use `--json` to inspect the complete payload sent to the LLM.",
            ]
        )

    return "\n".join(lines)
