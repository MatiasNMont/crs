# Token Benchmark

`crs benchmark-tokens` compares two prompts:

- Raw mode: all Terraform files in the repository.
- CRS mode: the compact graph context produced by `crs ask`.

```bash
crs benchmark-tokens ./aws-reference-example "What is affected if I delete the domain DynamoDB tables?"
```

The built-in estimate uses `ceil(characters / 4)`. It is a repeatable approximation, not a provider billing measurement.

Reports are written to `.crs/benchmarks/` as JSON, Markdown, HTML, and both prompt variants. For billing-quality measurements, send both prompts to the same model and compare provider-reported usage.

On `aws-reference-example`, the measured `summary` result is 7,481 raw tokens versus 2,063 CRS tokens, a 72.42% reduction.
