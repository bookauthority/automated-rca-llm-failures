import json
import os
import sys
import time
from pathlib import Path

from typing import Dict, Any, List

# Local imports
from workloads.synthetic_workload import run_workload
from analysis.check_instrumentation_quality import run_analysis


CHAPTER_NUMBER = 5
EXPERIMENT_ID = "exp-ch5-llm-instrumentation-otel-rca-signals-v1"
WORKLOAD_ID = "synthetic-mixed-traffic"


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _env_info() -> Dict[str, str]:
    import platform

    return {
        "os": platform.platform(),
        "python": sys.version.split()[0],
    }


def main() -> None:
    base_dir = Path.cwd()
    runs_dir = base_dir / "runs"
    baseline_dir = runs_dir / "baseline"
    treatment_dir = runs_dir / "treatment"
    _ensure_dir(baseline_dir)
    _ensure_dir(treatment_dir)

    # Run baseline workload (instrumentation disabled)
    baseline_metrics_path = baseline_dir / "metrics.json"
    baseline_events_path = baseline_dir / "events.jsonl"  # not used in baseline
    baseline_result = run_workload(
        variant="baseline",
        output_metrics_path=baseline_metrics_path,
        output_events_path=baseline_events_path,
        seed=42,
    )

    # Run treatment workload (instrumentation enabled)
    treatment_metrics_path = treatment_dir / "metrics.json"
    treatment_events_path = treatment_dir / "events.jsonl"
    treatment_result = run_workload(
        variant="treatment",
        output_metrics_path=treatment_metrics_path,
        output_events_path=treatment_events_path,
        seed=42,
    )

    # Run simple analysis (non-metric informational summary)
    analysis_path = runs_dir / "summary_report.json"
    analysis_summary = run_analysis(
        baseline_metrics_path=baseline_metrics_path,
        treatment_metrics_path=treatment_metrics_path,
        events_path=treatment_events_path,
        output_report_path=analysis_path,
    )

    # Prepare evidence
    evidence_dir = Path(os.environ.get("BOOKMAS_EVIDENCE_DIR", "/evidence"))
    _ensure_dir(evidence_dir)
    evidence_path = evidence_dir / "results.json"

    runs: List[Dict[str, Any]] = []

    # Baseline run entry
    runs.append(
        {
            "variant": "baseline",
            "workload_id": WORKLOAD_ID,
            "run_id": "baseline-1",
            "success": baseline_result.get("success", True),
            # Only numeric metrics inside metrics
            "metrics": {
                "gateway_p95_latency_ms": float(baseline_result["gateway_p95_latency_ms"]),
                "gateway_mean_latency_ms": float(baseline_result["gateway_mean_latency_ms"]),
                "gateway_error_rate": float(baseline_result["gateway_error_rate"]),
                "total_requests": float(baseline_result["total_requests"]),
            },
        }
    )

    # Treatment run entry (includes at least one instrumentation-related numeric metric)
    runs.append(
        {
            "variant": "treatment",
            "workload_id": WORKLOAD_ID,
            "run_id": "treatment-1",
            "success": treatment_result.get("success", True),
            "metrics": {
                "gateway_p95_latency_ms": float(treatment_result["gateway_p95_latency_ms"]),
                "gateway_mean_latency_ms": float(treatment_result["gateway_mean_latency_ms"]),
                "gateway_error_rate": float(treatment_result["gateway_error_rate"]),
                "total_requests": float(treatment_result["total_requests"]),
                # Simple instrumentation coverage proxy
                "events_per_request_mean": float(
                    treatment_result.get("events_per_request_mean", 0.0)
                ),
            },
        }
    )

    evidence: Dict[str, Any] = {
        "chapter": CHAPTER_NUMBER,
        "experiment_id": EXPERIMENT_ID,
        "environment": _env_info(),
        "runs": runs,
        "notes": "Synthetic local experiment; some metrics from the full chapter spec (e.g., OTLP export error rate) cannot be measured in this offline sandbox and are therefore omitted.",
        "analysis_summary": analysis_summary,
    }

    with evidence_path.open("w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2)


if __name__ == "__main__":
    main()
