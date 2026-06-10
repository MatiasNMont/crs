from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from .agent_installer import disable_agents, install_agents
from .agents import compact_agent_payload, render_agent_result, run_agents
from .benchmark import build_token_benchmark, save_benchmark
from .chaos import build_chaos_plan, render_chaos_html, render_chaos_markdown
from .indexer import build_graph
from .html import graph_to_html
from .memory import codeloom_package_status, resolve_backend
from .preflight import build_preflight_report, graph_to_payload, save_preflight_report
from .query import compact_context, failure, impact, resolve_node
from .render import render_failure, render_impact, render_postmortem, render_search, render_summary
from .storage import graph_path


def project_path(value: str) -> Path:
    path = Path(value).resolve()
    if not path.exists():
        raise argparse.ArgumentTypeError(f"Path does not exist: {value}")
    if not path.is_dir():
        raise argparse.ArgumentTypeError(f"Path is not a directory: {value}")
    return path


def cmd_init(args: argparse.Namespace) -> int:
    graph = build_graph(args.project)
    backend = resolve_backend(args.backend)
    messages = backend.save(args.project, graph, strict=args.strict_backend)
    print(f"CRS initialization completed with backend '{backend.name}'")
    for message in messages:
        print(f"- {message}")
    print(f"Nodes: {len(graph.nodes)}")
    print(f"Relationships: {len(graph.relations)}")
    agent_result = install_agents(args.project, target="base", force=False)
    print("Base agents installed:")
    for message in agent_result.messages:
        print(f"- {message}")
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    graph = resolve_backend(args.backend).load(args.project)
    print(render_summary(graph))
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    graph = resolve_backend(args.backend).load(args.project)
    print(render_search(graph, args.term))
    return 0


def cmd_impact(args: argparse.Namespace) -> int:
    graph = resolve_backend(args.backend).load(args.project)
    node_id = resolve_node(graph, args.node)
    result = impact(graph, node_id, args.depth)
    print(json.dumps(result, indent=2) if args.json else render_impact(result))
    return 0


def cmd_failure(args: argparse.Namespace) -> int:
    graph = resolve_backend(args.backend).load(args.project)
    node_id = resolve_node(graph, args.node)
    result = failure(graph, node_id, args.depth)
    print(json.dumps(result, indent=2) if args.json else render_failure(result))
    return 0


def cmd_postmortem(args: argparse.Namespace) -> int:
    graph = resolve_backend(args.backend).load(args.project)
    node_id = resolve_node(graph, args.node)
    document = render_postmortem(failure(graph, node_id, args.depth))
    if args.out:
        args.out.write_text(document, encoding="utf-8")
        print(f"Postmortem generated: {args.out}")
    else:
        print(document)
    return 0


def cmd_context(args: argparse.Namespace) -> int:
    graph = resolve_backend(args.backend).load(args.project)
    node_id = resolve_node(graph, args.node)
    result = compact_context(graph, node_id, args.depth, args.detail)
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


def cmd_graph_html(args: argparse.Namespace) -> int:
    graph = resolve_backend(args.backend).load(args.project)
    output = args.out or (args.project / ".crs" / "graph.html")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(graph_to_html(graph), encoding="utf-8")
    print(f"Graph HTML generated: {output}")
    return 0


def cmd_ask(args: argparse.Namespace) -> int:
    graph = resolve_backend(args.backend).load(args.project)
    result = run_agents(graph, args.question, args.depth, args.detail)
    if args.json:
        payload = result if args.full_payload else compact_agent_payload(result)
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(render_agent_result(result, include_context=args.show_context_summary))
    return 0


def cmd_backend_status(args: argparse.Namespace) -> int:
    codeloom_dir = args.project / ".crs" / "codeloom"
    manifest = codeloom_dir / "manifest.json"
    status = {
        "project": str(args.project),
        "default_backend": os.environ.get("CRS_MEMORY_BACKEND", "codeloom"),
        "codeloom_library": codeloom_package_status(),
        "codeloom_bin": os.environ.get("CRS_CODELOOM_BIN"),
        "codeloom_sync_command": os.environ.get("CRS_CODELOOM_SYNC_COMMAND"),
        "codeloom_export_exists": codeloom_dir.exists(),
        "codeloom_manifest": str(manifest) if manifest.exists() else None,
        "graph_json": str(graph_path(args.project)),
        "graph_json_exists": graph_path(args.project).exists(),
    }
    print(json.dumps(status, indent=2))
    return 0


def cmd_install_agent(args: argparse.Namespace) -> int:
    result = install_agents(args.project, target=args.target, force=args.force)
    for message in result.messages:
        print(message)
    print("Files:")
    for path in result.files:
        print(f"- {path}")
    return 0


def cmd_disable(args: argparse.Namespace) -> int:
    result = disable_agents(args.project, remove_memory=args.remove_memory)
    print("CRS disabled for agent sessions.")
    for message in result.messages:
        print(f"- {message}")
    return 0


def cmd_chaos(args: argparse.Namespace) -> int:
    graph = resolve_backend(args.backend).load(args.project)
    scenario_ids = args.scenario or None
    plan = build_chaos_plan(
        graph,
        component=args.component,
        count=args.count,
        depth=args.depth,
        requested_scenarios=scenario_ids,
    )

    output_dir = args.out or (args.project / ".crs" / "chaos")
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", plan["component"].replace("::", "__"))[:100]
    json_path = output_dir / f"{slug}.chaos.json"
    md_path = output_dir / f"{slug}.chaos.md"
    html_path = output_dir / f"{slug}.chaos.html"

    json_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_chaos_markdown(plan), encoding="utf-8")
    html_path.write_text(render_chaos_html(plan), encoding="utf-8")

    if args.json:
        print(json.dumps(plan, indent=2, ensure_ascii=False))
    else:
        print(f"Chaos plan generated for {plan['component']}")
        print(f"- JSON: {json_path}")
        print(f"- Markdown: {md_path}")
        print(f"- HTML: {html_path}")
        print(f"Scenarios: {plan['scenario_count']}")
    return 0


def cmd_preflight(args: argparse.Namespace) -> int:
    backend = resolve_backend(args.backend)
    old_graph = None
    try:
        old_graph = backend.load(args.project)
    except FileNotFoundError:
        old_graph = None

    new_graph_model = build_graph(args.project)
    new_graph = graph_to_payload(new_graph_model)
    report = build_preflight_report(old_graph, new_graph, max_affected=args.max_affected)
    paths = save_preflight_report(args.project, report, candidate_graph=new_graph)

    if args.update_memory:
        messages = backend.save(args.project, new_graph_model, strict=args.strict_backend)
    else:
        messages = ["CRS memory was not updated; use --update-memory to persist the new graph"]

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("CRS preflight completed")
        print(f"- JSON: {paths['latest_json']}")
        print(f"- Markdown: {paths['latest_markdown']}")
        print(f"- HTML: {paths['latest_html']}")
        print(f"- Prompt LLM: {paths['latest_prompt']}")
        if "candidate_graph" in paths:
            print(f"- Candidate snapshot: {paths['candidate_graph']}")
        print(f"- Added: {report['summary']['added']}")
        print(f"- Modified: {report['summary']['modified']}")
        print(f"- Removed: {report['summary']['removed']}")
        print(f"- Max blast radius: {report['summary']['max_node_affected']}")
        print(f"- Recommendation: {report['recommendation']}")
        for message in messages:
            print(f"- {message}")

    if report["summary"]["threshold_exceeded"]:
        return 2
    return 0


def cmd_benchmark_tokens(args: argparse.Namespace) -> int:
    graph = resolve_backend(args.backend).load(args.project)
    report = build_token_benchmark(args.project, graph, args.question, depth=args.depth, detail=args.detail)
    paths = save_benchmark(args.project, report)
    if args.json:
        printable = {key: value for key, value in report.items() if key != "prompts"}
        print(json.dumps(printable, indent=2, ensure_ascii=False))
    else:
        print("CRS token benchmark completed")
        print(f"- Without CRS: {report['raw']['estimated_tokens']} estimated tokens ({report['raw']['files_count']} files)")
        print(f"- With CRS: {report['crs']['estimated_tokens']} estimated tokens ({report['crs']['nodes_count']} nodes)")
        print(f"- Savings: {report['savings']['tokens_saved']} tokens")
        print(f"- Reduction: {report['savings']['reduction_percent']}%")
        print(f"- Raw/CRS ratio: {report['savings']['ratio_raw_to_crs']}x")
        print(f"- Markdown: {paths['latest_markdown']}")
        print(f"- HTML: {paths['latest_html']}")
        print(f"- JSON: {paths['latest_json']}")
    return 0


def add_backend_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--backend",
        choices=["json", "codeloom"],
        default=None,
        help="Memory backend. Default: CRS_MEMORY_BACKEND or codeloom.",
    )


def add_detail_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--detail",
        choices=["minimal", "summary", "full"],
        default="summary",
        help="Context detail level: minimal (structure only), "
        "summary (configuration for the focus node only, default), full (configuration for every node).",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crs",
        description="Code Relationship System: graph memory for Terraform projects.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Index a Terraform project and create .crs/graph.json.")
    init_parser.add_argument("project", type=project_path, help="Terraform project directory.")
    add_backend_args(init_parser)
    init_parser.add_argument("--strict-backend", action="store_true", help="Fail if external synchronization fails.")
    init_parser.set_defaults(func=cmd_init)

    summary_parser = subparsers.add_parser("summary", help="Show a graph summary.")
    summary_parser.add_argument("project", type=project_path)
    add_backend_args(summary_parser)
    summary_parser.set_defaults(func=cmd_summary)

    search_parser = subparsers.add_parser("search", help="Search nodes by name, file, or domain.")
    search_parser.add_argument("project", type=project_path)
    search_parser.add_argument("term")
    add_backend_args(search_parser)
    search_parser.set_defaults(func=cmd_search)

    impact_parser = subparsers.add_parser("impact", help="Answer: what is affected if component A changes?")
    impact_parser.add_argument("project", type=project_path)
    impact_parser.add_argument("node", help="Exact node ID or unambiguous fragment.")
    impact_parser.add_argument("--depth", type=int, default=3)
    impact_parser.add_argument("--json", action="store_true")
    add_backend_args(impact_parser)
    impact_parser.set_defaults(func=cmd_impact)

    failure_parser = subparsers.add_parser("failure", help="Answer: what can fail if component A goes down?")
    failure_parser.add_argument("project", type=project_path)
    failure_parser.add_argument("node", help="Exact node ID or unambiguous fragment.")
    failure_parser.add_argument("--depth", type=int, default=3)
    failure_parser.add_argument("--json", action="store_true")
    add_backend_args(failure_parser)
    failure_parser.set_defaults(func=cmd_failure)

    postmortem_parser = subparsers.add_parser("postmortem", help="Generate a graph-based postmortem draft.")
    postmortem_parser.add_argument("project", type=project_path)
    postmortem_parser.add_argument("node", help="Exact node ID or unambiguous fragment.")
    postmortem_parser.add_argument("--depth", type=int, default=3)
    postmortem_parser.add_argument("--out", type=Path)
    add_backend_args(postmortem_parser)
    postmortem_parser.set_defaults(func=cmd_postmortem)

    context_parser = subparsers.add_parser("context", help="Return bounded JSON context for an LLM.")
    context_parser.add_argument("project", type=project_path)
    context_parser.add_argument("node", help="Exact node ID or unambiguous fragment.")
    context_parser.add_argument("--depth", type=int, default=2)
    add_detail_arg(context_parser)
    add_backend_args(context_parser)
    context_parser.set_defaults(func=cmd_context)

    html_parser = subparsers.add_parser("graph-html", help="Generate an interactive HTML view of the CRS graph.")
    html_parser.add_argument("project", type=project_path)
    html_parser.add_argument("--out", type=Path, help="Output HTML file. Default: <project>/.crs/graph.html")
    add_backend_args(html_parser)
    html_parser.set_defaults(func=cmd_graph_html)

    ask_parser = subparsers.add_parser(
        "ask",
        help="CRS agent: interpret a question, run context, then impact/failure when applicable.",
    )
    ask_parser.add_argument("project", type=project_path)
    ask_parser.add_argument("question")
    ask_parser.add_argument("--depth", type=int, default=3)
    ask_parser.add_argument("--json", action="store_true")
    ask_parser.add_argument("--full-payload", action="store_true", help="Emit the complete unpruned payload (debug).")
    ask_parser.add_argument("--show-context-summary", action="store_true")
    add_detail_arg(ask_parser)
    add_backend_args(ask_parser)
    ask_parser.set_defaults(func=cmd_ask)

    agent_parser = subparsers.add_parser("agent", help="Alias for 'ask'.")
    agent_parser.add_argument("project", type=project_path)
    agent_parser.add_argument("question")
    agent_parser.add_argument("--depth", type=int, default=3)
    agent_parser.add_argument("--json", action="store_true")
    agent_parser.add_argument("--full-payload", action="store_true", help="Emit the complete unpruned payload (debug).")
    agent_parser.add_argument("--show-context-summary", action="store_true")
    add_detail_arg(agent_parser)
    add_backend_args(agent_parser)
    agent_parser.set_defaults(func=cmd_ask)

    backend_parser = subparsers.add_parser("backend-status", help="Show CRS memory backend status.")
    backend_parser.add_argument("project", type=project_path)
    backend_parser.set_defaults(func=cmd_backend_status)

    install_agent_parser = subparsers.add_parser(
        "install-agent",
        help="Install or update local CRS rules for supported coding agents.",
    )
    install_agent_parser.add_argument("project", type=project_path)
    install_agent_parser.add_argument(
        "--target",
        action="append",
        choices=["base", "all", "codex", "claude", "cursor", "windsurf"],
        default=None,
        help="Agent target. Repeat to install multiple targets. Default: base (Codex and Claude).",
    )
    install_agent_parser.add_argument("--force", action="store_true", help="Overwrite existing helper scripts.")
    install_agent_parser.set_defaults(func=cmd_install_agent)

    disable_parser = subparsers.add_parser(
        "disable",
        help="Remove CRS agent integrations for a no-CRS comparison.",
    )
    disable_parser.add_argument("project", type=project_path)
    disable_parser.add_argument(
        "--remove-memory",
        action="store_true",
        help="Also delete .crs graph memory and generated reports.",
    )
    disable_parser.set_defaults(func=cmd_disable)

    chaos_parser = subparsers.add_parser(
        "chaos",
        help="Generate Chaos Engineering scenarios and impact graphs for a component.",
    )
    chaos_parser.add_argument("project", type=project_path)
    chaos_parser.add_argument("component", help="Exact component ID or unambiguous fragment.")
    chaos_parser.add_argument("--count", type=int, default=3, help="Number of scenarios to generate.")
    chaos_parser.add_argument("--depth", type=int, default=3, help="Blast-radius traversal depth.")
    chaos_parser.add_argument(
        "--scenario",
        action="append",
        help="Specific scenario ID. Repeatable. When omitted, CRS selects scenarios by domain.",
    )
    chaos_parser.add_argument("--out", type=Path, help="Output directory. Default: <project>/.crs/chaos")
    chaos_parser.add_argument("--json", action="store_true")
    add_backend_args(chaos_parser)
    chaos_parser.set_defaults(func=cmd_chaos)

    preflight_parser = subparsers.add_parser(
        "preflight",
        help="Regenerate the graph, compare it with previous memory, and validate impact before Terraform.",
    )
    preflight_parser.add_argument("project", type=project_path)
    preflight_parser.add_argument("--max-affected", type=int, help="Fail when a changed node affects more than this threshold.")
    preflight_parser.add_argument("--update-memory", action="store_true", help="Persist the new graph after preflight.")
    preflight_parser.add_argument("--strict-backend", action="store_true", help="Fail if external synchronization fails.")
    preflight_parser.add_argument("--json", action="store_true")
    add_backend_args(preflight_parser)
    preflight_parser.set_defaults(func=cmd_preflight)

    benchmark_parser = subparsers.add_parser(
        "benchmark-tokens",
        help="Compare estimated tokens for full Terraform reads versus CRS context.",
    )
    benchmark_parser.add_argument("project", type=project_path)
    benchmark_parser.add_argument("question")
    benchmark_parser.add_argument("--depth", type=int, default=3)
    benchmark_parser.add_argument("--json", action="store_true")
    add_detail_arg(benchmark_parser)
    add_backend_args(benchmark_parser)
    benchmark_parser.set_defaults(func=cmd_benchmark_tokens)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        print(f"crs error: {exc}", file=sys.stderr)
        return 1
