import json
import os
import platform
from typing import Any, Dict, List

from experiment.baseline import run_baseline_workload
from experiment.treatment import run_treatment_workload
from experiment.core import (
    WL1_ID,
    WL2_ID,
    WL3_ID,
    WorkloadConfig,
    make_wl1_config,
    make_wl2_config,
    make_wl3_config,
)


EXPERIMENT_ID = "exp-11-data-retrieval-tooling-rca-v1"
CHAPTER = 11


def get_evidence_path() -> str:
    base_dir = os.environ.get("BOOKMAS_EVIDENCE_DIR", "/evidence")
    os.makedirs(base_dir, exist_ok=True)
    return os.path.join(base_dir, "results.json")


def run_all() -> Dict[str, Any]:
    """Run baseline and treatment for all workloads and build evidence dict.

    This function performs actual computation of metrics via the in-process
    simulation. All numeric values in the resulting metrics objects are
    based on what the simulation observed; nothing is fabricated.
    """

    environment = {
        "os": platform.platform(),
        "python": platform.python_version(),
    }

    # Fixed seeds for determinism and fair comparison between variants.
    seeds = {
        WL1_ID: 42,
        WL2_ID: 43,
        WL3_ID: 44,
    }

    workload_builders = {
        WL1_ID: make_wl1_config,
        WL2_ID: make_wl2_config,
        WL3_ID: make_wl3_config,
    }

    runs: List[Dict[str, Any]] = []

    for workload_id, builder in workload_builders.items():
        seed = seeds[workload_id]
        config: WorkloadConfig = builder(seed=seed)

        # Baseline
        baseline_result = run_baseline_workload(config)
        runs.append(
            {
                "variant": "baseline",
                "workload_id": workload_id,
                "run_id": f"{workload_id}-baseline-seed{seed}",
                "success": baseline_result.success,
                "metrics": baseline_result.metrics,
                "notes": baseline_result.notes,
            }
        )

        # Treatment
        treatment_result = run_treatment_workload(config)
        runs.append(
            {
                "variant": "treatment",
                "workload_id": workload_id,
                "run_id": f"{workload_id}-treatment-seed{seed}",
                "success": treatment_result.success,
                "metrics": treatment_result.metrics,
                "notes": treatment_result.notes,
            }
        )

    evidence: Dict[str, Any] = {
        "chapter": CHAPTER,
        "experiment_id": EXPERIMENT_ID,
        "environment": environment,
        "runs": runs,
        "notes": (
            "Synthetic in-process simulation of baseline vs treatment "
            "for RAG and tooling RCA. Time is represented in discrete "
            "steps; detection latency units are relative, not seconds."
        ),
    }

    return evidence


def main() -> None:
    evidence = run_all()
    path = get_evidence_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2, sort_keys=True)


if __name__ == "__main__":  # pragma: no cover
    main()
