from __future__ import annotations

import os
from typing import List, Dict, Any

from .events import RCAEvent
from .correlation import batch_correlate
from .util import write_jsonl, read_jsonl


def run_baseline_pipeline(
    events: List[RCAEvent], workload_id: str, run_id: str
) -> Dict[str, Any]:
    """Simulate a batch pipeline.

    Steps:
    1. Generator writes all events to a JSONL file (simulated object store).
    2. Batch job reads the file, reconstructs events, and correlates them.
    3. Compute simple metrics including correlation latency, defined as
       `correlation_complete_ts - generator_ts` for incident-related events.

    We use an artificial "correlation_complete_ts" that is the same for all
    events to mimic a batch window: all correlation is done after the batch.
    """

    # 1. Write events as produced by generator
    tmp_dir = os.path.join("/tmp", "exp06_baseline", workload_id, run_id)
    os.makedirs(tmp_dir, exist_ok=True)
    events_path = os.path.join(tmp_dir, "events.jsonl")
    write_jsonl(events_path, events)

    # 2. Read them back as if in a batch job
    loaded_events: List[RCAEvent] = []
    for row in read_jsonl(events_path):
        loaded_events.append(
            RCAEvent(
                event_id=row["event_id"],
                generator_ts=float(row["generator_ts"]),
                event_type=row["event_type"],
                request_id=row.get("request_id"),
                session_id=row.get("session_id"),
                incident_id=row.get("incident_id"),
                incident_type=row.get("incident_type"),
                is_incident_related=bool(row.get("is_incident_related", False)),
                service_name=row.get("service_name"),
                payload=row.get("payload", {}),
            )
        )

    # Simulate a single batch completion time: max generator_ts + fixed delta
    if loaded_events:
        batch_complete_ts = max(ev.generator_ts for ev in loaded_events) + 0.5
    else:
        batch_complete_ts = 0.5

    contexts = batch_correlate(loaded_events)

    # Metrics
    llm_events = sum(1 for e in loaded_events if e.event_type == "llm_interaction")
    incident_events = sum(1 for e in loaded_events if e.is_incident_related)

    latencies: List[float] = []
    for ctx in contexts.values():
        for ev_id in ctx.event_ids:
            ev = next(e for e in loaded_events if e.event_id == ev_id)
            latencies.append(batch_complete_ts - ev.generator_ts)

    return {
        "llm_events": llm_events,
        "incident_events": incident_events,
        "latencies": latencies,
    }
