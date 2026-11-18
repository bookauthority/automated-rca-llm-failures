from __future__ import annotations

import random
from typing import Iterable, Dict, Any, List

from .events import RCAEvent, make_event_id, poisson_interval


def _make_llm_event(
    idx: int,
    base_ts: float,
    request_id: str,
    session_id: str,
    incident_id: str | None,
    incident_type: str | None,
    is_incident_related: bool,
) -> RCAEvent:
    return RCAEvent(
        event_id=make_event_id(idx),
        generator_ts=base_ts,
        event_type="llm_interaction",
        request_id=request_id,
        session_id=session_id,
        incident_id=incident_id,
        incident_type=incident_type,
        is_incident_related=is_incident_related,
        service_name="llm_gateway",
        payload={"tokens": 100, "latency_ms": 120},
    )


def _make_metric_event(idx: int, base_ts: float, service_name: str, incident_id: str | None) -> RCAEvent:
    return RCAEvent(
        event_id=make_event_id(idx),
        generator_ts=base_ts,
        event_type="infra_metric",
        request_id=None,
        session_id=None,
        incident_id=incident_id,
        incident_type=None,
        is_incident_related=incident_id is not None,
        service_name=service_name,
        payload={"latency_ms_p95": 200.0, "error_rate": 0.02},
    )


def _make_trace_event(idx: int, base_ts: float, request_id: str, incident_id: str | None) -> RCAEvent:
    return RCAEvent(
        event_id=make_event_id(idx),
        generator_ts=base_ts,
        event_type="trace_span",
        request_id=request_id,
        session_id=None,
        incident_id=incident_id,
        incident_type=None,
        is_incident_related=incident_id is not None,
        service_name="llm_orchestrator",
        payload={"span_name": "orchestrate_call", "duration_ms": 80},
    )


def generate_workload_events(config: Dict[str, Any]) -> Iterable[RCAEvent]:
    """Yield RCAEvents for a given workload config.

    This generator is deterministic for a given seed and config.
    """

    seed = config.get("seed", 0)
    rng = random.Random(seed)
    ts = 0.0
    idx = 0

    workload_type = config["type"]

    if workload_type == "steady":
        total_requests = int(config.get("total_requests", 200))
        incident_fraction = float(config.get("incident_fraction", 0.1))

        for i in range(total_requests):
            is_incident = rng.random() < incident_fraction
            incident_id = f"inc_{i // 10}" if is_incident else None
            incident_type = "hallucination_spike" if is_incident else None

            request_id = f"req_{i:05d}"
            session_id = f"sess_{i // 5:04d}"

            ts += poisson_interval(rate_per_second=5.0, rng=rng)

            # LLM event
            idx += 1
            yield _make_llm_event(idx, ts, request_id, session_id, incident_id, incident_type, is_incident)

            # Metric and trace around same time
            idx += 1
            yield _make_metric_event(idx, ts + 0.05, "llm_backend", incident_id if is_incident else None)
            idx += 1
            yield _make_trace_event(idx, ts + 0.02, request_id, incident_id if is_incident else None)

    elif workload_type == "burst":
        phases: List[Dict[str, Any]] = config["phases"]
        for phase_idx, phase in enumerate(phases):
            requests = int(phase["requests"])
            incident_fraction = float(phase["incident_fraction"])
            base_rate = 3.0 + 5.0 * phase_idx

            for j in range(requests):
                is_incident = rng.random() < incident_fraction
                incident_id = f"inc_b_{phase_idx}_{j // 5}" if is_incident else None
                incident_type = "latency_regression" if is_incident else None

                request_id = f"w2_req_{phase_idx}_{j:05d}"
                session_id = f"w2_sess_{phase_idx}_{j // 4:04d}"

                ts += poisson_interval(rate_per_second=base_rate, rng=rng)

                idx += 1
                yield _make_llm_event(idx, ts, request_id, session_id, incident_id, incident_type, is_incident)

                idx += 1
                yield _make_metric_event(idx, ts + 0.03, "vector_store", incident_id if is_incident else None)

                idx += 1
                yield _make_trace_event(idx, ts + 0.01, request_id, incident_id if is_incident else None)

    elif workload_type == "replay":
        # Synthetic deterministic replay; pretend these came from files with fixed timestamps.
        incidents = int(config.get("incidents", 5))
        requests_per_incident = int(config.get("requests_per_incident", 10))

        for inc in range(incidents):
            incident_id = f"replay_inc_{inc}"
            incident_type = "hallucination_spike" if inc % 2 == 0 else "routing_misconfig"

            for k in range(requests_per_incident):
                # Inter-event times are fixed to preserve ordering deterministically
                ts += 0.2
                request_id = f"w3_req_{inc}_{k:04d}"
                session_id = f"w3_sess_{inc}_{k // 3:03d}"

                idx += 1
                yield _make_llm_event(idx, ts, request_id, session_id, incident_id, incident_type, True)

                idx += 1
                yield _make_metric_event(idx, ts + 0.01, "retriever", incident_id)

                idx += 1
                yield _make_trace_event(idx, ts + 0.02, request_id, incident_id)

    else:
        raise ValueError(f"Unknown workload type: {workload_type}")
