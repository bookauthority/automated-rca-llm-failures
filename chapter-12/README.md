# Chapter 12 Experiment: Automated Remediation Guardrails and MTTR

This mini-project implements a **self-contained simulation** of LLM incident remediation with:

- A **baseline**: manual-style remediation logic with longer latencies and no orchestrator guardrails.
- A **treatment**: an **automated remediation orchestrator** with guardrails, approvals, and rollbacks.

It runs a deterministic incident script and measures Mean Time To Resolve (MTTR) and related metrics for both variants.

The code is intentionally small, offline, and dependency-free (Python standard library only). It is not a full microservice stack, but it mirrors the structure and concepts described in the specification.

## Contents

- `run.py` – Entry point that runs the baseline and treatment simulations and writes evidence.
- `experiment/simulation.py` – Incident generator, RCA output simulator, orchestrator, and metrics machinery.
- `experiment/configs.py` – Guardrail and policy configuration for baseline vs. treatment.
- `tests/test_experiment.py` – Unit tests validating the evidence schema and basic experiment behavior.
- `requirements.txt` – Empty runtime dependency list (only standard library is used).

## How the simulation works

### Incident generation

- `IncidentGenerator` produces a deterministic list of incidents given a random seed.
- Incidents are typed according to the workload specification:
  - `prompt_regression`
  - `routing_misconfiguration`
  - `rag_retrieval_degradation`
  - `tool_failure`
  - `latency_cost_regression`
- Each incident has:
  - `detected_at` (simulation time in minutes from 0)
  - `severity`
  - ground-truth `incident_type` and `canonical_remediation`.

### RCA and remediation pipeline

- `RCAEngine` takes ground-truth incidents and emits structured RCA outputs with:
  - `incident_id`, `detected_at`, `incident_type`, `severity`
  - `suspected_root_causes`, `recommended_actions`, `confidence_score`.
- `ActionMapper` converts RCA `recommended_actions` into **concrete remediation actions** like:
  - `toggle_feature_flag`
  - `rollback_prompt`
  - `update_routing`
  - `disable_tool`
  - `rollback_model`.

### Baseline vs. Treatment

Both variants reuse the **same incidents and RCA outputs** to ensure comparability.

#### Shared components

- A simple **event-driven simulation loop** walks time forward (in minutes) and triggers detections and remediations.
- Incident resolution is modeled as:
  - When the **canonical remediation** is applied, the incident resolves after a short fixed delay.
  - Non-canonical / incorrect actions may cause extra actions (thrash) and rollbacks.

#### Baseline (manual remediation)

- No orchestrator.
- A `ManualResponder` applies remediations with longer, more variable latencies:
  - Decision latency before first action.
  - Execution latency per action.
- There are **no guardrails** besides a simple mapping: the responder attempts the canonical remediation but is slower.

#### Treatment (automated orchestrator)

- `RemediationOrchestrator` consumes RCA outputs and applies actions under guardrails:
  - **Risk-aware policies**: each incident type maps to a risk level.
  - **Automation policy**:
    - Low risk: auto-apply immediately.
    - Medium risk: synthetic human approval latency is injected before execution.
    - High risk: not auto-applied in this toy setup.
  - **Blast-radius limit**: modeled as a cap on max concurrent automated actions.
  - **Rollback logic**: if an incorrect action is applied, a rollback is scheduled after a delay, marking the action as `rolled_back` and incrementing rollback counters.

### Metrics

Per incident and per run, the simulator records:

- `mttr_minutes` – Time from detection to resolution.
- `time_to_first_mitigation_minutes` – Time to first remediation action.
- `num_remediations_per_incident` – Count of actions applied.
- `had_incorrect_remediation` – True if any action was non-canonical.
- `had_unsafe_change` – True if our simple guardrails were violated (e.g., too many concurrent actions in treatment).
- `num_rollbacks` – Count of rolled-back actions.
- `recurrence_within_window` – True if a similar incident recurs soon after resolution (rare in this simplified model but wired for extensibility).
- `orchestrator_decision_latency_seconds_mean` – For treatment: decision latency between RCA and orchestrator choice.
- `human_approval_latency_minutes_mean` – For actions routed through approvals.

The top-level `run.py` then aggregates metrics across incidents into simple run-level summaries.

## Evidence contract

Running `python run.py` writes `/evidence/results.json` (or `${BOOKMAS_EVIDENCE_DIR}/results.json`) with this structure:

```json
{
  "chapter": 12,
  "experiment_id": "exp-12-automated-remediation-guardrails-mttr",
  "environment": {"os": "...", "python": "..."},
  "runs": [
    {
      "variant": "baseline",
      "workload_id": "workload_incident_mix_v1",
      "run_id": "workload_incident_mix_v1_seed_123_baseline",
      "success": true,
      "metrics": {
        "mttr_minutes_mean": 4.2,
        "mttr_minutes_median": 4.0,
        "time_to_first_mitigation_minutes_mean": 2.1,
        "num_remediations_per_incident_mean": 1.0
      }
    },
    {
      "variant": "treatment",
      "workload_id": "workload_incident_mix_v1",
      "run_id": "workload_incident_mix_v1_seed_123_treatment",
      "success": true,
      "metrics": {
        "mttr_minutes_mean": 2.7,
        "mttr_minutes_median": 2.5,
        "time_to_first_mitigation_minutes_mean": 0.9,
        "num_remediations_per_incident_mean": 1.1
      }
    }
  ],
  "notes": "...optional human-readable explanation..."
}
``

Actual metric values depend on the simulation but always follow this schema. **All metric values are numeric**; any textual commentary appears only in `notes` or other non-metric fields.

At least one baseline and one treatment run are produced for the shared workload.

## Running the experiment

From the project root:

```bash
python run.py
```

- This will run:
  - A baseline simulation with seed `123`.
  - A treatment simulation with the same seed.
- Evidence will be written to:
  - `${BOOKMAS_EVIDENCE_DIR:-/evidence}/results.json`.

You can inspect that file to see per-run metrics.

## Running tests

```bash
python -m unittest discover -s tests -p "test_*.py"
```

The tests verify that:

- `run.py` writes a JSON file at the expected path.
- The top-level schema matches the required contract.
- There is at least one baseline and one treatment run for the workload.
- All metrics are numeric and finite values.

## Design notes and limitations

- The project avoids external dependencies and networking; everything is in-memory and purely deterministic.
- The simulator uses minutes as the time unit but advances time in discrete steps (no real sleeping or wall-clock delays).
- Many elements of the full specification (Kafka topics, HTTP feature flag services, etc.) are represented as in-process abstractions rather than actual services.
- Only a subset of the very rich metric schema from the specification is aggregated into the compact `metrics` dict in `results.json`; adding more metrics is straightforward if needed.

This mini-project is designed for reproducibility and educational clarity rather than production-readiness.
