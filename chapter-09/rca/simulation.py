from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from .workloads import Workload, PhaseConfig


@dataclass
class InteractionEvent:
    """Simulation of the rich interaction_event described in the spec.

    In practice we only use a subset of the fields for metrics, but the
    structure mirrors the richer design.
    """

    request_id: str
    workload_id: str
    phase_name: str
    variant: str  # "baseline" or "treatment"
    timestamp_utc: float
    user_query: str
    response_text: str
    model_version: str
    prompt_template_version: str
    retrieval_state: str
    policy_config: str
    hallucination_label_llm: str
    hallucination_label_non_llm: str
    hallucination_consensus_label: str
    hallucination_confidence: float
    policy_decision: str
    policy_reason_codes: List[str]
    rca_processing_latency_ms: float


def _seed_for_run(variant: str, workload_id: str, phase_name: str) -> int:
    base = 37 if variant == "baseline" else 73
    return base + abs(hash((variant, workload_id, phase_name))) % (2**31 - 1)


def _hallucination_probability(config: Dict[str, str]) -> float:
    """Return a probability of hallucination based on prompt/retrieval/policy.

    This is a handcrafted deterministic function that captures the scenario
    logic:
    - Healthy retrieval + v1 prompts: low hallucination.
    - Prompt regression versions: higher hallucination.
    - Retrieval degraded: higher hallucination.
    - Prompt compensation on degraded retrieval: very high hallucination.
    """

    prompt_ver = config.get("prompt_template_version", "")
    retrieval_state = config.get("retrieval_state", "healthy")

    base = 0.05
    if "regressed" in prompt_ver:
        base += 0.25
    if "fixed" in prompt_ver:
        base -= 0.02
    if "rag-assistant-v1" in prompt_ver:
        base += 0.05
    if "rag-assistant-v2-heuristic-fix" in prompt_ver:
        base += 0.15

    if retrieval_state == "degraded":
        base += 0.22

    # Clip to [0, 0.95]
    return max(0.0, min(0.95, base))


def _policy_violation_probability(config: Dict[str, str]) -> float:
    policy_cfg = config.get("policy_config", "policy-v1")

    # Healthy baseline.
    if policy_cfg == "policy-v1":
        return 0.03
    # Stricter overblocking: more blocks, but not necessarily more *violations*.
    if policy_cfg == "policy-v2-stricter":
        return 0.04
    # Buggy underblocking: higher violations.
    if policy_cfg == "policy-v3-buggy":
        return 0.12

    return 0.03


def _policy_decision_from_probability(p: float, rnd: random.Random) -> Tuple[str, List[str]]:
    if rnd.random() < p:
        return "block", ["policy_violation"]
    # Occasionally modify content without full block.
    if rnd.random() < 0.05:
        return "modify", ["soft_filter"]
    return "allow", []


def _consensus_label(llm_label: str, non_llm_label: str, p: float) -> Tuple[str, float]:
    # Simple rule: if either says yes and p>0.2 -> severe; if partial -> mild.
    if llm_label == "yes" or non_llm_label == "yes":
        return "severe", max(0.5, min(0.95, p + 0.2))
    if llm_label == "partial" or non_llm_label == "partial":
        return "mild", max(0.3, min(0.9, p + 0.1))
    return "none", max(0.0, min(0.5, p))


def _judge_labels(p: float, rnd: random.Random) -> Tuple[str, str]:
    """Return (llm_label, non_llm_label) as yes/partial/no."""
    r1 = rnd.random()
    r2 = rnd.random()

    def sample_label(r: float) -> str:
        if r < p * 0.6:
            return "yes"
        if r < p * 0.9:
            return "partial"
        return "no"

    return sample_label(r1), sample_label(r2)


def simulate_workload(
    workload: Workload,
    variant: str,
) -> List[InteractionEvent]:
    """Simulate running the workload for a given variant.

    We compress real-time durations into integer numbers of events per phase.
    """

    all_events: List[InteractionEvent] = []
    base_time = time.time()

    for phase in workload.phases:
        seed = _seed_for_run(variant, workload.workload_id, phase.name)
        rnd = random.Random(seed)

        # Each minute maps to 3 synthetic requests (see workloads.minutes_to_requests).
        num_requests = max(1, phase.duration_minutes * 3)
        config = phase.configuration
        p_hall = _hallucination_probability(config)
        p_pol = _policy_violation_probability(config)

        for i in range(num_requests):
            req_id = f"{workload.workload_id}:{phase.name}:{variant}:{i}"
            t = base_time + len(all_events) * 0.001

            llm_label, non_llm_label = _judge_labels(p_hall, rnd)
            consensus, conf = _consensus_label(llm_label, non_llm_label, p_hall)

            policy_decision, reason_codes = _policy_decision_from_probability(
                p_pol, rnd
            )

            # Simulate extra processing time for treatment.
            rca_latency_ms = 0.2 if variant == "baseline" else 1.1

            event = InteractionEvent(
                request_id=req_id,
                workload_id=workload.workload_id,
                phase_name=phase.name,
                variant=variant,
                timestamp_utc=t,
                user_query="synthetic question",
                response_text="synthetic answer",
                model_version=config.get("model_version", "model-A-stable"),
                prompt_template_version=config.get(
                    "prompt_template_version", "unknown-prompt"
                ),
                retrieval_state=config.get("retrieval_state", "healthy"),
                policy_config=config.get("policy_config", "policy-v1"),
                hallucination_label_llm=llm_label,
                hallucination_label_non_llm=non_llm_label,
                hallucination_consensus_label=consensus,
                hallucination_confidence=conf,
                policy_decision=policy_decision,
                policy_reason_codes=reason_codes,
                rca_processing_latency_ms=rca_latency_ms,
            )
            all_events.append(event)

    return all_events


__all__ = ["InteractionEvent", "simulate_workload"]
