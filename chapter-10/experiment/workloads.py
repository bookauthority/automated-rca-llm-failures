from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple


@dataclass
class Request:
    """A synthetic request description.

    For this offline simulation, a request only carries enough metadata to
    decide which model is used and to keep counts.
    """

    id: int
    intent: str
    phase: str


@dataclass
class WorkloadConfig:
    workload_id: str  # "eval" or "prod"
    num_requests: int
    intents: Dict[str, float]  # intent -> probability


EVAL_INTENTS = {
    "factual_qa": 0.25,
    "summarization": 0.25,
    "classification": 0.25,
    "misc": 0.25,
}

PROD_INTENTS = {
    "short_qa": 0.4,
    "long_form": 0.3,
    "classification": 0.2,
    "misc": 0.1,
}


def get_workload_config(workload_id: str) -> WorkloadConfig:
    if workload_id == "eval":
        return WorkloadConfig(
            workload_id="eval",
            num_requests=400,  # bounded for sandbox
            intents=EVAL_INTENTS,
        )
    elif workload_id == "prod":
        return WorkloadConfig(
            workload_id="prod",
            num_requests=800,  # a bit larger, still bounded
            intents=PROD_INTENTS,
        )
    else:
        raise ValueError(f"Unknown workload_id: {workload_id}")


def _sample_intent(rng: random.Random, intents: Dict[str, float]) -> str:
    r = rng.random()
    cumulative = 0.0
    for intent, p in intents.items():
        cumulative += p
        if r <= cumulative:
            return intent
    # Fallback due to floating issues
    return next(iter(intents.keys()))


def generate_requests(
    workload: WorkloadConfig,
    phase: str,
    rng: random.Random,
) -> List[Request]:
    requests: List[Request] = []
    for i in range(workload.num_requests):
        intent = _sample_intent(rng, workload.intents)
        requests.append(Request(id=i, intent=intent, phase=phase))
    return requests
