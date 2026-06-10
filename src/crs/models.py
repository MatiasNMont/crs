from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class Relation:
    source: str
    target: str
    kind: str
    evidence: str
    file: str | None = None
    line: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "kind": self.kind,
            "evidence": self.evidence,
            "file": self.file,
            "line": self.line,
        }


@dataclass
class Node:
    id: str
    kind: str
    labels: list[str]
    file: str
    start_line: int
    end_line: int
    config: str
    attributes: dict[str, str] = field(default_factory=dict)
    references: list[str] = field(default_factory=list)
    domain_tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "labels": self.labels,
            "file": self.file,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "config": self.config,
            "attributes": self.attributes,
            "references": sorted(set(self.references)),
            "domain_tags": sorted(set(self.domain_tags)),
        }


@dataclass
class Graph:
    project_root: str
    generated_at: str
    nodes: dict[str, Node] = field(default_factory=dict)
    relations: list[Relation] = field(default_factory=list)

    @classmethod
    def empty(cls, project_root: Path) -> "Graph":
        return cls(
            project_root=str(project_root.resolve()),
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def to_dict(self) -> dict[str, Any]:
        incoming: dict[str, list[dict[str, Any]]] = {node_id: [] for node_id in self.nodes}
        outgoing: dict[str, list[dict[str, Any]]] = {node_id: [] for node_id in self.nodes}

        for relation in self.relations:
            relation_dict = relation.to_dict()
            outgoing.setdefault(relation.source, []).append(relation_dict)
            incoming.setdefault(relation.target, []).append(relation_dict)

        return {
            "schema_version": 1,
            "project_root": self.project_root,
            "generated_at": self.generated_at,
            "node_count": len(self.nodes),
            "relation_count": len(self.relations),
            "nodes": {node_id: node.to_dict() for node_id, node in sorted(self.nodes.items())},
            "relations": [relation.to_dict() for relation in self.relations],
            "incoming": incoming,
            "outgoing": outgoing,
        }
