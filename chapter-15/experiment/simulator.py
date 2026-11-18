from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple


class WorkloadID(str, Enum):
    CS1 = "workload-cs1-hallucination-spike-after-data-refresh"
    CS2 = "workload-cs2-latency-and-cost-regressions-routing-misconfig"
    CS3 = "workload-cs3-cascading-failures-broken-tool-integration"


@dataclass
class TickMetrics:
    """Synthetic metrics produced for one discrete time step.

    All values are numeric and deterministic given the simulator parameters.
    """

    logical_time_s: float
    latency_ms: float
    error_rate: float
    retrieval_health: float
    routing_slow_fraction: float
    tool_health: float


@dataclass
class WorkloadConfig:
    """Configuration for a workload simulation.

    We parameterize the simulation by phase durations and incident severity.
    The config is kept simple to ensure deterministic behavior.
    """

    workload_id: WorkloadID
    total_ticks: int
    incident_start_tick: int
    incident_end_tick: int
    baseline_latency_ms: float
    incident_latency_ms: float
    baseline_error_rate: float
    incident_error_rate: float

    # Domain-specific health signals (0.0 bad, 1.0 good)
    baseline_retrieval_health: float
    incident_retrieval_health: float
    baseline_routing_slow_fraction: float
    incident_routing_slow_fraction: float
    baseline_tool_health: float
    incident_tool_health: float


class WorkloadSimulator:
    """Deterministic simulator for synthetic LLM incident workloads.

    Each call to :meth:`run` produces a fixed sequence of TickMetrics that
    encode the before/after-incident behavior.
    """

    def __init__(self, config: WorkloadConfig) -> None:
        self.config = config

    def run(self) -> List[TickMetrics]:
        cfg = self.config
        metrics: List[TickMetrics] = []

        for tick in range(cfg.total_ticks):
            in_incident = cfg.incident_start_tick <= tick < cfg.incident_end_tick
            phase_progress = self._phase_progress(tick)

            if in_incident:
                latency_ms = self._interp(
                    cfg.baseline_latency_ms,
                    cfg.incident_latency_ms,
                    phase_progress,
                )
                error_rate = self._interp(
                    cfg.baseline_error_rate,
                    cfg.incident_error_rate,
                    phase_progress,
                )
                retrieval_health = self._interp(
                    cfg.baseline_retrieval_health,
                    cfg.incident_retrieval_health,
                    phase_progress,
                )
                routing_slow_fraction = self._interp(
                    cfg.baseline_routing_slow_fraction,
                    cfg.incident_routing_slow_fraction,
                    phase_progress,
                )
                tool_health = self._interp(
                    cfg.baseline_tool_health,
                    cfg.incident_tool_health,
                    phase_progress,
                )
            else:
                # Outside incident window, stay at baseline but add tiny
                # deterministic wiggle to make averages non-trivial.
                wiggle = 1.0 + 0.01 * math.sin(tick / 10.0)
                latency_ms = cfg.baseline_latency_ms * wiggle
                error_rate = cfg.baseline_error_rate * wiggle
                retrieval_health = cfg.baseline_retrieval_health
                routing_slow_fraction = cfg.baseline_routing_slow_fraction
                tool_health = cfg.baseline_tool_health

            logical_time_s = float(tick)
            metrics.append(
                TickMetrics(
                    logical_time_s=logical_time_s,
                    latency_ms=latency_ms,
                    error_rate=error_rate,
                    retrieval_health=retrieval_health,
                    routing_slow_fraction=routing_slow_fraction,
                    tool_health=tool_health,
                )
            )

        return metrics

    @staticmethod
    def _interp(a: float, b: float, t: float) -> float:
        # Simple linear interpolation
        return a + (b - a) * t

    def _phase_progress(self, tick: int) -> float:
        """Return a smooth [0,1] progress value during the incident.

        This is used to ensure incident effects ramp in rather than appear as
        a step function, while remaining deterministic.
        """

        cfg = self.config
        if tick < cfg.incident_start_tick or tick >= cfg.incident_end_tick:
            return 0.0
        duration = max(1, cfg.incident_end_tick - cfg.incident_start_tick)
        rel = (tick - cfg.incident_start_tick) / duration
        # Ease-in curve to avoid harsh edges.
        return float(rel * rel)


def build_default_workload_configs() -> Tuple[WorkloadConfig, WorkloadConfig, WorkloadConfig]:
    """Build default configs roughly inspired by the chapter's three case studies.

    Values are chosen to be:
    * Different per workload to capture qualitative differences.
    * Deterministic and simple enough for straightforward reasoning.
    """

    # CS1: Hallucination spike after data refresh – more errors, mild latency hit.
    cs1 = WorkloadConfig(
        workload_id=WorkloadID.CS1,
        total_ticks=90,
        incident_start_tick=20,
        incident_end_tick=80,
        baseline_latency_ms=50.0,
        incident_latency_ms=65.0,
        baseline_error_rate=0.02,
        incident_error_rate=0.12,
        baseline_retrieval_health=0.95,
        incident_retrieval_health=0.5,
        baseline_routing_slow_fraction=0.2,
        incident_routing_slow_fraction=0.2,
        baseline_tool_health=1.0,
        incident_tool_health=1.0,
    )

    # CS2: Routing misconfig – latency increase with similar error rate.
    cs2 = WorkloadConfig(
        workload_id=WorkloadID.CS2,
        total_ticks=60,
        incident_start_tick=15,
        incident_end_tick=55,
        baseline_latency_ms=40.0,
        incident_latency_ms=120.0,
        baseline_error_rate=0.03,
        incident_error_rate=0.035,
        baseline_retrieval_health=1.0,
        incident_retrieval_health=1.0,
        baseline_routing_slow_fraction=0.2,
        incident_routing_slow_fraction=0.8,
        baseline_tool_health=1.0,
        incident_tool_health=1.0,
    )

    # CS3: Tool cascade failure – sharp error and latency spikes.
    cs3 = WorkloadConfig(
        workload_id=WorkloadID.CS3,
        total_ticks=75,
        incident_start_tick=20,
        incident_end_tick=60,
        baseline_latency_ms=60.0,
        incident_latency_ms=180.0,
        baseline_error_rate=0.05,
        incident_error_rate=0.4,
        baseline_retrieval_health=1.0,
        incident_retrieval_health=1.0,
        baseline_routing_slow_fraction=0.3,
        incident_routing_slow_fraction=0.3,
        baseline_tool_health=1.0,
        incident_tool_health=0.1,
    )

    return cs1, cs2, cs3
