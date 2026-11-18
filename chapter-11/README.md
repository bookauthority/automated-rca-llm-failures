# Experiment 11 – Diagnosing Data, Retrieval, and Tooling Pipeline Failures

This self-contained Python 3.11+ project simulates a simplified RAG + tooling
system with a baseline observability setup and an augmented RCA (root cause
analysis) subsystem.

It is tailored for offline, sandboxed execution and produces a compact
`results.json` evidence file that can be validated against a reduced schema for
this environment.

## Overview

The real chapter design describes a distributed system with multiple services,
streaming buses, and observability backends. In this sandbox we instead
implement an **in-process simulation** capturing the same logical structure:

- A small synthetic **document corpus** partitioned into namespaces
  (e.g., `policies/current`), representing the RAG corpus.
- A **retrieval pipeline** that returns documents based on integer IDs
  and simple keyword matching (no external vector DB).
- A **tool layer** that simulates endpoints such as a `weather_api` that
  can behave normally or in a flaky fashion.
- A **baseline variant** that only records coarse per-request logs and
  simple error rates.
- A **treatment variant** that adds an **RCA subsystem**:
  - Structured events for ingestion, retrieval, and tools.
  - Simple anomaly detectors for ingestion drift and tool flakiness.
  - Basic root cause “artifacts” describing detected incidents.

The experiment runs 3 simplified workloads:

1. `WL1-normal-mixed-traffic` – normal RAG + tool traffic.
2. `WL2-broken-ingestion-job` – ingestion for `policies/current` silently
   stops updating after a simulated time; retrieval continues.
3. `WL3-flaky-tool-endpoint` – the `weather_api` becomes intermittently
   flaky (timeouts / errors) before recovering.

Each workload is executed **once for baseline and once for treatment** in this
sandboxed version. This is sufficient to generate comparable metrics for the
offline experiment harness.

## Evidence schema (sandboxed)

The top-level experiment driver is `run.py`. When executed, it:

- Runs both baseline and treatment variants for all three workloads.
- Measures simple numeric metrics per run (e.g., number of requests,
  number of failed tool calls, number of stale retrievals, and, for
  treatment, detection latency in synthetic time units).
- Writes JSON evidence to the file:

```jsonc
{
  "chapter": 11,
  "experiment_id": "exp-11-data-retrieval-tooling-rca-v1",
  "environment": {"os": "...", "python": "..."},
  "runs": [
    {
      "variant": "baseline" | "treatment",
      "workload_id": "WL1-normal-mixed-traffic" | "WL2-broken-ingestion-job" | "WL3-flaky-tool-endpoint",
      "run_id": "<unique-per-workload-and-variant>",
      "success": true | false,
      "metrics": {
        "requests_total": <number>,
        "retrieval_stale_or_missing": <number>,
        "tool_failures": <number>,
        "rca_detection_latency_units": <number> // treatment only, when detected
      },
      "notes": "...optional textual details..."
    }
  ],
  "notes": "Additional context about what was run."
}
```

### Important constraints

- **All metric values are numeric** (no strings, lists, or nulls).
- The project uses only the **Python standard library**; `requirements.txt`
  is empty of runtime deps.
- The evidence file is written to the directory specified by the
  `BOOKMAS_EVIDENCE_DIR` environment variable, defaulting to `/evidence`.
- At least **one baseline and one treatment run per workload** are produced.

The included tests in `tests/test_experiment.py` validate the shape of
`/evidence/results.json` and some basic invariants (e.g., coverage of
workloads and variants, and numeric metrics).

## Files

- `run.py` – main entrypoint; orchestrates all workloads and writes
  `/evidence/results.json`.
- `experiment/core.py` – core simulation primitives shared by baseline
  and treatment.
- `experiment/baseline.py` – baseline simulation logic without RCA.
- `experiment/treatment.py` – treatment simulation logic with RCA
  instrumentation and detection.
- `tests/test_experiment.py` – unittest suite verifying evidence schema
  and basic semantics.

## Running the experiment

1. Ensure you are using Python 3.11+.

2. Install (no external dependencies; this will be a NOOP):

```bash
pip install -r requirements.txt
```

3. Run the experiment:

```bash
python run.py
```

This will create `/evidence/results.json` (or another directory if
`BOOKMAS_EVIDENCE_DIR` is set).

4. Run the tests:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

If the tests pass, the evidence file should conform to the required
runtime contract for the sandboxed environment.

## Notes on simplifications

Because this environment is offline and constrained:

- We do **not** call real LLMs, vector databases, HTTP tools, or
  external systems. All behaviors (retrieval, ingestion, tool flakiness)
  are simulated in memory using deterministic pseudo-random processes.
- "Time" is represented as integer **time steps** instead of wall clock
  seconds. Detection latencies are measured in these synthetic units and
  exposed as numeric metrics. Mapping them to real time is out of scope
  for this sandbox.
- The full experiment design describes additional metrics (e.g., MTTR,
  precision/recall over multiple runs). Here we provide **simplified
  but faithful proxies** that remain consistent between baseline and
  treatment, preserving the logical distinction between variants and the
  impact of the RCA subsystem.
