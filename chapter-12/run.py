import json
import os
import sys
import platform
from pathlib import Path

from experiment.simulation import run_experiment_pair


CHAPTER_NUMBER = 12
EXPERIMENT_ID = "exp-12-automated-remediation-guardrails-mttr"
WORKLOAD_ID = "workload_incident_mix_v1"
DEFAULT_SEED = 123


def main() -> None:
    # Run one baseline and one treatment simulation with the same seed
    seed = DEFAULT_SEED
    baseline_result, treatment_result = run_experiment_pair(
        workload_id=WORKLOAD_ID,
        seed=seed,
    )

    # Build evidence structure
    evidence_dir = os.environ.get("BOOKMAS_EVIDENCE_DIR", "/evidence")
    evidence_path = Path(evidence_dir) / "results.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)

    environment = {
        "os": platform.platform(),
        "python": sys.version.split()[0],
    }

    runs = []
    runs.append({
        "variant": "baseline",
        "workload_id": WORKLOAD_ID,
        "run_id": baseline_result["run_id"],
        "success": bool(baseline_result.get("success", True)),
        "metrics": baseline_result["metrics"],
    })
    runs.append({
        "variant": "treatment",
        "workload_id": WORKLOAD_ID,
        "run_id": treatment_result["run_id"],
        "success": bool(treatment_result.get("success", True)),
        "metrics": treatment_result["metrics"],
    })

    evidence = {
        "chapter": CHAPTER_NUMBER,
        "experiment_id": EXPERIMENT_ID,
        "environment": environment,
        "runs": runs,
        "notes": (
            "Deterministic simulation comparing manual (baseline) vs. "
            "guarded automated (treatment) remediation orchestrator."
        ),
    }

    with evidence_path.open("w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
