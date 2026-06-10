from __future__ import annotations

import json
import os
import shlex
import subprocess
from importlib import import_module
from importlib.metadata import PackageNotFoundError, version
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from .models import Graph
from .storage import graph_path, load_graph as load_json_graph, save_graph as save_json_graph


class MemoryBackend(ABC):
    name: str

    @abstractmethod
    def save(self, project_root: Path, graph: Graph, strict: bool = False) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def load(self, project_root: Path) -> dict[str, Any]:
        raise NotImplementedError


class JsonMemoryBackend(MemoryBackend):
    name = "json"

    def save(self, project_root: Path, graph: Graph, strict: bool = False) -> list[str]:
        save_json_graph(project_root, graph)
        return [f"json: {graph_path(project_root)}"]

    def load(self, project_root: Path) -> dict[str, Any]:
        return load_json_graph(project_root)


class CodeLoomMemoryBackend(MemoryBackend):
    name = "codeloom"

    def save(self, project_root: Path, graph: Graph, strict: bool = False) -> list[str]:
        messages = []
        save_json_graph(project_root, graph)
        messages.append(f"json: {graph_path(project_root)}")

        payload = graph.to_dict()
        codeloom_dir = project_root / ".crs" / "codeloom"
        codeloom_dir.mkdir(parents=True, exist_ok=True)

        manifest = {
            "backend": "codeloom",
            "schema": "crs-codeloom-v1",
            "project_root": payload["project_root"],
            "generated_at": payload["generated_at"],
            "node_count": payload["node_count"],
            "relation_count": payload["relation_count"],
            "graph_json": str(graph_path(project_root)),
            "nodes_jsonl": str(codeloom_dir / "nodes.jsonl"),
            "relations_jsonl": str(codeloom_dir / "relations.jsonl"),
        }

        (codeloom_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        write_jsonl(codeloom_dir / "nodes.jsonl", payload["nodes"].values())
        write_jsonl(codeloom_dir / "relations.jsonl", payload["relations"])
        write_context_index(codeloom_dir / "context-index.json", payload)
        messages.append(f"codeloom export: {codeloom_dir}")

        sync_message = self.sync_python_library(project_root, graph_path(project_root), codeloom_dir, strict)
        if sync_message:
            messages.append(sync_message)

        sync_message = self.sync_external(project_root, graph_path(project_root), codeloom_dir, strict)
        if sync_message:
            messages.append(sync_message)
        return messages

    def load(self, project_root: Path) -> dict[str, Any]:
        return load_json_graph(project_root)

    def sync_python_library(self, project_root: Path, graph_file: Path, codeloom_dir: Path, strict: bool) -> str | None:
        try:
            codeloom = import_module("codeloom")
        except ImportError as exc:
            if strict:
                raise RuntimeError("The 'codeloom' Python library is not installed.") from exc
            return "codeloom library: unavailable; reinstall CRS because CodeLoom is a required dependency"

        kwargs = {
            "project": str(project_root),
            "project_root": str(project_root),
            "graph": str(graph_file),
            "graph_path": str(graph_file),
            "output": str(codeloom_dir),
            "out": str(codeloom_dir),
        }

        try:
            pipeline = import_module("codeloom.core.pipeline")
            run_pipeline = getattr(pipeline, "run_pipeline", None)
            if run_pipeline:
                output_dir = codeloom_dir.parent / "codeloom-native"
                run_pipeline(
                    source_dir=project_root,
                    output_dir=output_dir,
                    embed=os.environ.get("CRS_CODELOOM_EMBED", "0") == "1",
                    incremental=True,
                    lang=os.environ.get("CRS_CODELOOM_LANG", "auto"),
                    git=os.environ.get("CRS_CODELOOM_GIT", "0") == "1",
                )
                return f"codeloom library: run_pipeline ok ({output_dir})"

            if hasattr(codeloom, "ingest"):
                call_flexible(codeloom.ingest, kwargs)
                return "codeloom library: ingest ok"

            if hasattr(codeloom, "index"):
                call_flexible(codeloom.index, kwargs)
                return "codeloom library: index ok"

            if hasattr(codeloom, "CodeLoom"):
                instance = codeloom.CodeLoom()
                for method_name in ["ingest", "index", "import_graph", "load_graph"]:
                    method = getattr(instance, method_name, None)
                    if method:
                        call_flexible(method, kwargs)
                        return f"codeloom library: CodeLoom.{method_name} ok"

            if hasattr(codeloom, "Client"):
                client = codeloom.Client()
                for method_name in ["ingest", "index", "import_graph", "load_graph"]:
                    method = getattr(client, method_name, None)
                    if method:
                        call_flexible(method, kwargs)
                        return f"codeloom library: Client.{method_name} ok"
        except Exception as exc:
            if strict:
                raise RuntimeError(f"The 'codeloom' Python library failed during synchronization: {exc}") from exc
            return f"codeloom library: non-blocking failure ({exc})"

        message = "codeloom library: imported, but no compatible run_pipeline/ingest/index/CodeLoom/Client API was found"
        if strict:
            raise RuntimeError(message)
        return message

    def sync_external(self, project_root: Path, graph_file: Path, codeloom_dir: Path, strict: bool) -> str | None:
        command_template = os.environ.get("CRS_CODELOOM_SYNC_COMMAND")
        codeloom_bin = os.environ.get("CRS_CODELOOM_BIN")

        if command_template:
            command = render_command_template(
                command_template,
                {
                    "project": str(project_root),
                    "graph": str(graph_file),
                    "codeloom_dir": str(codeloom_dir),
                },
            )
            return run_external(command, strict)

        if codeloom_bin:
            command = [
                codeloom_bin,
                "ingest",
                "--project",
                str(project_root),
                "--graph",
                str(graph_file),
                "--out",
                str(codeloom_dir),
            ]
            return run_external(command, strict)

        return "codeloom synchronization: not configured; use CRS_CODELOOM_BIN or CRS_CODELOOM_SYNC_COMMAND"


def write_jsonl(path: Path, items: Any) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for item in items:
            handle.write(json.dumps(item, sort_keys=True, ensure_ascii=False))
            handle.write("\n")


def write_context_index(path: Path, payload: dict[str, Any]) -> None:
    index = {}
    for node_id, node in payload["nodes"].items():
        index[node_id] = {
            "file": node["file"],
            "start_line": node["start_line"],
            "end_line": node["end_line"],
            "kind": node["kind"],
            "domain_tags": node.get("domain_tags", []),
            "incoming_count": len(payload["incoming"].get(node_id, [])),
            "outgoing_count": len(payload["outgoing"].get(node_id, [])),
        }
    path.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")


def render_command_template(template: str, values: dict[str, str]) -> list[str]:
    """Convert the template into an argument list without invoking a shell.

    Only the exact {project}, {graph}, and {codeloom_dir} placeholders are
    replaced after tokenization, so paths containing spaces or metacharacters
    cannot alter the command.
    """
    try:
        tokens = shlex.split(template, posix=(os.name != "nt"))
    except ValueError as exc:
        raise ValueError(f"Invalid CRS_CODELOOM_SYNC_COMMAND: {exc}") from exc
    if os.name == "nt":
        tokens = [token.strip('"') for token in tokens]

    rendered = []
    for token in tokens:
        for key, value in values.items():
            token = token.replace("{" + key + "}", value)
        rendered.append(token)
    if not rendered:
        raise ValueError("CRS_CODELOOM_SYNC_COMMAND is empty")
    return rendered


def run_external(command: list[str], strict: bool, timeout_seconds: int = 600) -> str:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            shell=False,
            timeout=timeout_seconds,
        )
    except FileNotFoundError as exc:
        if strict:
            raise RuntimeError(f"CodeLoom is unavailable: {exc}") from exc
        return f"codeloom synchronization: skipped ({exc})"
    except subprocess.TimeoutExpired as exc:
        if strict:
            raise RuntimeError(f"CodeLoom synchronization exceeded the {timeout_seconds}s timeout") from exc
        return f"codeloom synchronization: skipped after timeout ({timeout_seconds}s)"

    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or f"exit {completed.returncode}"
        if strict:
            raise RuntimeError(f"CodeLoom synchronization failed: {message}")
        return f"codeloom synchronization: non-blocking failure ({message})"
    return "codeloom sync: ok"


def resolve_backend(name: str | None) -> MemoryBackend:
    selected = (name or os.environ.get("CRS_MEMORY_BACKEND") or "codeloom").lower()
    if selected == "json":
        return JsonMemoryBackend()
    if selected == "codeloom":
        return CodeLoomMemoryBackend()
    raise ValueError(f"Unsupported memory backend: {selected}")


def codeloom_package_status() -> dict[str, Any]:
    try:
        module = import_module("codeloom")
        available = True
        error = None
    except ImportError as exc:
        module = None
        available = False
        error = str(exc)

    try:
        package_version = version("codeloom")
    except PackageNotFoundError:
        package_version = None

    return {
        "available": available,
        "version": package_version,
        "module_file": getattr(module, "__file__", None) if module else None,
        "error": error,
    }


def call_flexible(function: Any, kwargs: dict[str, str]) -> Any:
    attempts = [
        {"project": kwargs["project"], "graph": kwargs["graph"], "output": kwargs["output"]},
        {"project_root": kwargs["project_root"], "graph_path": kwargs["graph_path"], "out": kwargs["out"]},
        {"project": kwargs["project"], "graph_path": kwargs["graph_path"], "out": kwargs["out"]},
    ]
    last_error: Exception | None = None
    for attempt in attempts:
        try:
            return function(**attempt)
        except TypeError as exc:
            last_error = exc
    try:
        return function(kwargs["project"], kwargs["graph"], kwargs["output"])
    except TypeError as exc:
        raise last_error or exc
