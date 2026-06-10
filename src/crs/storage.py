from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import Graph


def memory_dir(project_root: Path) -> Path:
    return project_root / ".crs"


def graph_path(project_root: Path) -> Path:
    return memory_dir(project_root) / "graph.json"


def history_dir(project_root: Path) -> Path:
    return memory_dir(project_root) / "history"


def safe_node_filename(node_id: str) -> str:
    # Add a hash suffix to prevent collisions between node IDs that sanitize to
    # the same filename, and truncate to respect Windows path limits.
    digest = hashlib.sha256(node_id.encode("utf-8")).hexdigest()[:8]
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", node_id)[:100]
    return f"{safe}-{digest}.json"


def save_graph(project_root: Path, graph: Graph) -> None:
    base = memory_dir(project_root)
    nodes_dir = base / "nodes"
    nodes_dir.mkdir(parents=True, exist_ok=True)
    history_dir(project_root).mkdir(parents=True, exist_ok=True)

    payload = graph.to_dict()
    current_graph = graph_path(project_root)
    if current_graph.exists():
        snapshot_existing_graph(project_root, current_graph)

    graph_text = json.dumps(payload, indent=2, sort_keys=True)
    current_graph.write_text(graph_text, encoding="utf-8")
    write_new_graph_snapshot(project_root, graph_text)

    incoming = payload["incoming"]
    outgoing = payload["outgoing"]
    for node_id, node in payload["nodes"].items():
        node_payload = {
            **node,
            "incoming": incoming.get(node_id, []),
            "outgoing": outgoing.get(node_id, []),
        }
        (nodes_dir / safe_node_filename(node_id)).write_text(
            json.dumps(node_payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )


def load_graph(project_root: Path) -> dict[str, Any]:
    path = graph_path(project_root)
    if not path.exists():
        raise FileNotFoundError(f"CRS memory does not exist at {path}. Run: crs init {project_root}")
    return json.loads(path.read_text(encoding="utf-8"))


def snapshot_existing_graph(project_root: Path, current_graph: Path) -> Path:
    payload = json.loads(current_graph.read_text(encoding="utf-8"))
    generated_at = payload.get("generated_at") or datetime.now(timezone.utc).isoformat()
    stamp = safe_stamp(generated_at)
    target = history_dir(project_root) / f"graph-{stamp}.json"
    if not target.exists():
        shutil.copy2(current_graph, target)
    return target


def write_new_graph_snapshot(project_root: Path, graph_text: str) -> Path:
    return write_graph_snapshot(project_root, graph_text, prefix="graph")


def write_graph_snapshot(project_root: Path, graph_text: str, prefix: str = "graph") -> Path:
    history_dir(project_root).mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = history_dir(project_root) / f"{prefix}-{stamp}.json"
    counter = 1
    while target.exists():
        target = history_dir(project_root) / f"{prefix}-{stamp}-{counter}.json"
        counter += 1
    target.write_text(graph_text, encoding="utf-8")
    return target


def safe_stamp(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z]+", "", value.replace("+00:00", "Z"))[:32] or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
