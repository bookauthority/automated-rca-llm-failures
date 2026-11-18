from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set

from .events import RCAEvent


@dataclass
class IncidentContext:
    context_id: str
    incident_id: str | None
    event_ids: Set[str] = field(default_factory=set)
    first_ts: float | None = None
    last_ts: float | None = None

    def add_event(self, event: RCAEvent) -> None:
        self.event_ids.add(event.event_id)
        if self.first_ts is None or event.generator_ts < self.first_ts:
            self.first_ts = event.generator_ts
        if self.last_ts is None or event.generator_ts > self.last_ts:
            self.last_ts = event.generator_ts


def batch_correlate(events: List[RCAEvent]) -> Dict[str, IncidentContext]:
    """Offline/batch correlation by incident_id.

    Every incident-related event is grouped under its incident_id; non-incident events
    are ignored for purposes of incident contexts.
    """

    contexts: Dict[str, IncidentContext] = {}
    for ev in events:
        if not ev.incident_id:
            continue
        ctx = contexts.get(ev.incident_id)
        if ctx is None:
            ctx = IncidentContext(context_id=ev.incident_id, incident_id=ev.incident_id)
            contexts[ev.incident_id] = ctx
        ctx.add_event(ev)
    return contexts


class StreamingCorrelator:
    """Simple streaming correlator with in-memory state.

    For sandbox purposes this just groups by incident_id like the batch
    correlator, but it accepts events incrementally and can be queried
    at any time.
    """

    def __init__(self) -> None:
        self.contexts: Dict[str, IncidentContext] = {}

    def on_event(self, event: RCAEvent) -> None:
        if not event.incident_id:
            return
        ctx = self.contexts.get(event.incident_id)
        if ctx is None:
            ctx = IncidentContext(context_id=event.incident_id, incident_id=event.incident_id)
            self.contexts[event.incident_id] = ctx
        ctx.add_event(event)

    def snapshot(self) -> Dict[str, IncidentContext]:
        # Shallow copy is enough since we only read in metrics
        return dict(self.contexts)
