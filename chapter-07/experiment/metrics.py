from __future__ import annotations

from typing import Iterable, List, Tuple

from .events import LLMEvent
from .detectors import DetectionResult


def compute_avg_latency(events: Iterable[LLMEvent]) -> float:
    total = 0.0
    count = 0
    for e in events:
        total += e.latency_ms
        count += 1
    return total / count if count else 0.0


def compute_failure_event_rate(events: Iterable[LLMEvent]) -> float:
    total = 0
    failures = 0
    for e in events:
        total += 1
        if e.is_failure:
            failures += 1
    return failures / total if total else 0.0


def compute_detection_and_fp_rates(
    events: List[LLMEvent], detections: List[DetectionResult]
) -> Tuple[float, float]:
    """Compute detection rate over failure events and false positive rate.

    detection_rate = (# failure events that were detected) / (# failure events)
    false_positive_rate = (# detections on non-failure events) / (# non-failure events)
    """

    # Map event_id -> event for quick lookup
    event_by_id = {e.event_id: e for e in events}

    detected_failures = 0
    detected_non_failures = 0
    total_failures = 0
    total_non_failures = 0

    for e in events:
        if e.is_failure:
            total_failures += 1
        else:
            total_non_failures += 1

    # Track which event_ids were detected
    detected_ids = set(d.event_id for d in detections if d.is_detection)

    for eid in detected_ids:
        ev = event_by_id.get(eid)
        if ev is None:
            continue
        if ev.is_failure:
            detected_failures += 1
        else:
            detected_non_failures += 1

    detection_rate = detected_failures / total_failures if total_failures else 0.0
    false_positive_rate = (
        detected_non_failures / total_non_failures if total_non_failures else 0.0
    )

    return detection_rate, false_positive_rate
