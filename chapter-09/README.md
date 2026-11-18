# Chapter 9 Prompt / Policy / Hallucination RCA – Offline Experiment

This is a **self-contained, offline Python 3.11+ project** that simulates the
experiment described in the specification for:

- Chapter: **9**
- Experiment ID: **chap9-prompt-policy-hallucination-rca-v1**

The purpose is to:

- Implement a **baseline** vs. **treatment** RCA setup.
- Specialize RCA for **prompt, policy, and hallucination failures**.
- Produce **reproducible evidence** in `/evidence/results.json` following the
  required schema.

The project uses **only the Python standard library**; there are **no external
runtime dependencies or network calls**. All RAG, LLM, and policy behavior is
simulated deterministically to enable fair offline comparisons.

## Project layout

- `run.py` – Main entrypoint that runs all workloads for baseline and
  treatment, gathers metrics, and writes `/evidence/results.json`.
- `requirements.txt` – Empty of runtime dependencies (standard library only).
- `rca/` – Core simulation and RCA logic.
  - `__init__.py`
  - `prompt_registry.py` – Treatment-only prompt/template registry,
    version metadata, and diffs.
  - `evaluators.py` – Simulated LLM and non-LLM judges.
  - `content_attribution.py` – Layered attribution logic for hallucinations
    and policy failures.
  - `prompt_rca.py` – Prompt regression detection using rolling windows and
    simple non-parametric comparison.
  - `policy_rca.py` – Policy misconfiguration detection.
  - `workloads.py` – Encodes W1, W2, W3 workloads and their phases.
  - `simulation.py` – Simulated RAG system, retrieval, prompts, and policy
    engine that generate interaction events.
  - `experiment_runner.py` – Orchestrates running all workloads under
    baseline and treatment.
- `services/`
  - `prompt_content_rca_service.py` – Treatment-style service abstraction
    that consumes enriched interaction events and produces RCA annotations.
- `scripts/`
  - `run_chap9_experiment.py` – Thin wrapper around the experiment runner
    (not used by tests; `run.py` is the main entry here).
- `tests/`
  - `test_experiment.py` – Verifies evidence schema and minimal behavioral
    properties using **only** the standard library.

## What is simulated vs. real?

**Simulated (offline):**

- LLM responses, RAG retrieval, and policy engine decisions.
- LLM and non-LLM judges for hallucinations.
- Prompt/template versions and regressions.
- Retrieval degradation and policy configuration changes.

**Real (measured):**

- Wall-clock execution time for each run (per workload and variant).
- Counts of interaction events processed.
- Simple numeric metrics derived from the simulated traces, such as:
  - `num_requests`
  - `hallucination_rate`
  - `policy_violation_rate`
  - `mean_rca_processing_latency_ms`
  - `runtime_seconds`

These provide a minimal but concrete and reproducible quantitative basis for
comparing baseline vs. treatment.

## Baseline vs. treatment in this project

The simulation encodes the conceptual differences described in the
specification:

- **Baseline**
  - Generic interaction events with limited metadata.
  - Simple hallucination flag from a single LLM-like judge without access to
    retrieval or prompt metadata.
  - No prompt template registry or version-aware analysis.
  - No explicit policy rule identifiers or content-aware attribution.

- **Treatment**
  - Events are enriched with **prompt template IDs/versions**, prompt
    metadata, retrieval metrics, and policy configuration details.
  - Uses both a simulated **LLM judge** and a **heuristic judge**, then
    aggregates into a consensus hallucination label and confidence.
  - Runs **prompt regression detection** per template version.
  - Runs **policy misconfiguration detection**.
  - Uses **layered attribution** to assign probabilities over
    `{prompt, retrieval, model, policy}` as candidate root causes.

The implementation is deliberately small and deterministic so that it can run
reliably in a constrained sandbox, but the data structures and processing flow
mirror the richer real-world design.

## Evidence format

Running `python run.py` produces `/evidence/results.json` (or another
directory if `BOOKMAS_EVIDENCE_DIR` is set) with this exact top-level schema:

```json
{
  "chapter": 9,
  "experiment_id": "chap9-prompt-policy-hallucination-rca-v1",
  "environment": {"os": "...", "python": "..."},
  "runs": [
    {
      "variant": "baseline",
      "workload_id": "W1-prompt-regression-detection",
      "run_id": "...",
      "success": true,
      "metrics": {
        "num_requests": 120.0,
        "hallucination_rate": 0.25,
        "runtime_seconds": 0.42
      }
    },
    {
      "variant": "treatment",
      "workload_id": "W1-prompt-regression-detection",
      "run_id": "...",
      "success": true,
      "metrics": {
        "num_requests": 120.0,
        "hallucination_rate": 0.18,
        "runtime_seconds": 0.51
      }
    }
    // plus baseline and treatment for W2 and W3
  ],
  "notes": "..."
}
```

**Important constraints satisfied by this project:**

- At least **one baseline and one treatment run per workload** (W1, W2, W3).
- **Every metric value is a finite JSON number** (no strings, booleans,
  lists, nulls, or objects).
- Any aspects that cannot be measured offline (e.g., real network latency or
  cloud LLM costs) are **omitted from `metrics`** and discussed only in
  `notes` if at all.

Additional explanatory data **may** be included at the top level or as
non-metric fields in each run, but tests only assert the required parts of the
schema.

## How to run

1. Ensure you are using **Python 3.11+**.

2. (Optional) Create and activate a virtual environment.

3. Install requirements (standard library only, but this is a no-op for
   consistency):

   ```bash
   pip install -r requirements.txt
   ```

4. Run the experiment:

   ```bash
   python run.py
   ```

   This will:
   - Run baseline and treatment for **W1**, **W2**, and **W3**.
   - Write `/evidence/results.json` (or `$BOOKMAS_EVIDENCE_DIR/results.json`).

5. Run tests:

   ```bash
   python -m unittest discover -s tests -p "test_*.py"
   ```

## Design notes

- The simulation uses simple numeric heuristics to approximate the behavior
  described in the narrative specification:
  - Prompt regressions increase hallucination probabilities in W1.
  - Retrieval degradation increases hallucinations in W2.
  - Policy configuration affects policy violations in W3.
- Treatment instrumentation introduces extra per-request processing, which is
  reflected in `mean_rca_processing_latency_ms` and slightly longer
  `runtime_seconds`, but not enough to cause timeouts.
- All random sampling is controlled via fixed seeds per run so baseline and
  treatment compare fairly.

## Limitations

- There is **no actual external LLM or vector database**; everything is
  simulated.
- True wall-clock timing inside the sandbox may vary slightly between
  environments, but the overall structure and relative differences are
  reproducible.
- Many chapter metrics (like time to human-confirmed root cause) cannot be
  realistically measured offline and are therefore excluded from the
  `metrics` object.
