# Chapter 7 Experiment: Detecting and Localizing LLM Failures in Real Time

This is a **self-contained, offline, synthetic experiment** for:

- **Chapter**: 7
- **Experiment ID**: `exp-07-detect-localize-llm-failures-v1`
- **Title**: Detecting and Localizing LLM Failures in Real Time

The goal is to:

- Implement a simple metrics-only **baseline detector**.
- Implement a more advanced **treatment detector** that adds content-aware failure signals and per-prompt statistics.
- Generate synthetic LLM interaction events for several workloads that roughly correspond to the narrative (latency spikes, token/cost anomalies, hallucinations, policy issues, etc.).
- Run both detectors over the same synthetic events and compare simple numeric metrics.
- Emit experiment evidence in a strictly defined JSON schema to `/evidence/results.json`.

This project does **not** call any real LLMs or external services. Everything is simulated deterministically using the Python standard library only.

## Project Layout

- `run.py` – Main entrypoint. Runs the experiment, executes workloads under baseline and treatment detectors, and writes `/evidence/results.json`.
- `experiment/__init__.py` – Package marker.
- `experiment/config.py` – Static configuration for workloads, failure regimes, and detector parameters.
- `experiment/events.py` – Dataclasses and helpers to generate synthetic events representing LLM interactions.
- `experiment/detectors.py` – Implementation of baseline and treatment detectors.
- `experiment/metrics.py` – Simple metric calculators used by `run.py`.
- `tests/test_experiment.py` – Unittests. They:
  - Execute `run.py` in-process.
  - Assert that `/evidence/results.json` exists.
  - Validate the exact evidence schema (including numeric metrics).

## Environment & Dependencies

- **Python**: 3.11+
- **Dependencies**: Python standard library only. No external libraries are required at runtime.

Install (optional) development tools as desired, but they are not required to run this experiment.

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

The `requirements.txt` is intentionally minimal and has no runtime dependencies.

## Running the Experiment

```bash
# From the project root
python run.py
```

This will:

1. Determine the evidence directory from `BOOKMAS_EVIDENCE_DIR` (default: `/evidence`).
2. Generate synthetic events for all configured workloads.
3. Run the baseline and treatment detectors over the exact same events.
4. Compute basic numeric metrics per `(variant, workload)` pair:
   - `avg_latency_ms`
   - `failure_event_rate`
   - `detection_rate` (fraction of failure events that were flagged)
   - `false_positive_rate`
5. Write a JSON evidence file at:

```bash
$BOOKMAS_EVIDENCE_DIR/results.json
```

with this schema:

```json
{
  "chapter": 7,
  "experiment_id": "exp-07-detect-localize-llm-failures-v1",
  "environment": {"os": "...", "python": "..."},
  "runs": [
    {
      "variant": "baseline" | "treatment",
      "workload_id": "...",
      "run_id": "...",
      "success": true,
      "metrics": {
        "avg_latency_ms": 123.4,
        "failure_event_rate": 0.25,
        "detection_rate": 0.8,
        "false_positive_rate": 0.05
      }
    }
  ],
  "notes": "... optional text ..."
}
```

Additional non-metric information may be added outside of `metrics`, but numeric metrics **must** be finite JSON numbers.

Each workload has at least one baseline and one treatment run.

## Running Tests

```bash
python -m unittest discover -s tests -p "test_*.py"
```

The tests validate that:

- `run.py` creates `/evidence/results.json` under a temporary evidence directory.
- The JSON structure matches the required schema:
  - Correct `chapter` and `experiment_id`.
  - `environment` contains strings.
  - `runs` has at least one baseline and one treatment run per workload.
  - All metric values are numbers.

## Design Notes

### Synthetic Workloads

The code implements a compact subset of the rich narrative workloads:

- `baseline_normal_workload`
- `latency_spike_failure`
- `token_cost_anomaly`
- `hallucination_spike_failure`
- `policy_violation_burst`
- `prompt_regression_version_swap`
- `routing_misconfiguration`

For each, the generator controls:

- Number of events
- Base latency / tokens
- Failure-specific modifications (e.g., spike in latency or hallucination flag)

### Baseline vs Treatment Detectors

- **Baseline**
  - Simple global threshold rules on per-event latency and an overall error-like flag.
  - No per-prompt logic.
  - Mimics metrics-only SLO alerts.

- **Treatment**
  - Adds per-prompt statistics and a basic rolling mean/std detector.
  - Uses content flags on events (e.g., `is_hallucination`, `is_policy_violation`) as if produced by an external LLM judge, but here those are generated deterministically.
  - Still implemented in a streaming-like, single-pass manner.

### Metrics

All numeric metrics are computed directly from the generated events and detector outputs; nothing is fabricated or inferred without support from the data.

Because this environment is offline and synthetic:

- We do **not** attempt to measure wall-clock latency or resource usage.
- Metrics focus on detection behaviour over the simulated event stream.

You can extend the experiment by:

- Adding more nuanced failure regimes.
- Extending detectors (e.g., more realistic anomaly scoring).
- Enriching metrics (e.g., per-prompt localization accuracy) while preserving the required top-level schema.
