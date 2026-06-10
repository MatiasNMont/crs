from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .agents import compact_agent_payload, run_agents
from .hcl_scanner import redact_sensitive
from .indexer import discover_tf_files


def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


def collect_tf_context(project_root: Path) -> tuple[str, list[str]]:
    root = project_root.resolve()
    chunks = []
    files = []
    for path in discover_tf_files(root):
        rel = path.relative_to(root)
        files.append(str(rel))
        content = redact_sensitive(path.read_text(encoding="utf-8", errors="replace"))
        chunks.append(f"# FILE: {rel}\n{content}")
    return "\n\n".join(chunks), files


def build_raw_prompt(question: str, project_root: Path) -> tuple[str, list[str]]:
    context, files = collect_tf_context(project_root)
    prompt = f"""User question:
{question}

Complete Terraform repository context:

{context}

Instructions:
Analyze the impact of the change by reading the complete context.
"""
    return prompt, files


def build_crs_prompt(question: str, graph: dict[str, Any], depth: int, detail: str = "summary") -> tuple[str, dict[str, Any]]:
    result = run_agents(graph, question, depth, detail)
    payload = compact_agent_payload(result)
    # Stable order for prompt caching: the graph context comes first and the
    # variable question comes last.
    prompt = f"""CRS context (structural memory; stable across questions about the same graph):
{json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)}

Instructions:
Use CRS memory first. Do not grep the complete repository.
If you need a node's full configuration, request it by file:lines.

User question:
{question}
"""
    return prompt, payload


def build_token_benchmark(project_root: Path, graph: dict[str, Any], question: str, depth: int = 3, detail: str = "summary") -> dict[str, Any]:
    raw_prompt, raw_files = build_raw_prompt(question, project_root)
    crs_prompt, crs_payload = build_crs_prompt(question, graph, depth, detail)

    raw_chars = len(raw_prompt)
    crs_chars = len(crs_prompt)
    raw_tokens = estimate_tokens(raw_prompt)
    crs_tokens = estimate_tokens(crs_prompt)
    saved_tokens = raw_tokens - crs_tokens
    reduction = round((saved_tokens / raw_tokens) * 100, 2) if raw_tokens else 0.0

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_root": str(project_root),
        "question": question,
        "methodology": {
            "token_estimate": "ceil(characters / 4)",
            "raw_mode": "all Terraform .tf files excluding .git/.crs/.terraform",
            "crs_mode": "crs ask JSON payload with decision/context/result",
        },
        "raw": {
            "files_count": len(raw_files),
            "files": raw_files,
            "characters": raw_chars,
            "estimated_tokens": raw_tokens,
        },
        "crs": {
            "nodes_count": len(crs_payload["context"].get("nodes", {})),
            "relations_count": len(crs_payload["context"].get("relations", [])),
            "characters": crs_chars,
            "estimated_tokens": crs_tokens,
            "decision": crs_payload["decision"],
            "detail": crs_payload["context"].get("detail", detail),
            "mode": "compact",
        },
        "savings": {
            "tokens_saved": saved_tokens,
            "characters_saved": raw_chars - crs_chars,
            "reduction_percent": reduction,
            "ratio_raw_to_crs": round(raw_tokens / crs_tokens, 2) if crs_tokens else None,
        },
        "prompts": {
            "raw": raw_prompt,
            "crs": crs_prompt,
        },
    }


def render_benchmark_markdown(report: dict[str, Any]) -> str:
    return f"""# CRS Token Benchmark

Question:

```text
{report['question']}
```

## Result

| Method | Estimated tokens | Characters | Scope |
| --- | ---: | ---: | --- |
| Without CRS | {report['raw']['estimated_tokens']} | {report['raw']['characters']} | {report['raw']['files_count']} Terraform files |
| With CRS | {report['crs']['estimated_tokens']} | {report['crs']['characters']} | {report['crs']['nodes_count']} nodes / {report['crs']['relations_count']} relationships |

## Savings

- Tokens saved: `{report['savings']['tokens_saved']}`
- Reduction: `{report['savings']['reduction_percent']}%`
- Raw/CRS ratio: `{report['savings']['ratio_raw_to_crs']}x`

## CRS decision

```json
{json.dumps(report['crs']['decision'], indent=2, ensure_ascii=False)}
```

## Methodology

- Estimate: `{report['methodology']['token_estimate']}`
- Without CRS: `{report['methodology']['raw_mode']}`
- With CRS: `{report['methodology']['crs_mode']}`

## Files included without CRS

{chr(10).join(f"- `{file}`" for file in report['raw']['files'])}
"""


def render_benchmark_html(report: dict[str, Any]) -> str:
    payload = json.dumps(report, ensure_ascii=False).replace("</", "<\\/")
    title = html.escape("CRS Token Benchmark")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    body {{ margin: 0; font-family: Segoe UI, Arial, sans-serif; background: #f7f8fb; color: #18202f; }}
    header {{ background: #0f766e; color: white; padding: 24px 32px; }}
    main {{ max-width: 1100px; margin: 0 auto; padding: 24px 32px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; }}
    .card {{ background: white; border: 1px solid #d8dee9; border-radius: 8px; padding: 16px; box-shadow: 0 8px 24px rgba(24,32,47,.08); }}
    strong {{ font-size: 28px; }}
    code, pre {{ background: #edf2f7; border-radius: 6px; }}
    code {{ padding: 2px 5px; }}
    pre {{ padding: 12px; overflow: auto; }}
  </style>
</head>
<body>
  <header><h1>CRS Token Benchmark</h1><div>{html.escape(report['question'])}</div></header>
  <main id="app"></main>
  <script id="data" type="application/json">{payload}</script>
  <script>
    const r = JSON.parse(document.getElementById("data").textContent);
    const esc = v => String(v).replace(/[&<>"']/g, c => ({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}}[c]));
    document.getElementById("app").innerHTML = `
      <section class="grid">
        <div class="card"><h3>Without CRS</h3><strong>${{r.raw.estimated_tokens}}</strong><p>estimated tokens</p><p>${{r.raw.files_count}} files</p></div>
        <div class="card"><h3>With CRS</h3><strong>${{r.crs.estimated_tokens}}</strong><p>estimated tokens</p><p>${{r.crs.nodes_count}} nodes</p></div>
        <div class="card"><h3>Savings</h3><strong>${{r.savings.reduction_percent}}%</strong><p>${{r.savings.tokens_saved}} tokens</p></div>
        <div class="card"><h3>Ratio</h3><strong>${{r.savings.ratio_raw_to_crs}}x</strong><p>raw / CRS</p></div>
      </section>
      <section class="card"><h2>CRS decision</h2><pre>${{esc(JSON.stringify(r.crs.decision, null, 2))}}</pre></section>
      <section class="card"><h2>Methodology</h2><p>${{esc(r.methodology.token_estimate)}}</p></section>
    `;
  </script>
</body>
</html>
"""


def save_benchmark(project_root: Path, report: dict[str, Any]) -> dict[str, Path]:
    output_dir = project_root / ".crs" / "benchmarks"
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    paths = {
        "json": output_dir / f"benchmark-{stamp}.json",
        "markdown": output_dir / f"benchmark-{stamp}.md",
        "html": output_dir / f"benchmark-{stamp}.html",
        "raw_prompt": output_dir / f"benchmark-{stamp}.raw-prompt.txt",
        "crs_prompt": output_dir / f"benchmark-{stamp}.crs-prompt.txt",
        "latest_json": output_dir / "latest.json",
        "latest_markdown": output_dir / "latest.md",
        "latest_html": output_dir / "latest.html",
    }
    json_report = {key: value for key, value in report.items() if key != "prompts"}
    json_text = json.dumps(json_report, indent=2, ensure_ascii=False)
    markdown_text = render_benchmark_markdown(report)
    html_text = render_benchmark_html(json_report)
    paths["json"].write_text(json_text, encoding="utf-8")
    paths["markdown"].write_text(markdown_text, encoding="utf-8")
    paths["html"].write_text(html_text, encoding="utf-8")
    paths["raw_prompt"].write_text(report["prompts"]["raw"], encoding="utf-8")
    paths["crs_prompt"].write_text(report["prompts"]["crs"], encoding="utf-8")
    paths["latest_json"].write_text(json_text, encoding="utf-8")
    paths["latest_markdown"].write_text(markdown_text, encoding="utf-8")
    paths["latest_html"].write_text(html_text, encoding="utf-8")
    return paths
