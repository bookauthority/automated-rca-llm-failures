from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List, Tuple

from .rca_baseline import BaselineRCA
from .rca_treatment import TreatmentRCA
from .simulator import (
    WorkloadConfig,
    WorkloadID,
    WorkloadSimulator,
    build_default_workload_configs,
)


@dataclass
class RunMetrics:
    avg_latency_ms: float
    error_rate: float
    time_to_detection: float


def _run_single_simulation(config: WorkloadConfig, variant: str, rca_detector) -> Tuple[RunMetrics, bool, str]:
    """Run one deterministic simulation for a workload and variant.

    Returns metrics, success flag, and a human-readable note fragment.
    """

    simulator = WorkloadSimulator(config)
    ticks = simulator.run()

    # Compute average latency and error rate across all ticks.
    total_latency = 0.0
    total_error = 0.0
    count = float(len(ticks)) if ticks else 1.0

    for t in ticks:
        total_latency += t.latency_ms
        total_error += t.error_rate

    avg_latency_ms = total_latency / count
    avg_error_rate = total_error / count

    detection_result = rca_detector.detect(config.workload_id, ticks)

    # If nothing is detected, record time_to_detection as the full
    # simulation duration; this is deterministic and numeric.
    if detection_result.detected and detection_result.detection_time_s is not None:
        time_to_detection = float(detection_result.detection_time_s)
    else:
        time_to_detection = float(config.total_ticks)

    metrics = RunMetrics(
        avg_latency_ms=avg_latency_ms,
        error_rate=avg_error_rate,
        time_to_detection=time_to_detection,
    )

    # All simulations complete successfully in this synthetic harness.
    success = True

    note_fragment = (
        f"variant={variant} workload={config.workload_id.value} "
        f"avg_latency_ms={avg_latency_ms:.3f} error_rate={avg_error_rate:.3f} "
        f"time_to_detection={time_to_detection:.3f}"
    )
    return metrics, success, note_fragment


def run_all_experiments() -> Tuple[List[Dict], str]:
    """Run all workloads for both baseline and treatment.

    Returns a tuple of (runs_list, notes_string) where runs_list is ready to
    be embedded into the evidence JSON under the `runs` key.
    """

    cs1, cs2, cs3 = build_default_workload_configs()
    workload_configs = [cs1, cs2, cs3]

    baseline_rca = BaselineRCA()
    treatment_rca = TreatmentRCA()

    runs: List[Dict] = []
    note_fragments: List[str] = []

    # At least one baseline and one treatment run per workload are required.
    # We choose 2 runs per (workload, variant) to get slightly more data while
    # staying well within resource limits.
    runs_per_variant = 2

    for config in workload_configs:
        for variant, detector in (("baseline", baseline_rca), ("treatment", treatment_rca)):
            for rep in range(runs_per_variant):
                metrics, success, note = _run_single_simulation(config, variant, detector)
                run_id = f"{config.workload_id.value}-{variant}-run{rep+1}"

                run_record: Dict = {
                    "variant": variant,
                    # IMPORTANT: serialize Enum by its .value (the stable ID),
                    # not by str(enum), to satisfy the experiment contract
                    # and ensure tests see correct workload IDs.
                    "workload_id": config.workload_id.value,
                    "run_id": run_id,
                    "success": bool(success),
                    "metrics": {k: float(v) for k, v in asdict(metrics).items()},
                }
                runs.append(run_record)
                note_fragments.append(note)

    notes = " | ".join(note_fragments)
    return runs, notes
