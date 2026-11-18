from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Iterable, List, Optional

from .config import WorkloadConfig


@dataclass
class LLMEvent:
    """Simplified representation of an LLM interaction event.

    This mirrors only a subset of the chapter's evidence schema fields,
    sufficient for our synthetic detection experiment.
    """

    event_id: str
    timestamp: float  # relative time index (not wall-clock)
    workload_name: str
    prompt_template_id: str
    prompt_version: str
    model_id: str
    route_id: str
    rag_index_id: Optional[str]
    latency_ms: float
    tokens_input: int
    tokens_output: int
    is_failure: bool
    is_hallucination: bool
    is_policy_violation: bool
    quality_score: float  # 0-1


def _rng_for_workload(workload_id: str, base_seed: int) -> random.Random:
    return random.Random(base_seed + abs(hash(workload_id)) % (10**6))


def generate_workload_events(
    workload_id: str, cfg: WorkloadConfig, base_seed: int
) -> List[LLMEvent]:
    """Generate a deterministic sequence of synthetic events for a workload.

    The generator encodes a simple notion of failure periods and failure types.
    """

    rng = _rng_for_workload(workload_id, base_seed)
    events: List[LLMEvent] = []

    # Prompt/model routing is simplified but kept per-workload distinct
    base_prompt = {
        "baseline_normal_workload": "qa_rag_v1",
        "latency_spike_failure": "qa_rag_v1",
        "token_cost_anomaly": "long_form_v1",
        "hallucination_spike_failure": "qa_rag_v1",
        "policy_violation_burst": "policy_sensitive_v1",
        "prompt_regression_version_swap": "qa_rag_v1",
        "routing_misconfiguration": "tool_agent_v1",
    }.get(workload_id, "generic_prompt")

    base_version = "v1"
    model_id = "llm_vA"
    route_id = "default_route"
    rag_index_id = "knowledge_base_v1" if "qa_rag" in base_prompt else None

    # Derived parameters for content failures
    base_hallucination_rate = 0.05
    base_policy_violation_rate = 0.01
    base_quality_score = 0.8

    for i in range(cfg.num_events):
        frac = i / max(cfg.num_events - 1, 1)
        in_failure = cfg.failure_start_fraction <= frac <= cfg.failure_end_fraction

        # Latency
        latency = rng.normalvariate(cfg.base_latency_ms, cfg.base_latency_ms * 0.05)
        if in_failure:
            latency *= cfg.latency_multiplier

        # Tokens as a simple function of workload type
        base_tokens_in = 80 if "qa_rag" in base_prompt else 200
        base_tokens_out = 100 if "qa_rag" in base_prompt else 250
        if in_failure:
            base_tokens_in = int(base_tokens_in * cfg.token_multiplier)
            base_tokens_out = int(base_tokens_out * cfg.token_multiplier)
        tokens_input = max(5, int(rng.normalvariate(base_tokens_in, base_tokens_in * 0.1)))
        tokens_output = max(5, int(rng.normalvariate(base_tokens_out, base_tokens_out * 0.1)))

        # Failure flags
        failure_prob = cfg.base_failure_rate
        if in_failure:
            failure_prob = min(1.0, failure_prob + cfg.extra_failure_rate)
        is_failure = rng.random() < failure_prob

        # Content-specific labels
        hallucination_rate = base_hallucination_rate
        policy_rate = base_policy_violation_rate
        quality = base_quality_score

        if in_failure:
            hallucination_rate = min(1.0, hallucination_rate + cfg.hallucination_spike)
            policy_rate = min(1.0, policy_rate + cfg.policy_violation_spike)
            quality = max(0.0, quality - cfg.quality_drop)

        is_hallucination = rng.random() < hallucination_rate
        is_policy_violation = rng.random() < policy_rate

        # Quality noise
        quality_noise = rng.normalvariate(0.0, 0.05)
        quality_score = min(1.0, max(0.0, quality + quality_noise))

        # Simple prompt version swap to reflect prompt regression narrative
        prompt_version = base_version
        if workload_id == "prompt_regression_version_swap" and in_failure:
            prompt_version = "v2_regressed"

        events.append(
            LLMEvent(
                event_id=f"{workload_id}-{i}",
                timestamp=float(i),
                workload_name=workload_id,
                prompt_template_id=base_prompt,
                prompt_version=prompt_version,
                model_id=model_id,
                route_id=route_id,
                rag_index_id=rag_index_id,
                latency_ms=float(max(1.0, latency)),
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                is_failure=is_failure or is_hallucination or is_policy_violation,
                is_hallucination=is_hallucination,
                is_policy_violation=is_policy_violation,
                quality_score=quality_score,
            )
        )

    return events
