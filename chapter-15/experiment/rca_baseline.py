from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from .simulator import TickMetrics, WorkloadID


@dataclass
class DetectionResult:
    detected: bool
    detection_time_s: Optional[float]


class BaselineRCA:
    """Baseline/manual-style RCA detector.

    This mimics a less specialized, dashboard-driven process by:
    * Using higher thresholds for anomaly detection.
    * Ignoring specialized signals and relying mostly on latency + error.
    """

    def detect(self, workload_id: WorkloadID, ticks: Iterable[TickMetrics]) -> DetectionResult:
        detection_time: Optional[float] = None
        detected = False

        # Coarse thresholds: it takes fairly strong signals to trigger.
        # These are intentionally less sensitive than the treatment.
        latency_threshold = 0.0
        error_threshold = 0.0

        if workload_id == WorkloadID.CS1:
            latency_threshold = 60.0
            error_threshold = 0.08
        elif workload_id == WorkloadID.CS2:
            latency_threshold = 100.0
            error_threshold = 0.05
        elif workload_id == WorkloadID.CS3:
            latency_threshold = 100.0
            error_threshold = 0.2

        for t in ticks:
            if detected:
                break
            if t.latency_ms >= latency_threshold or t.error_rate >= error_threshold:
                detected = True
                detection_time = t.logical_time_s

        return DetectionResult(detected=detected, detection_time_s=detection_time)
