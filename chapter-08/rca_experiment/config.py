from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class WorkloadConfig:
    """Configuration for a synthetic workload.

    difficulty: logical difficulty score (higher = harder incident).
    base_noise: amount of randomness introduced into metric simulations.
    """

    workload_id: str
    difficulty: float
    base_noise: float


# Four workloads mirroring the chapter specification.
WORKLOADS: List[WorkloadConfig] = [
    WorkloadConfig(
        workload_id="workload-1-rag-hallucination-spike",
        difficulty=0.7,
        base_noise=0.1,
    ),
    WorkloadConfig(
        workload_id="workload-2-routing-misconfiguration-latency-regression",
        difficulty=0.5,
        base_noise=0.08,
    ),
    WorkloadConfig(
        workload_id="workload-3-prompt-template-regression",
        difficulty=0.6,
        base_noise=0.09,
    ),
    WorkloadConfig(
        workload_id="workload-4-tooling-api-flakiness",
        difficulty=0.8,
        base_noise=0.12,
    ),
]


# Ground-truth labels (simplified) for each workload.
GROUND_TRUTH_CATEGORIES: Dict[str, str] = {
    "workload-1-rag-hallucination-spike": "data",
    "workload-2-routing-misconfiguration-latency-regression": "routing",
    "workload-3-prompt-template-regression": "prompt",
    "workload-4-tooling-api-flakiness": "tooling",
}


# Deterministic seeds per workload for reproducibility.
SEEDS: Dict[str, int] = {
    "workload-1-rag-hallucination-spike": 101,
    "workload-2-routing-misconfiguration-latency-regression": 102,
    "workload-3-prompt-template-regression": 103,
    "workload-4-tooling-api-flakiness": 104,
}
