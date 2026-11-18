import json
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any


@dataclass
class Span:
    name: str
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    start_time_ns: int
    end_time_ns: Optional[int] = None

    def end(self) -> None:
        if self.end_time_ns is None:
            self.end_time_ns = time.time_ns()


class Tracer:
    """Very small local tracer that just issues IDs and durations."""

    def __init__(self, service_name: str) -> None:
        self.service_name = service_name

    def start_span(self, name: str, parent: Optional[Span] = None) -> Span:
        trace_id = parent.trace_id if parent else uuid.uuid4().hex
        span_id = uuid.uuid4().hex[:16]
        parent_span_id = parent.span_id if parent else None
        return Span(
            name=name,
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            start_time_ns=time.time_ns(),
        )


class EventWriter:
    """Append JSON events to a file, simulating an OTEL log exporter."""

    def __init__(self, path: str) -> None:
        self.path = Path(path)
        if not self.path.parent.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def write_event(self, event: Dict[str, Any]) -> None:
        line = json.dumps(event, sort_keys=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
