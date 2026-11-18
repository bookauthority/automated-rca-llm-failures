import json
import os
import sys
from pathlib import Path

from experiment.baseline import run_baseline_for_workload
from experiment.treatment import run_treatment_for_workload
from experiment.utils import get_environment_info


CHAPTER_NUMBER = 10
EXPERIMENT_ID = "exp-model-drift-routing-rca-ch10"


def get_evidence_path() -> Path:
    base = os.environ.get("BOOKMAS_EVIDENCE_DIR", "/evidence")
    return Path(base) / "results.json"


def main() -> None:
    # Ensure evidence directory exists
    evidence_path = get_evidence_path()
    evidence_path.parent.mkdir(parents=True, exist_ok=True)

    workloads = [
        "eval",  # synthetic_eval_workload
        "prod",  # synthetic_prod_like_workload
    ]

    runs = []
    notes_parts = []

    for workload_id in workloads:
        # Baseline
        baseline_result = run_baseline_for_workload(workload_id)
        runs.append({
            "variant": "baseline",
            "workload_id": workload_id,
            "run_id": baseline_result["run_id"],
            "success": bool(baseline_result["success"]),
            "metrics": baseline_result["metrics"],
        })

        # Treatment
        treatment_result = run_treatment_for_workload(workload_id)
        runs.append({
            "variant": "treatment",
            "workload_id": workload_id,
            "run_id": treatment_result["run_id"],
            "success": bool(treatment_result["success"]),
            "metrics": treatment_result["metrics"],
        })

        # Collect some textual notes outside metrics
        notes_parts.append(
            f"Workload {workload_id}: baseline_n={baseline_result['num_requests']}, "
            f"treatment_n={treatment_result['num_requests']}"
        )

    evidence = {
        "chapter": CHAPTER_NUMBER,
        "experiment_id": EXPERIMENT_ID,
        "environment": get_environment_info(),
        "runs": runs,
        "notes": " | ".join(notes_parts),
    }

    with evidence_path.open("w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - defensive
        # Write a minimal evidence file indicating failure if something goes wrong.
        evidence_path = get_evidence_path()
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        fallback = {
            "chapter": CHAPTER_NUMBER,
            "experiment_id": EXPERIMENT_ID,
            "environment": get_environment_info(),
            "runs": [],
            "notes": f"run.py failed: {type(exc).__name__}: {exc}",
        }
        with evidence_path.open("w", encoding="utf-8") as f:
            json.dump(fallback, f, indent=2, sort_keys=True)
        # Still re-raise to fail tests appropriately
        raise
