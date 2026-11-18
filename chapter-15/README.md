# Chapter 15 – End-to-End RCA Case Studies (Offline Experiment Harness)

This mini-project implements a **self-contained, fully offline** Python 3.11+ experiment
for the chapter:

> **15 – End-to-End Case Studies: Automated RCA for Real LLM Incidents**

It simulates three LLM incident case studies with **baseline (manual)** and
**treatment (automated RCA)** pipelines and writes evidence in a standard JSON
format consumable by the book's tooling.

The implementation is intentionally lightweight and deterministic:

* No network calls, containers, or external services.
* The "LLM stack" and incidents are modeled with simple in-memory stochastic
  processes.
* The **baseline** and **treatment** differ only in the quality of their
  detection and diagnosis algorithms and thresholds, not in the underlying
  synthetic system behavior.

This keeps the project runnable in an offline sandbox while still making the
**comparative experiment structure, metrics, and RCA workflows** concrete.

---

## Contents

Key files:

* `run.py` – main entry point. Runs all workloads under baseline & treatment,
  records synthetic metrics, and writes `/evidence/results.json`.
* `experiment/simulator.py` – core simulation of the LLM service, incidents,
  and observability signals.
* `experiment/rca_baseline.py` – manual/dashboard-like RCA logic.
* `experiment/rca_treatment.py` – automated RCA logic with better signals.
* `experiment/runner.py` – orchestrates workloads, variants, and aggregation
  into the evidence schema.
* `tests/test_experiment.py` – unittests that validate the evidence file's
  schema and basic invariants.

There are **no external Python dependencies**; everything uses the standard
library.

---

## Installation

Requirements:

* Python **3.11+** (3.11 or newer is recommended).

Install (there is nothing to install, but to keep parity with the book's
instructions you can run):

```bash
pip install -r requirements.txt
```

This will be a no-op because `requirements.txt` is empty.

---

## Running the Experiment

From the project root:

```bash
python run.py
```

This will:

1. Detect the evidence directory from the environment variable
   `BOOKMAS_EVIDENCE_DIR`. If unset, it defaults to `/evidence`.
2. Run all three workloads, each under both variants:
   * `baseline`
   * `treatment`
3. For each `(workload, variant)` pair it performs two independent runs
   (configurable inside `experiment/runner.py`).
4. Collect the following **numeric metrics** per run:
   * `avg_latency_ms` – average per-request latency across the run.
   * `error_rate` – fraction of failing requests.
   * `time_to_detection` – simulated detection delay (seconds) for the
     incident, derived from alerting logic.
5. Aggregate results and write them to:

   ```
   /evidence/results.json
   ```

   in the required schema:

   ```json
   {
     "chapter": 15,
     "experiment_id": "ch15-end-to-end-rca-case-studies-e2e-llm-incidents-v1",
     "environment": {"os": "...", "python": "..."},
     "runs": [
       {
         "variant": "baseline",
         "workload_id": "workload-cs1-hallucination-spike-after-data-refresh",
         "run_id": "...",
         "success": true,
         "metrics": {
           "avg_latency_ms": 12.3,
           "error_rate": 0.05,
           "time_to_detection": 42.0
         }
       },
       {
         "variant": "treatment",
         "workload_id": "workload-cs1-hallucination-spike-after-data-refresh",
         "run_id": "...",
         "success": true,
         "metrics": { ... }
       }
       // ... more runs for CS2 and CS3 ...
     ],
     "notes": "..."
   }
   ```

The sandbox in which your code runs will provide a writable `/evidence`
folder. If it uses a different directory, it should set
`BOOKMAS_EVIDENCE_DIR` accordingly.

---

## Running Tests

To run the test suite:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

The tests will:

1. Invoke `run.py` (via an imported function) to generate a fresh
   `results.json` in a **temporary evidence directory**.
2. Validate that:
   * The top-level schema matches the contract.
   * There are runs for all three workloads.
   * For each workload, at least one `baseline` and one `treatment` run
     exists.
   * Every run has numeric metrics and correct field types.

---

## Design Notes

### Offline RCA Simulation

This project cannot use real LLMs or observability stacks. Instead, it
implements a small synthetic environment that captures the *structure* of the
chapter's case studies:

* **Workload CS1 – Hallucination spike after data refresh**
  * Incident: at a configured time, the "retrieval quality" parameter drops.
  * Effect: higher logical error rate, slightly higher latency.
  * Treatment RCA has better detection of the hallucination-type incident,
    leading to a shorter simulated time-to-detection.

* **Workload CS2 – Latency and cost regressions from routing misconfig**
  * Incident: routing weight shifts to a slower model.
  * Effect: higher latency, no improvement in logical error rate.

* **Workload CS3 – Cascading failures from broken tool integration**
  * Incident: tool error rate spikes and then becomes an outage.
  * Effect: significantly higher error rate and latency.

For each workload, we model the system as a sequence of discrete time steps
("ticks"). Each tick generates synthetic metrics, and the RCA logic
(baseline/treatment) acts only on those metrics.

### Baseline vs Treatment

* **Baseline** imitates manual RCA:
  * Higher thresholds for anomaly detection.
  * Slower polling interval (simulated as needing more evidence before
    declaring an incident).
  * Uses fewer signal dimensions (e.g., primarily latency and overall
    error rate).

* **Treatment** imitates an automated RCA stack:
  * More sensitive/higher-quality detectors for each incident type
    (hallucination spike, latency-only regression, cascading tool failures).
  * Uses specialized features (retrieval health, routing distribution,
    tool health) when deciding if an incident has occurred.
  * As a result, it typically achieves **lower time-to-detection**.

To remain faithful to the instructions:

* We **do not fabricate metrics**. All reported metrics are computed directly
  from the simulated system's time series.
* We avoid real clocks and external side effects; the simulation advances its
  own logical time.

---

## Limitations

The full chapter describes many metrics (MTTR, hypothesis accuracy,
false-diagnosis rate, etc.) that require real humans in the loop, full
observability, and RCA tooling.

In this offline sandbox we **cannot** collect:

* Actual human investigation timelines.
* Real alert precision/recall based on noisy data.
* Hypothesis tracking or correctness.

Therefore, the implementation focuses on a **small, reliable subset of
numeric metrics** derived from the simulator:

* `avg_latency_ms`
* `error_rate`
* `time_to_detection`

The evidence format and code structure, however, are designed so that richer
metrics could be plugged in if the simulation were replaced by a live system.

---

## Extending the Experiment

If you want to explore more of the chapter's ideas:

* Extend `experiment/simulator.py` to track explicit incident phases and
  recovery actions.
* Implement synthetic RCA hypotheses and scoring, and capture them in a
  richer evidence schema.
* Add additional metrics to `metrics` for each run (ensuring they remain
  numeric and are directly computed from the simulation state).

This small harness is intended as a **minimal, reproducible scaffold** for
those future extensions.
