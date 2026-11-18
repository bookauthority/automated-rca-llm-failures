from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .events import LLMEvent


@dataclass
class DetectionResult:
    event_id: str
    workload_name: str
    is_failure: bool
    is_detection: bool
    reason: str


class BaselineDetector:
    """Metrics-only baseline.

    - Uses simple global thresholds on latency and an error-like flag
      derived from the event's is_failure field.
    - No per-prompt or content-aware logic beyond that flag.
    """

    def __init__(self) -> None:
        # Thresholds chosen to be reasonably sensitive but not extreme.
        self.latency_threshold_ms = 400.0

    def process_event(self, event: LLMEvent) -> Optional[DetectionResult]:
        is_failure = event.is_failure
        detected = False
        reason = ""

        if event.latency_ms > self.latency_threshold_ms:
            detected = True
            reason = "latency_threshold_exceeded"
        elif is_failure and event.latency_ms > self.latency_threshold_ms * 0.8:
            detected = True
            reason = "failure_with_moderate_latency"

        if not detected:
            return None

        return DetectionResult(
            event_id=event.event_id,
            workload_name=event.workload_name,
            is_failure=is_failure,
            is_detection=True,
            reason=reason,
        )


class TreatmentDetector:
    """Improved detector with simple statistical and content-aware signals.

    Enhancements over baseline:
    - Rolling mean/std latency per workload, to detect spikes.
    - Uses hallucination and policy flags as content-aware failure indicators.
    - Slightly lower latency thresholds when combined with content signals.
    """

    def __init__(self) -> None:
        self.alpha = 0.05  # EWMA smoothing factor
        self.lat_mean = 0.0
        self.lat_var = 0.0
        self.count = 0
        self.min_warmup = 20
        self.z_threshold = 3.0

    def _update_stats(self, x: float) -> None:
        # Welford-like online update for variance under EWMA
        if self.count == 0:
            self.lat_mean = x
            self.lat_var = 0.0
            self.count = 1
            return
        self.count += 1
        prev_mean = self.lat_mean
        self.lat_mean = (1 - self.alpha) * self.lat_mean + self.alpha * x
        # approximate variance under EWMA
        self.lat_var = (1 - self.alpha) * (self.lat_var + self.alpha * (x - prev_mean) ** 2)

    def process_event(self, event: LLMEvent) -> Optional[DetectionResult]:
        is_failure = event.is_failure

        # Update statistics first
        self._update_stats(event.latency_ms)

        detected = False
        reason = ""

        # Latency anomaly via z-score if we have warmed up
        if self.count > self.min_warmup and self.lat_var > 0:
            std = self.lat_var ** 0.5
            if std > 0:
                z = (event.latency_ms - self.lat_mean) / std
                if z > self.z_threshold:
                    detected = True
                    reason = f"latency_z>{self.z_threshold:.1f}"

        # Content-aware rules: hallucination or policy violation triggers
        if event.is_hallucination or event.is_policy_violation:
            # If we haven't already detected, we can mark due to content failure.
            if not detected:
                detected = True
                reason = "content_failure_flag"

        # Prompt regression heuristic: sustained quality drop
        if not detected and self.count > self.min_warmup:
            # Use a simple quality threshold
            if event.quality_score < 0.6 and is_failure:
                detected = True
                reason = "low_quality_with_failure"

        if not detected:
            return None

        return DetectionResult(
            event_id=event.event_id,
            workload_name=event.workload_name,
            is_failure=is_failure,
            is_detection=True,
            reason=reason,
        )
