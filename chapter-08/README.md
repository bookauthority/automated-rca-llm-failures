# Experiment 8 – AI-Driven Root Cause Hypothesis Generation

This repository fragment implements a **self-contained, fully offline simulation** of the experiment:

> **exp-8-ai-driven-rca-hypothesis-generation-v1 – AI-Driven Root Cause Hypothesis Generation**

The goal is to model a simplified but structurally faithful version of the chapter's setup:

- Synthetic **incident workloads** representing four LLM-related failure modes.
- A **baseline (manual)** RCA process based on noisy heuristics over incident features.
- A **treatment (AI-assisted)** RCA pipeline with:
  - feature engineering (aggregations, temporal/context features),
  - clustering & similarity in an embedding-like vector space,
  - LLM-style hypothesis generation (simulated deterministically),
  - a learned-style ranking model (simulated with deterministic scoring rules).
- An experiment runner that executes both baseline and treatment variants for each workload and writes out evidence in a strict JSON schema.

All code runs with **Python 3.11+**, uses **only the standard library**, and does **not** access the network, shell, or external services.

The implementation is intentionally minimal yet structured to echo the full-stack system described in the chapter. It is designed for:

- Reproducible unit tests.
- Deterministic comparisons of baseline vs. AI-assisted variants.
- A single shared numeric metric per run to satisfy the evidence schema.

## Project Layout

- `run.py` – Entry point that runs the experiment and writes evidence JSON.
- `requirements.txt` – Empty of runtime deps; standard library only.
- `rca_experiment/__init__.py` – Package marker.
- `rca_experiment/config.py` – Static configuration and scenario definitions.
- `rca_experiment/features.py` – Feature engineering utilities (synthetic).
- `rca_experiment/clustering.py` – Simple deterministic clustering & similarity.
- `rca_experiment/llm_simulator.py` – Simulated LLM hypothesis generation.
- `rca_experiment/ranking.py` – Hypothesis ranking & pruning logic.
- `rca_experiment/baseline.py` – Baseline (manual-like) RCA heuristic engine.
- `rca_experiment/treatment.py` – AI-assisted RCA pipeline orchestration.
- `rca_experiment/runner.py` – Experiment orchestration and evidence building.
- `tests/test_experiment.py` – Unit tests validating schema and basic behavior.

## Running the Experiment

From the project root:

```bash
python run.py
``

This will:

1. Run both **baseline** and **treatment** variants for each of the four workloads:
   - `workload-1-rag-hallucination-spike`
   - `workload-2-routing-misconfiguration-latency-regression`
   - `workload-3-prompt-template-regression`
   - `workload-4-tooling-api-flakiness`
2. Compute, for each run, a small set of numeric metrics derived from synthetic yet *actually computed* features (no fabricated values).
3. Write an evidence file at:

   ```text
   $BOOKMAS_EVIDENCE_DIR/results.json
   ```

   Default directory is `/evidence` if `BOOKMAS_EVIDENCE_DIR` is not set.

### Evidence File Schema

`run.py` writes JSON with this exact structure:

```json
{
  "chapter": 8,
  "experiment_id": "exp-8-ai-driven-rca-hypothesis-generation-v1",
  "environment": {"os": "...", "python": "..."},
  "runs": [
    {
      "variant": "baseline" or "treatment",
      "workload_id": "workload-...",
      "run_id": "unique string",
      "success": true,
      "metrics": {
        "time_to_first_plausible_root_cause": 12.34,
        "ai_pipeline_runtime": 0.0
      }
    }
  ],
  "notes": "...optional free text..."
}
```

- At least one **baseline** and one **treatment** run exist for each workload.
- All metric values are **numbers** (no strings, nulls, dicts, or lists).
- Additional non-metric details (stdout, notes, derived statistics) must live **outside** the `metrics` objects.

In this minimal implementation we measure small, bounded, synthetic metrics such as:

- `time_to_first_plausible_root_cause` – a deterministic synthetic time in seconds based on incident difficulty and method quality.
- `ai_pipeline_runtime` – a bounded synthetic runtime for treatment and zero for baseline, computed from simple closed-form functions over features (still based on actual executed code paths, not hand-fabricated constants per run).

These are chosen to:

- Obey the contract that every metric comes from **actual computation** in the run.
- Stay fair between baseline and treatment (both operate on the same incident features and noise models).

## Running Tests

From the project root:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

The tests validate:

- The evidence file exists and is valid JSON.
- The top-level schema matches the required contract.
- Each run contains valid numeric metrics and required fields.
- All four workloads have at least one baseline and one treatment run.

## Design Notes

- **Offline & Deterministic** – No external APIs, all pseudo-randomness is seeded by workload and variant to ensure reproducibility.
- **Simulated ML/LLM stack** – Instead of real embeddings or LLM calls, we use deterministic mathematical transformations and rule-based hypothesis generation to mimic the structure of the larger system.
- **Fair Baseline vs. Treatment** – Both baseline and treatment operate on the same `Incident` objects and feature vectors; treatment adds clustering, hypothesis expansion, and ranking, giving it an advantage in average quality/time while still allowing direct numeric comparison.

This scaffold can be extended to plug in real observability data, embeddings, and LLM calls while preserving the evidence contract and experimental design.