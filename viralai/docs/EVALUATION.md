Evaluation: FASTA-based mutation detection
=========================================

This document explains how to run the evaluation endpoint and CLI to test the
mutation detection engine on real FASTA files.

API endpoint
------------

POST /analysis/evaluate

- Accepts a multipart/form-data upload with one `reference` file and one-or-more
  `queries` files (all FASTA-like text files).
- Returns a JSON body with a `reports` array describing `mutation_count`, `positions`,
  `runtime_seconds`, and timestamps for each query.

Example using curl:

```bash
curl -s -X POST "http://127.0.0.1:8000/analysis/evaluate" \
  -F "reference=@/path/to/reference.fasta" \
  -F "queries=@/path/to/query1.fasta" \
  -F "queries=@/path/to/query2.fasta" \
  -H "X-API-Key: <your-researcher-key>"
```

Example using Python httpx:

```python
import httpx

files = [
    ("reference", ("ref.fasta", open("ref.fasta", "rb"), "text/plain")),
    ("queries", ("q1.fasta", open("q1.fasta", "rb"), "text/plain")),
]

headers = {"X-API-Key": "<your-researcher-key>"}
resp = httpx.post("http://127.0.0.1:8000/analysis/evaluate", files=files, headers=headers)
print(resp.json())
```

CLI
---

You can also evaluate FASTA files locally via the CLI:

```bash
python -m viralai.cli evaluate-fasta --reference /path/to/ref.fasta --query /path/to/query_or_dir --output-dir .viralai_evaluation
```

Outputs
-------

- CLI writes per-query JSON reports to `--output-dir/reports/` and prints a short
  summary to stdout.
- API returns a JSON `reports` array suitable for programmatic consumption.

Expected positions
------------------

Each per-query report includes a `positions` array with integer genome positions where
mutations were detected. To provide ground-truth for automated scoring, supply an
`expected_positions` JSON map keyed by query filename when calling the API (or when
preparing a benchmark dataset). Example (HTTP client with `expected_positions` as a
form field):

```python
import json
import httpx

files = [
    ("reference", ("ref.fasta", open("ref.fasta", "rb"), "text/plain")),
    ("queries", ("q1.fasta", open("q1.fasta", "rb"), "text/plain")),
]
expected = json.dumps({"q1.fasta": [5, 42]})
headers = {"X-API-Key": "<your-researcher-key>"}
resp = httpx.post("http://127.0.0.1:8000/analysis/evaluate", files=files, data={"expected_positions": expected}, headers=headers)
print(resp.json())
```

Benchmark persistence
---------------------

Benchmark run history is stored by `BenchmarkRepository` to a JSON file under the
configured data root (the CLI and API use `.viralai_api_data` by default). The
CLI dashboard and `/benchmark` endpoints read and write this `benchmarks.json` file.
To run and persist benchmarks from the CLI:

```bash
viralai dashboard --run-benchmarks --data-dir .viralai_api_data
```

The resulting file will be `.viralai_api_data/benchmarks.json` and can be inspected
or used by the UI to display historical metrics.
