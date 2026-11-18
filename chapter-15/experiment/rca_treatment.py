from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from .simulator import TickMetrics, WorkloadID


@dataclass
class DetectionResult:
    detected: bool
    detection_time_s: Optional[float]


class TreatmentRCA:
    """Automated RCA-style detector.

    More sensitive and targeted for each incident pattern. It uses the extra
    domain-specific signals provided by the simulator to emulate an
    LLM-aware RCA pipeline.
    """

    def detect(self, workload_id: WorkloadID, ticks: Iterable[TickMetrics]) -> DetectionResult:
        detection_time: Optional[float] = None
        detected = False

        for t in ticks:
            if detected:
                break

            if workload_id == WorkloadID.CS1:
                # Hallucination spike: rely heavily on retrieval health and
                # modest increase in error rate. Thresholds are more sensitive
                # than baseline.
                if t.retrieval_health <= 0.8 or t.error_rate >= 0.06:
                    detected = True
                    detection_time = t.logical_time_s

            elif workload_id == WorkloadID.CS2:
                # Routing regression: look at slow model fraction and latency.
                if t.routing_slow_fraction >= 0.6 or t.latency_ms >= 80.0:
                    detected = True
                    detection_time = t.logical_time_s

            elif workload_id == WorkloadID.CS3:
                # Tool cascade: look at tool health and error rate.
                if t.tool_health <= 0.7 or t.error_rate >= 0.15:
                    detected = True
                    detection_time = t.logical_time_s

        return DetectionResult(detected=detected, detection_time_s=detection_time)
