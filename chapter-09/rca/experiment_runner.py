from __future__ import annotations

import time
from typing import Any, Dict, List

from .simulation import simulate_workload
from .workloads import define_workloads
from services.prompt_content_rca_service import PromptContentRCAService
from .prompt_rca import compute_hallucination_rate
from .policy_rca import compute_policy_violation_rate


def _aggregate_baseline_metrics(events) -> Dict[str, float]:
    # Baseline uses consensus hallucination label directly and policy decisions.
    total = len(events)
    if total == 0:
        return {
            "num_requests": 0.0,
            "hallucination_rate": 0.0,
            "policy_violation_rate": 0.0,
            "mean_rca_processing_latency_ms": 0.0,
        }

    hall = 0
    viol = 0
    for e in events:
        if e.hallucination_consensus_label in {"mild", "severe"}:
            hall += 1
        if e.policy_decision == "block" and "policy_violation" in e.policy_reason_codes:
            viol += 1

    mean_latency = sum(e.rca_processing_latency_ms for e in events) / float(total)
    return {
        "num_requests": float(total),
        "hallucination_rate": hall / float(total),
        "policy_violation_rate": viol / float(total),
        "mean_rca_processing_latency_ms": mean_latency,
    }


def _aggregate_treatment_metrics(events) -> Dict[str, float]:
    service = PromptContentRCAService()
    core = service.process_events(events)
    # Attach num_requests for comparability.
    core["num_requests"] = float(len(events))
    return core


def _run_single_variant(workload_id: str, variant: str) -> Dict[str, Any]:
    from .workloads import define_workloads as _def

    w = {w.workload_id: w for w in _def()}[workload_id]

    start = time.perf_counter()
    events = simulate_workload(w, variant=variant)
    runtime = time.perf_counter() - start

    if variant == "baseline":
        metrics = _aggregate_baseline_metrics(events)
    else:
        metrics = _aggregate_treatment_metrics(events)

    metrics["runtime_seconds"] = float(runtime)

    run_id = f"{workload_id}-{variant}-{int(start * 1_000_000)}"

    return {
        "variant": variant,
        "workload_id": workload_id,
        "run_id": run_id,
        "success": True,
        "metrics": metrics,
    }


def run_all_workloads() -> List[Dict[str, Any]]:
    runs: List[Dict[str, Any]] = []
    workloads = define_workloads()

    for w in workloads:
        # For fairness we run baseline then treatment; both simulation paths
        # are deterministic given the workload, variant, and phase names.
        baseline_run = _run_single_variant(w.workload_id, "baseline")
        treatment_run = _run_single_variant(w.workload_id, "treatment")
        runs.append(baseline_run)
        runs.append(treatment_run)

    return runs


__all__ = ["run_all_workloads"]
