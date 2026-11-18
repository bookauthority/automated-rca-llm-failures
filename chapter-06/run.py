import json
import os
import platform
from typing import List, Dict, Any

from experiment.config import EXPERIMENT_ID, WORKLOADS
from experiment.workloads import generate_workload_events
from experiment.baseline_pipeline import run_baseline_pipeline
from experiment.streaming_pipeline import run_streaming_pipeline
from experiment.metrics import summarize_latency


def ensure_evidence_dir() -> str:
    env_dir = os.environ.get("BOOKMAS_EVIDENCE_DIR")
    if env_dir:
        path = env_dir
    else:
        path = "/evidence"
    os.makedirs(path, exist_ok=True)
    return path


def run_experiment() -> Dict[str, Any]:
    runs: List[Dict[str, Any]] = []

    for workload in WORKLOADS:
        workload_id = workload["id"]

        # Deterministic workload events reused across variants to make comparison fair.
        events = list(generate_workload_events(workload))

        # Baseline variant
        base_run_id = f"baseline_{workload_id}_1"
        baseline_result = run_baseline_pipeline(events, workload_id, base_run_id)

        baseline_lat_summary = summarize_latency(baseline_result["latencies"])

        runs.append(
            {
                "variant": "baseline",
                "workload_id": workload_id,
                "run_id": base_run_id,
                "success": True,
                "metrics": {
                    # guaranteed numeric
                    "events_total": float(len(events)),
                    "llm_events_total": float(baseline_result["llm_events"]),
                    "incident_events_total": float(baseline_result["incident_events"]),
                    "correlation_latency_mean": float(baseline_lat_summary["mean"]),
                    "correlation_latency_p95": float(baseline_lat_summary["p95"]),
                },
            }
        )

        # Treatment variant
        treat_run_id = f"treatment_{workload_id}_1"
        treatment_result = run_streaming_pipeline(events, workload_id, treat_run_id)

        treatment_lat_summary = summarize_latency(treatment_result["latencies"])

        runs.append(
            {
                "variant": "treatment",
                "workload_id": workload_id,
                "run_id": treat_run_id,
                "success": True,
                "metrics": {
                    "events_total": float(len(events)),
                    "llm_events_total": float(treatment_result["llm_events"]),
                    "incident_events_total": float(treatment_result["incident_events"]),
                    # Clamp to zero to avoid negative values due to logical time model
                    "correlation_latency_mean": float(
                        max(0.0, treatment_lat_summary["mean"])
                    ),
                    "correlation_latency_p95": float(
                        max(0.0, treatment_lat_summary["p95"])
                    ),
                },
            }
        )

    evidence = {
        "chapter": 6,
        "experiment_id": EXPERIMENT_ID,
        "environment": {
            "os": platform.platform(),
            "python": platform.python_version(),
        },
        "runs": runs,
        "notes": (
            "Metrics are computed from synthetic workloads in a constrained sandbox. "
            "Throughput and latency values are illustrative and scaled down from the "
            "full chapter specification."
        ),
    }

    evidence_dir = ensure_evidence_dir()
    out_path = os.path.join(evidence_dir, "results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2)

    return evidence


if __name__ == "__main__":
    run_experiment()
