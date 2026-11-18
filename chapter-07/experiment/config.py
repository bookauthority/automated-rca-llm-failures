from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


# Global RNG seed for reproducibility across the whole experiment
RNG_SEED = 7_000_007


@dataclass(frozen=True)
class WorkloadConfig:
    """Configuration describing a synthetic workload.

    The fields are intentionally simple; more complex behaviour
    lives in the event generator.
    """

    name: str
    num_events: int
    base_latency_ms: float
    base_failure_rate: float
    # Failure regime controls
    failure_type: Optional[str] = None
    failure_start_fraction: float = 0.0
    failure_end_fraction: float = 0.0
    # Multipliers or deltas for failure periods
    latency_multiplier: float = 1.0
    extra_failure_rate: float = 0.0
    hallucination_spike: float = 0.0
    policy_violation_spike: float = 0.0
    quality_drop: float = 0.0
    token_multiplier: float = 1.0


# Workload configurations matching the narrative in a simplified manner.

WORKLOAD_CONFIGS: Dict[str, WorkloadConfig] = {
    # Baseline workload: used for calibration-like behaviour, no induced failures.
    "baseline_normal_workload": WorkloadConfig(
        name="baseline_normal_workload",
        num_events=400,
        base_latency_ms=200.0,
        base_failure_rate=0.02,
    ),
    # Latency spike: increased latency in a portion of the stream.
    "latency_spike_failure": WorkloadConfig(
        name="latency_spike_failure",
        num_events=400,
        base_latency_ms=200.0,
        base_failure_rate=0.02,
        failure_type="latency_injection",
        failure_start_fraction=0.3,
        failure_end_fraction=0.7,
        latency_multiplier=3.0,
    ),
    # Token/cost anomaly: we approximate this by increasing failure flags moderately
    # and treat some of these as cost-related issues.
    "token_cost_anomaly": WorkloadConfig(
        name="token_cost_anomaly",
        num_events=400,
        base_latency_ms=220.0,
        base_failure_rate=0.02,
        failure_type="token_cost_anomaly",
        failure_start_fraction=0.3,
        failure_end_fraction=0.8,
        token_multiplier=2.5,
        extra_failure_rate=0.03,
    ),
    # Hallucination spike: content failure with normal latency.
    "hallucination_spike_failure": WorkloadConfig(
        name="hallucination_spike_failure",
        num_events=400,
        base_latency_ms=210.0,
        base_failure_rate=0.02,
        failure_type="hallucination_spike",
        failure_start_fraction=0.3,
        failure_end_fraction=0.8,
        hallucination_spike=0.35,  # baseline 0.05; spike approx 0.4 total
    ),
    # Policy violation burst: content policy failures.
    "policy_violation_burst": WorkloadConfig(
        name="policy_violation_burst",
        num_events=300,
        base_latency_ms=210.0,
        base_failure_rate=0.01,
        failure_type="policy_violation_burst",
        failure_start_fraction=0.2,
        failure_end_fraction=0.6,
        policy_violation_spike=0.29,
    ),
    # Prompt regression: quality drop and slightly increased hallucinations.
    "prompt_regression_version_swap": WorkloadConfig(
        name="prompt_regression_version_swap",
        num_events=450,
        base_latency_ms=210.0,
        base_failure_rate=0.02,
        failure_type="prompt_regression",
        failure_start_fraction=0.33,
        failure_end_fraction=0.88,
        quality_drop=0.2,
        hallucination_spike=0.1,
    ),
    # Routing misconfiguration: mild latency and quality changes.
    "routing_misconfiguration": WorkloadConfig(
        name="routing_misconfiguration",
        num_events=350,
        base_latency_ms=205.0,
        base_failure_rate=0.02,
        failure_type="routing_misconfig",
        failure_start_fraction=0.3,
        failure_end_fraction=0.85,
        latency_multiplier=1.5,
        quality_drop=0.1,
    ),
}
