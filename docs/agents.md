# CRS Agents

`crs ask` provides a small deterministic agent layer over graph queries.

## Pipeline

1. Tokenize the question and remove stop words.
2. Score graph nodes against the remaining terms.
3. Detect intent: `impact`, `failure`, or `context`.
4. Build compact graph context around the selected node.
5. Run the corresponding graph query.
6. Return human-readable output or compact JSON.

```bash
crs ask . "What is affected if the network module changes?"
crs ask . "What is affected if I delete the domain DynamoDB tables?" --json
```

The default JSON payload contains `decision`, `command`, `context`, and `result`. Use `--full-payload` only for debugging internal agent metadata.

Intent detection supports common English and Spanish terms, while all generated tool output is English.
