from __future__ import annotations

import html
import json
from typing import Any


def graph_to_html(graph: dict[str, Any]) -> str:
    nodes = []
    for node_id, node in graph["nodes"].items():
        nodes.append(
            {
                "id": node_id,
                "kind": node.get("kind", ""),
                "file": node.get("file", ""),
                "start_line": node.get("start_line"),
                "end_line": node.get("end_line"),
                "domain_tags": node.get("domain_tags", []),
                "config": node.get("config", ""),
            }
        )

    links = [
        {
            "source": relation["source"],
            "target": relation["target"],
            "kind": relation["kind"],
            "evidence": relation.get("evidence", ""),
        }
        for relation in graph["relations"]
        if relation["source"] in graph["nodes"] and relation["target"] in graph["nodes"]
    ]

    payload = {
        "project_root": graph["project_root"],
        "generated_at": graph["generated_at"],
        "node_count": graph["node_count"],
        "relation_count": graph["relation_count"],
        "nodes": nodes,
        "links": links,
    }

    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    title = html.escape(f"CRS Graph - {graph['project_root']}")

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f8fb;
      --panel: #ffffff;
      --ink: #18202f;
      --muted: #667085;
      --line: #d8dee9;
      --accent: #0f766e;
      --danger: #b42318;
      --shadow: 0 10px 28px rgba(24, 32, 47, 0.10);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      height: 100vh;
      overflow: hidden;
      font-family: "Segoe UI", Arial, sans-serif;
      background: var(--bg);
      color: var(--ink);
    }}
    .app {{
      display: grid;
      grid-template-columns: 320px 1fr 380px;
      height: 100vh;
      min-width: 980px;
    }}
    aside {{
      background: var(--panel);
      border-right: 1px solid var(--line);
      padding: 18px;
      overflow: auto;
    }}
    .details {{
      border-left: 1px solid var(--line);
      border-right: 0;
    }}
    h1 {{
      margin: 0 0 4px;
      font-size: 20px;
      letter-spacing: 0;
    }}
    h2 {{
      margin: 22px 0 10px;
      font-size: 13px;
      text-transform: uppercase;
      color: var(--muted);
      letter-spacing: 0.04em;
    }}
    .meta {{
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
      word-break: break-word;
    }}
    .stat-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-top: 14px;
    }}
    .stat {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      background: #fbfcfe;
    }}
    .stat strong {{
      display: block;
      font-size: 22px;
    }}
    .stat span {{
      color: var(--muted);
      font-size: 12px;
    }}
    label {{
      display: block;
      margin: 12px 0 6px;
      color: var(--muted);
      font-size: 12px;
    }}
    input, select, button {{
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 9px 10px;
      font: inherit;
      background: #fff;
      color: var(--ink);
    }}
    button {{
      cursor: pointer;
      background: var(--accent);
      border-color: var(--accent);
      color: white;
      margin-top: 10px;
    }}
    .canvas-wrap {{
      position: relative;
      overflow: hidden;
    }}
    svg {{
      width: 100%;
      height: 100%;
      display: block;
      background: radial-gradient(circle at 50% 40%, #ffffff 0, #f7f8fb 62%);
    }}
    .link {{
      stroke: #a9b4c6;
      stroke-opacity: 0.58;
      stroke-width: 1.2;
    }}
    .link.highlight {{
      stroke: var(--danger);
      stroke-width: 2.4;
      stroke-opacity: 0.95;
    }}
    .node circle {{
      stroke: #fff;
      stroke-width: 2;
      filter: drop-shadow(0 2px 3px rgba(24, 32, 47, 0.20));
      cursor: pointer;
    }}
    .node text {{
      font-size: 10px;
      fill: #344054;
      pointer-events: none;
      paint-order: stroke;
      stroke: #fff;
      stroke-width: 3px;
      stroke-linejoin: round;
    }}
    .node.dim, .link.dim {{
      opacity: 0.12;
    }}
    .node.selected circle {{
      stroke: var(--danger);
      stroke-width: 4;
    }}
    .legend {{
      display: grid;
      gap: 7px;
      margin-top: 10px;
    }}
    .legend-row {{
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
    }}
    .swatch {{
      width: 12px;
      height: 12px;
      border-radius: 50%;
      display: inline-block;
    }}
    .pill {{
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 3px 8px;
      margin: 3px 4px 3px 0;
      background: #edf2f7;
      color: #344054;
      font-size: 12px;
    }}
    pre {{
      white-space: pre-wrap;
      word-break: break-word;
      background: #101828;
      color: #e4e7ec;
      padding: 12px;
      border-radius: 8px;
      font-size: 12px;
      max-height: 360px;
      overflow: auto;
    }}
    .empty {{
      color: var(--muted);
      margin-top: 18px;
      line-height: 1.5;
    }}
    .toolbar {{
      position: absolute;
      left: 16px;
      bottom: 16px;
      background: rgba(255,255,255,0.92);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 8px 10px;
      box-shadow: var(--shadow);
      color: var(--muted);
      font-size: 12px;
    }}
  </style>
</head>
<body>
  <div class="app">
    <aside>
      <h1>CRS Graph</h1>
      <div class="meta" id="project"></div>
      <div class="stat-grid">
        <div class="stat"><strong id="nodeCount"></strong><span>Nodes</span></div>
        <div class="stat"><strong id="linkCount"></strong><span>Relationships</span></div>
      </div>

      <h2>Filtros</h2>
      <label for="search">Search nodes</label>
      <input id="search" placeholder="aurora, module.data, eks">

      <label for="kindFilter">Tipo</label>
      <select id="kindFilter"><option value="">Todos</option></select>

      <label for="domainFilter">Domain</label>
      <select id="domainFilter"><option value="">Todos</option></select>

      <button id="reset">Reset vista</button>

      <h2>Leyenda</h2>
      <div class="legend" id="legend"></div>
    </aside>

    <main class="canvas-wrap">
      <svg id="graph" role="img" aria-label="CRS graph visualization"></svg>
      <div class="toolbar">Drag nodes. Click for details. Scroll to zoom.</div>
    </main>

    <aside class="details">
      <h1>Detalle</h1>
      <div id="details" class="empty">Select a node to view its configuration and relationships.</div>
    </aside>
  </div>

  <script id="crs-data" type="application/json">{data_json}</script>
  <script>
    const data = JSON.parse(document.getElementById("crs-data").textContent);
    const svg = document.getElementById("graph");
    const search = document.getElementById("search");
    const kindFilter = document.getElementById("kindFilter");
    const domainFilter = document.getElementById("domainFilter");
    const details = document.getElementById("details");
    const reset = document.getElementById("reset");
    const colors = {{
      resource: "#2563eb",
      module: "#0f766e",
      variable: "#7c3aed",
      output: "#ca8a04",
      data: "#db2777",
      locals: "#475467"
    }};
    const fallback = "#64748b";

    document.getElementById("project").textContent = data.project_root + " · " + data.generated_at;
    document.getElementById("nodeCount").textContent = data.node_count;
    document.getElementById("linkCount").textContent = data.relation_count;

    const kinds = [...new Set(data.nodes.map(n => n.kind))].sort();
    const domains = [...new Set(data.nodes.flatMap(n => n.domain_tags || []))].sort();
    for (const kind of kinds) kindFilter.append(new Option(kind, kind));
    for (const domain of domains) domainFilter.append(new Option(domain, domain));
    document.getElementById("legend").innerHTML = kinds.map(kind =>
      `<div class="legend-row"><span class="swatch" style="background:${{colors[kind] || fallback}}"></span>${{kind}}</div>`
    ).join("");

    const state = {{
      selected: null,
      zoom: 1,
      panX: 0,
      panY: 0,
      dragging: null,
      panning: null
    }};

    const nodeById = new Map(data.nodes.map(n => [n.id, n]));
    const outgoing = new Map();
    const incoming = new Map();
    for (const link of data.links) {{
      if (!outgoing.has(link.source)) outgoing.set(link.source, []);
      if (!incoming.has(link.target)) incoming.set(link.target, []);
      outgoing.get(link.source).push(link);
      incoming.get(link.target).push(link);
    }}

    function initPositions() {{
      const rect = svg.getBoundingClientRect();
      const width = rect.width || 900;
      const height = rect.height || 700;
      const radius = Math.min(width, height) * 0.38;
      data.nodes.forEach((node, index) => {{
        const angle = (index / data.nodes.length) * Math.PI * 2;
        node.x = width / 2 + Math.cos(angle) * radius * (0.55 + (index % 7) / 14);
        node.y = height / 2 + Math.sin(angle) * radius * (0.55 + (index % 5) / 12);
        node.vx = 0;
        node.vy = 0;
      }});
    }}

    function tick() {{
      const rect = svg.getBoundingClientRect();
      const cx = rect.width / 2;
      const cy = rect.height / 2;
      for (const link of data.links) {{
        const a = nodeById.get(link.source);
        const b = nodeById.get(link.target);
        if (!a || !b) continue;
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const desired = link.kind === "contains" ? 86 : 128;
        const force = (dist - desired) * 0.002;
        const fx = dx / dist * force;
        const fy = dy / dist * force;
        a.vx += fx;
        a.vy += fy;
        b.vx -= fx;
        b.vy -= fy;
      }}
      for (let i = 0; i < data.nodes.length; i++) {{
        for (let j = i + 1; j < data.nodes.length; j++) {{
          const a = data.nodes[i];
          const b = data.nodes[j];
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const dist2 = dx * dx + dy * dy || 1;
          if (dist2 > 22000) continue;
          const force = 18 / dist2;
          a.vx -= dx * force;
          a.vy -= dy * force;
          b.vx += dx * force;
          b.vy += dy * force;
        }}
      }}
      for (const node of data.nodes) {{
        node.vx += (cx - node.x) * 0.0008;
        node.vy += (cy - node.y) * 0.0008;
        node.vx *= 0.88;
        node.vy *= 0.88;
        if (!node.fixed) {{
          node.x += node.vx;
          node.y += node.vy;
        }}
      }}
      render();
      requestAnimationFrame(tick);
    }}

    function visibleNode(node) {{
      const term = search.value.trim().toLowerCase();
      const kind = kindFilter.value;
      const domain = domainFilter.value;
      if (kind && node.kind !== kind) return false;
      if (domain && !(node.domain_tags || []).includes(domain)) return false;
      if (term && !node.id.toLowerCase().includes(term) && !node.file.toLowerCase().includes(term)) return false;
      return true;
    }}

    function relatedToSelected(id) {{
      if (!state.selected) return true;
      if (id === state.selected) return true;
      return (outgoing.get(state.selected) || []).some(l => l.target === id)
        || (incoming.get(state.selected) || []).some(l => l.source === id)
        || (outgoing.get(id) || []).some(l => l.target === state.selected)
        || (incoming.get(id) || []).some(l => l.source === state.selected);
    }}

    function render() {{
      const visible = new Set(data.nodes.filter(visibleNode).map(n => n.id));
      const selectedLinks = new Set();
      if (state.selected) {{
        for (const link of [...(incoming.get(state.selected) || []), ...(outgoing.get(state.selected) || [])]) {{
          selectedLinks.add(link.source + "->" + link.target + ":" + link.kind);
        }}
      }}
      const linkMarkup = data.links
        .filter(l => visible.has(l.source) && visible.has(l.target))
        .map(l => {{
          const a = nodeById.get(l.source);
          const b = nodeById.get(l.target);
          const key = l.source + "->" + l.target + ":" + l.kind;
          const cls = "link" + (state.selected && !selectedLinks.has(key) ? " dim" : "") + (selectedLinks.has(key) ? " highlight" : "");
          return `<line class="${{cls}}" x1="${{a.x}}" y1="${{a.y}}" x2="${{b.x}}" y2="${{b.y}}"><title>${{escapeText(l.kind + ": " + l.evidence)}}</title></line>`;
        }}).join("");
      const nodeMarkup = data.nodes
        .filter(n => visible.has(n.id))
        .map(n => {{
          const dim = state.selected && !relatedToSelected(n.id);
          const selected = state.selected === n.id;
          const label = shortLabel(n.id);
          const r = n.kind === "module" ? 10 : n.kind === "resource" ? 7 : 6;
          return `<g class="node${{dim ? " dim" : ""}}${{selected ? " selected" : ""}}" data-id="${{escapeAttr(n.id)}}" transform="translate(${{n.x}},${{n.y}})">
            <circle r="${{r}}" fill="${{colors[n.kind] || fallback}}"></circle>
            <text x="10" y="4">${{escapeText(label)}}</text>
          </g>`;
        }}).join("");
      svg.innerHTML = `<g transform="translate(${{state.panX}},${{state.panY}}) scale(${{state.zoom}})">${{linkMarkup}}${{nodeMarkup}}</g>`;
      bindNodeEvents();
    }}

    function bindNodeEvents() {{
      svg.querySelectorAll(".node").forEach(el => {{
        el.addEventListener("mousedown", event => {{
          event.stopPropagation();
          const id = el.getAttribute("data-id");
          state.dragging = {{ id, startX: event.clientX, startY: event.clientY }};
          nodeById.get(id).fixed = true;
        }});
        el.addEventListener("click", event => {{
          event.stopPropagation();
          selectNode(el.getAttribute("data-id"));
        }});
      }});
    }}

    function selectNode(id) {{
      state.selected = id;
      const node = nodeById.get(id);
      const inc = incoming.get(id) || [];
      const out = outgoing.get(id) || [];
      details.innerHTML = `
        <div class="meta">${{escapeText(node.file)}}:${{node.start_line}}-${{node.end_line}}</div>
        <h2>${{escapeText(node.id)}}</h2>
        <div>${{(node.domain_tags || []).map(t => `<span class="pill">${{escapeText(t)}}</span>`).join("") || '<span class="pill">no tags</span>'}}</div>
        <h2>Entrantes (${{inc.length}})</h2>
        ${{inc.length ? inc.map(l => `<div class="meta">← ${{escapeText(l.source)}} · ${{escapeText(l.kind)}}</div>`).join("") : '<div class="meta">No incoming relationships.</div>'}}
        <h2>Salientes (${{out.length}})</h2>
        ${{out.length ? out.map(l => `<div class="meta">→ ${{escapeText(l.target)}} · ${{escapeText(l.kind)}}</div>`).join("") : '<div class="meta">No outgoing relationships.</div>'}}
        <h2>Configuration</h2>
        <pre>${{escapeText(node.config)}}</pre>
      `;
      render();
    }}

    function shortLabel(id) {{
      const parts = id.split("::");
      const address = parts[parts.length - 1];
      return address.length > 34 ? address.slice(0, 31) + "..." : address;
    }}
    function escapeText(value) {{
      return String(value).replace(/[&<>"']/g, c => ({{ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }}[c]));
    }}
    function escapeAttr(value) {{
      return escapeText(value);
    }}

    for (const control of [search, kindFilter, domainFilter]) control.addEventListener("input", render);
    reset.addEventListener("click", () => {{
      search.value = "";
      kindFilter.value = "";
      domainFilter.value = "";
      state.selected = null;
      state.zoom = 1;
      state.panX = 0;
      state.panY = 0;
      initPositions();
      details.className = "empty";
      details.textContent = "Select a node to view its configuration and relationships.";
      render();
    }});
    svg.addEventListener("mousedown", event => {{
      state.panning = {{ x: event.clientX, y: event.clientY, panX: state.panX, panY: state.panY }};
    }});
    window.addEventListener("mousemove", event => {{
      if (state.dragging) {{
        const node = nodeById.get(state.dragging.id);
        node.x += (event.clientX - state.dragging.startX) / state.zoom;
        node.y += (event.clientY - state.dragging.startY) / state.zoom;
        state.dragging.startX = event.clientX;
        state.dragging.startY = event.clientY;
        render();
      }} else if (state.panning) {{
        state.panX = state.panning.panX + event.clientX - state.panning.x;
        state.panY = state.panning.panY + event.clientY - state.panning.y;
        render();
      }}
    }});
    window.addEventListener("mouseup", () => {{
      state.dragging = null;
      state.panning = null;
    }});
    svg.addEventListener("wheel", event => {{
      event.preventDefault();
      const delta = event.deltaY > 0 ? 0.92 : 1.08;
      state.zoom = Math.max(0.25, Math.min(3, state.zoom * delta));
      render();
    }}, {{ passive: false }});

    initPositions();
    tick();
  </script>
</body>
</html>
"""
