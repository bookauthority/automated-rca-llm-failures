import json
import os
import platform
import uuid
from typing import Dict, List, Tuple

from experiment.config import WORKLOAD_CONFIGS, RNG_SEED
from experiment.events import generate_workload_events
from experiment.detectors import BaselineDetector, TreatmentDetector, DetectionResult
from experiment.metrics import (
    compute_avg_latency,
    compute_failure_event_rate,
    compute_detection_and_fp_rates,
)


CHAPTER = 7
EXPERIMENT_ID = "exp-07-detect-localize-llm-failures-v1"


def run_experiment() -> Dict:
    # Fixed seed for deterministic behaviour across runs
    # Event generation functions will use this base seed combined with workload name.

    results: Dict = {
        "chapter": CHAPTER,
        "experiment_id": EXPERIMENT_ID,
        "environment": {
            "os": platform.platform(),
            "python": platform.python_version(),
        },
        "runs": [],
        "notes": (
            "Synthetic offline experiment with deterministic event generation. "
            "Metrics reflect detection behaviour over simulated LLM interaction events."
        ),
    }

    # Each workload will be executed once for baseline and once for treatment.
    for workload_id, cfg in WORKLOAD_CONFIGS.items():
        # Generate one shared event stream per workload, reused between variants.
        events = generate_workload_events(workload_id, cfg, RNG_SEED)

        for variant in ("baseline", "treatment"):
            if variant == "baseline":
                detector = BaselineDetector()
            else:
                detector = TreatmentDetector()

            detection_results: List[DetectionResult] = []
            for ev in events:
                res = detector.process_event(ev)
                if res is not None:
                    detection_results.append(res)

            # Compute metrics for this variant/workload pair
            avg_latency = compute_avg_latency(events)
            failure_rate = compute_failure_event_rate(events)
            detection_rate, fp_rate = compute_detection_and_fp_rates(
                events, detection_results
            )

            run_entry = {
                "variant": variant,
                "workload_id": workload_id,
                "run_id": f"{workload_id}-{variant}-{uuid.uuid4().hex[:8]}",
                "success": True,
                "metrics": {
                    "avg_latency_ms": float(avg_latency),
                    "failure_event_rate": float(failure_rate),
                    "detection_rate": float(detection_rate),
                    "false_positive_rate": float(fp_rate),
                },
                # Non-metric additional information may be added here if desired.
            }
            results["runs"].append(run_entry)

    return results


def main() -> None:
    evidence_dir = os.environ.get("BOOKMAS_EVIDENCE_DIR", "/evidence")
    os.makedirs(evidence_dir, exist_ok=True)
    results = run_experiment()
    output_path = os.path.join(evidence_dir, "results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
