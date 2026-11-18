from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, Iterable


@dataclass
class RCAEvent:
    event_id: str
    generator_ts: float
    event_type: str  # 'llm_interaction' | 'infra_metric' | 'trace_span'
    request_id: Optional[str]
    session_id: Optional[str]
    incident_id: Optional[str]
    incident_type: Optional[str]
    is_incident_related: bool
    service_name: Optional[str]
    payload: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def make_event_id(counter: int) -> str:
    return f"evt_{counter:06d}"


def poisson_interval(rate_per_second: float, rng: random.Random) -> float:
    """Return an exponential inter-arrival time matching a Poisson(rate)."""

    if rate_per_second <= 0:
        return 0.0
    u = rng.random()
    return -math.log(1.0 - u) / rate_per_second


def now_monotonic() -> float:
    # Abstracted for tests; could be monkeypatched if needed.
    return time.monotonic()
