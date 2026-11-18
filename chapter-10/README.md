# Chapter 10 – Diagnosing Model Drift, Routing, and Performance Regressions

This is a **self-contained, offline Python 3.11+ experiment** implementing a
simplified version of the specification for:

- **Experiment ID**: `exp-model-drift-routing-rca-ch10`
- **Chapter**: 10

The goal is to simulate:

1. A **baseline** LLM gateway with simple metrics only.
2. A **treatment** gateway with **model drift and routing RCA** logic.

We simulate three logical models:

- `model_v1_stable` – good, stable behavior.
- `model_v2_candidate_good` – similar or slightly better than v1.
- `model_v3_candidate_bad` – worse quality and higher latency/cost.

We also simulate a minimal RCA engine that:

- Aggregates per-model metrics.
- Detects regressions between stable and canary models.
- Attributes regressions to **model_drift** or **routing_misconfig** using
  simple rules.

All simulation is performed with the Python standard library only.

## Project layout

- `run.py` – Orchestrates the experiment, runs baseline and treatment
  simulations, and writes evidence JSON to `$BOOKMAS_EVIDENCE_DIR/results.json`.
- `experiment/__init__.py` – Package marker.
- `experiment/models.py` – Simulated model behaviors (latency, quality, cost).
- `experiment/workloads.py` – Synthetic workloads and request generators.
- `experiment/baseline.py` – Baseline gateway simulation.
- `experiment/rca.py` – RCA logic (treatment variant) for drift/routing.
- `experiment/treatment.py` – Treatment gateway simulation using RCA.
- `experiment/utils.py` – Shared utilities (timing, environment detection).
- `tests/test_experiment.py` – Unit tests for evidence schema & basic behavior.
- `requirements.txt` – Intentionally empty of runtime deps (stdlib only).

## How the experiment works

This project does **not** call any real LLMs or external services. Instead,
it uses synthetic stochastic models to produce plausible metrics:

- Each model returns a **simulated latency**, **token count**, and
  **quality score**.
- The distributions differ by model and phase to represent drift and
  regressions.
- Two logical workloads are simulated:
  - `synthetic_eval_workload` (ID: `eval`)
  - `synthetic_prod_like_workload` (ID: `prod`)

Both workloads are run under **baseline** and **treatment** with shared
random seeds to make them comparable.

The **baseline** simply runs the routing and collects per-request metrics.

The **treatment** additionally:

- Logs per-request routing decisions.
- Aggregates metrics per model.
- Compares canary vs. stable metrics.
- Detects quality and latency regressions.
- Classifies them as `model_drift` or `routing_misconfig` based on simple
  rules (e.g., large change in canary weight without model change).

## Evidence file contract

`run.py` writes a single JSON file to:

- Path: `$BOOKMAS_EVIDENCE_DIR/results.json`
- If `BOOKMAS_EVIDENCE_DIR` is not set, `/evidence/results.json` is used.

The JSON has this schema (plus some extra, non-metric fields):

```json
{
  "chapter": 10,
  "experiment_id": "exp-model-drift-routing-rca-ch10",
  "environment": {"os": "...", "python": "..."},
  "runs": [
    {
      "variant": "baseline",
      "workload_id": "eval",
      "run_id": "baseline_eval_1",
      "success": true,
      "metrics": {
        "mean_quality": 0.82,
        "mean_latency_ms": 12.3
      }
    },
    {
      "variant": "treatment",
      "workload_id": "eval",
      "run_id": "treatment_eval_1",
      "success": true,
      "metrics": {
        "mean_quality": 0.81,
        "mean_latency_ms": 13.1,
        "rca_detected_regressions": 1.0
      }
    }
  ],
  "notes": "... free text ...",
  "extra": {...}
}
```

**Important constraints enforced by tests:**

- `chapter` is the integer `10`.
- `experiment_id` is exactly
  `"exp-model-drift-routing-rca-ch10"`.
- `runs` contains at least one **baseline** and one **treatment** run
  for **each workload**.
- Every `metrics` value is a **finite JSON number** (no strings, no
  nulls, no nested objects).

If some quantities cannot be measured in this sandbox, they are simply
**omitted from `metrics`** and, if helpful, mentioned in the top-level
`notes` field.

## Running the experiment

From the project root:

```bash
python run.py
```

This will:

1. Run baseline and treatment simulations for each workload.
2. Compute aggregated metrics.
3. Write `/evidence/results.json` (or
   `$BOOKMAS_EVIDENCE_DIR/results.json` if the environment variable is set).

You can inspect this file to see the metrics used to compare baseline
and treatment variants.

## Running tests

From the project root:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

The tests validate:

- The evidence file exists after running `run.py`.
- The evidence JSON conforms to the required schema.
- Metrics are numeric and finite.
- Both baseline and treatment contain runs for each workload.

## Determinism and reproducibility

- All pseudo-randomness is generated with explicitly seeded `random.Random`
  instances.
- Seeds are constant per variant/workload so that runs are reproducible.
- No external network access or non-standard libraries are used.

## Limitations

This implementation is **highly simplified** compared to the full
chapter specification:

- No real HTTP gateway or FastAPI app is run.
- No real databases or Prometheus metrics are used.
- Only aggregated metrics (e.g., mean quality, mean latency) are
  computed instead of full sliding-window change point detection.

Nevertheless, the core ideas of **baseline vs. treatment**,
**model-centric drift**, **routing-aware metrics**, and **RCA attribution**
are captured in a way that is deterministic and easily executable in an
offline sandbox.
