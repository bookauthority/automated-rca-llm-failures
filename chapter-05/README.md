# Chapter 5 Experiment: Instrumenting LLM Systems for High-Fidelity RCA Signals

This mini-project implements a fully self-contained Python 3.11+ experiment for:

- Baseline: a minimal, non-instrumented LLM gateway.
- Treatment: an RCA-instrumented gateway that emits structured LLM interaction events, traces, and RCA signals.
- Synthetic workload: drives both variants with identical, deterministic traffic and collects metrics.
- Analysis: checks some instrumentation quality aspects and writes evidence as JSON.

The implementation is **offline only** (no network, no external services, no OpenTelemetry SDK). Instead, it simulates the concepts (traces, spans, logs, redaction, feedback, guardrails, evaluator scores) using only the Python standard library so it can run in a restricted sandbox.

The structure mirrors the chapter sections:

- **5.1** Principles → `gateway/instrumentation/` modules and comments.
- **5.2** Event schema → `gateway/instrumentation/schema.py` and `config/llm_interaction_schema.json`.
- **5.3** Redaction → `gateway/instrumentation/redaction.py` and `config/instrumentation.yaml` (YAML-like but parsed manually).
- **5.4** Traces/logs → `gateway/instrumentation/otel_setup.py` (simulated traces/logs) and events written to `runs/*/events.jsonl`.
- **5.5** Feedback/guardrails/evaluators → `gateway/instrumented_app.py`, `workloads/synthetic_workload.py`, and `analysis/offline_evaluator.py`.
- **5.6** Minimal observability pipeline → use of the schema + event writer + trace context.
- **5.7** Synthetic workload → `workloads/synthetic_workload.py` plus `run.py` orchestration.

## Project Layout

- `run.py` – Orchestrates the full experiment: runs baseline and treatment workloads and writes `/evidence/results.json`.
- `gateway/`
  - `baseline_app.py` – Minimal gateway without RCA instrumentation.
  - `instrumented_app.py` – Gateway with structured events, traces, guardrails, feedback hooks.
  - `llm_client.py` – Deterministic mock LLM backend used by both variants.
  - `instrumentation/`
    - `schema.py` – Python representation of the LLM interaction schema.
    - `otel_setup.py` – Simulated trace/span context and JSON log writer.
    - `redaction.py` – Configurable redaction/pseudonymization utilities.
- `workloads/`
  - `synthetic_workload.py` – Generates a synthetic mixed workload and measures metrics.
- `analysis/`
  - `check_instrumentation_quality.py` – Validates events, simple linkage checks, schema compliance.
  - `offline_evaluator.py` – Simple heuristic quality/safety scoring.
- `config/`
  - `instrumentation.yaml` – Redaction configuration (YAML-like, parsed manually).
  - `llm_interaction_schema.json` – JSON Schema for interaction events.
- `tests/`
  - `test_experiment.py` – Asserts the evidence schema and sanity-checks the run.

## Running the Experiment

From the project root:

```bash
python run.py
```

This will:

1. Create `runs/baseline` and `runs/treatment` directories under the working directory.
2. Run the synthetic workload once against the baseline gateway implementation (no instrumentation output, but basic metrics are collected).
3. Run the synthetic workload once against the treatment gateway implementation (instrumentation is active; events and traces are written).
4. Call `analysis/check_instrumentation_quality.py` to produce a simple summary.
5. Write evidence JSON to `${BOOKMAS_EVIDENCE_DIR:-/evidence}/results.json` with the following structure:

```json
{
  "chapter": 5,
  "experiment_id": "exp-ch5-llm-instrumentation-otel-rca-signals-v1",
  "environment": {"os": "...", "python": "..."},
  "runs": [
    {
      "variant": "baseline",
      "workload_id": "synthetic-mixed-traffic",
      "run_id": "baseline-1",
      "success": true,
      "metrics": {
        "gateway_p95_latency_ms": 0.5,
        "gateway_mean_latency_ms": 0.2,
        "gateway_error_rate": 0.0,
        "total_requests": 120
      }
    },
    {
      "variant": "treatment",
      "workload_id": "synthetic-mixed-traffic",
      "run_id": "treatment-1",
      "success": true,
      "metrics": {
        "gateway_p95_latency_ms": 0.7,
        "gateway_mean_latency_ms": 0.3,
        "gateway_error_rate": 0.0,
        "total_requests": 120,
        "events_per_request_mean": 1.0
      }
    }
  ],
  "notes": "..."
}
```

**Important constraints implemented**:

- Uses only the Python standard library. `requirements.txt` is intentionally empty of runtime dependencies.
- No network, subprocesses, or external commands are used.
- All file writes are constrained to the project tree and `/evidence`.
- Metrics are computed from real execution of local Python functions, not fabricated.
- Treatment and baseline share the same deterministic mock LLM and workload generator.

## Running Tests

```bash
python -m unittest discover -s tests -p "test_*.py"
```

This will:

- Run `run.py` (as part of the test) to generate evidence (if not already present).
- Validate that `/evidence/results.json` matches the expected schema.
- Ensure at least one baseline and one treatment run are present, and that numeric metrics exist.

## Notes on Limitations

- OpenTelemetry is **simulated only** via simple span/trace IDs and JSON logs – no external collector.
- Some advanced metrics from the chapter spec (e.g., OTLP export error rate) cannot be meaningfully measured in this offline sandbox and are therefore omitted from `metrics`.
- The timing metrics are based on `time.perf_counter()` around local function calls; they will be very small but are still real measurements.
