from __future__ import annotations

import time
from typing import Dict, List

from .baseline import run_baseline_rca
from .config import WORKLOADS, WorkloadConfig
from .features import IncidentFeatures, compute_incident_features
from .treatment import run_treatment_rca


def _build_historical_features() -> Dict[str, IncidentFeatures]:
    """Construct a tiny synthetic historical incident index.

    For simplicity we reuse baseline features across workloads as stand-ins
    for historical incidents.
    """

    historical: Dict[str, IncidentFeatures] = {}
    for wl in WORKLOADS:
        feat = compute_incident_features(wl, variant="baseline")
        key = f"hist-{wl.workload_id}"
        historical[key] = feat
    return historical


def run_experiment() -> Dict[str, object]:
    """Run baseline and treatment RCA for each workload.

    Returns a dictionary with a "runs" list suitable for serialization into
    the evidence file.
    """

    runs: List[Dict[str, object]] = []
    historical = _build_historical_features()

    for wl in WORKLOADS:
        # Baseline run
        baseline_start = time.time()
        baseline_features = compute_incident_features(wl, variant="baseline")
        baseline_result = run_baseline_rca(baseline_features)
        baseline_end = time.time()

        baseline_run = {
            "variant": "baseline",
            "workload_id": wl.workload_id,
            "run_id": f"{wl.workload_id}-baseline-1",
            "success": True,
            "metrics": {
                # Synthetic but computed values (seconds).
                "time_to_first_plausible_root_cause": float(
                    baseline_result.time_to_first_plausible_root_cause
                ),
                # For baseline, AI pipeline runtime is zero by definition.
                "ai_pipeline_runtime": 0.0,
                # Wall-clock runtime of the baseline computation itself.
                "wall_clock_runtime": float(max(0.0, baseline_end - baseline_start)),
            },
        }
        runs.append(baseline_run)

        # Treatment run
        treatment_start = time.time()
        treatment_result = run_treatment_rca(wl, historical)
        treatment_end = time.time()

        treatment_run = {
            "variant": "treatment",
            "workload_id": wl.workload_id,
            "run_id": f"{wl.workload_id}-treatment-1",
            "success": True,
            "metrics": {
                "time_to_first_plausible_root_cause": float(
                    treatment_result.time_to_first_plausible_root_cause
                ),
                "ai_pipeline_runtime": float(treatment_result.ai_pipeline_runtime),
                "wall_clock_runtime": float(max(0.0, treatment_end - treatment_start)),
            },
        }
        runs.append(treatment_run)

    notes = (
        "Synthetic experiment results for exp-8-ai-driven-rca-hypothesis-generation-v1. "
        "All metrics are derived from deterministic, offline computations over "
        "simulated incident features; no external services were contacted."
    )

    return {"runs": runs, "notes": notes}
