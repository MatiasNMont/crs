# Chaos Engineering

`crs chaos` creates experiments from the selected component's graph domain and blast radius.

```bash
crs chaos ./aws-reference-example root::aws_dynamodb_table.domain --count 3 --depth 3
```

Built-in scenarios cover data outages, data latency, packet loss, pod termination, messaging backlog, unavailable secrets/KMS, and ledger/payment degradation.

Each experiment contains a hypothesis, target, parameters, observable signals, guardrails, abort conditions, direct dependencies, and affected downstream nodes.

CRS generates JSON, Markdown, and self-contained HTML under `.crs/chaos/`. These are planning artifacts. Review and adapt them for a controlled non-production environment before using any fault-injection platform.
