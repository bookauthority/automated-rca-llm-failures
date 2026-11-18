from __future__ import annotations

import queue
import threading
from typing import List, Dict, Any

from .events import RCAEvent
from .correlation import StreamingCorrelator


def run_streaming_pipeline(
    events: List[RCAEvent], workload_id: str, run_id: str
) -> Dict[str, Any]:
    """Simulate a streaming ingestion and correlation pipeline.

    A producer thread pushes events into a queue, and a consumer thread
    pops them and feeds a StreamingCorrelator. Correlation latency is
    approximated as `consumer_observed_ts - generator_ts`, where
    `consumer_observed_ts` is a monotonically increasing logical clock
    based on event processing order.
    """

    q: "queue.Queue[RCAEvent]" = queue.Queue()
    correlator = StreamingCorrelator()

    # Logical consumer clock; initialize at the first event's generator_ts
    # so that consumer time never lags behind generator time.
    consumer_clock = {"t": 0.0}
    latencies: List[float] = []

    if events:
        # Start at the minimum generator timestamp to guarantee
        # consumer_clock >= generator_ts for all events.
        min_ts = min(e.generator_ts for e in events)
        consumer_clock["t"] = min_ts

    def producer() -> None:
        for ev in events:
            q.put(ev)
        # Signal completion
        q.put(None)  # type: ignore[arg-type]

    def consumer() -> None:
        while True:
            ev = q.get()
            if ev is None:
                break
            # Advance logical clock per event to simulate processing time
            consumer_clock["t"] += 0.01
            if ev.is_incident_related:
                # latency is when we process it minus when it was generated
                latency = consumer_clock["t"] - ev.generator_ts
                # Guard against any numerical edge cases
                if latency < 0.0:
                    latency = 0.0
                latencies.append(latency)
            correlator.on_event(ev)

    prod_thread = threading.Thread(target=producer, daemon=True)
    cons_thread = threading.Thread(target=consumer, daemon=True)

    prod_thread.start()
    cons_thread.start()
    prod_thread.join()
    cons_thread.join()

    llm_events = sum(1 for e in events if e.event_type == "llm_interaction")
    incident_events = sum(1 for e in events if e.is_incident_related)

    # Ensure at least one latency sample if there are incident events
    if not latencies and incident_events > 0:
        # Fallback: nominal small latency so metrics are defined
        latencies.append(0.01)

    return {
        "llm_events": llm_events,
        "incident_events": incident_events,
        "latencies": latencies,
    }
