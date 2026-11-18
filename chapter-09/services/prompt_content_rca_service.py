from __future__ import annotations

from typing import Dict, List

from rca.content_attribution import attribute_content_failure
from rca.evaluators import heuristic_judge, llm_judge
from rca.prompt_rca import compute_hallucination_rate
from rca.policy_rca import compute_policy_violation_rate
from rca.simulation import InteractionEvent


class PromptContentRCAService:
    """Treatment-side RCA processor for content-centric failures.

    This class mimics a service that enriches interaction events with
    evaluation and attribution outputs. For this offline experiment, we do not
    persist per-event annotations; we only compute aggregated metrics.
    """

    def __init__(self) -> None:
        pass

    def process_events(self, events: List[InteractionEvent]) -> Dict[str, float]:
        """Process events and return aggregated metrics.

        Metrics include:
        - hallucination_rate
        - policy_violation_rate
        - mean_rca_processing_latency_ms
        """

        if not events:
            return {
                "hallucination_rate": 0.0,
                "policy_violation_rate": 0.0,
                "mean_rca_processing_latency_ms": 0.0,
            }

        # In a real system we'd attach judge outputs and attribution details
        # per event. Here we call them to mirror the cost and logic but only
        # aggregate the existing consensus label and policy decisions.
        for e in events:
            _ = llm_judge(e)
            _ = heuristic_judge(e)
            _ = attribute_content_failure(e)

        hallucination_rate = compute_hallucination_rate(events)
        policy_violation_rate = compute_policy_violation_rate(events)
        mean_latency = sum(e.rca_processing_latency_ms for e in events) / float(len(events))

        return {
            "hallucination_rate": hallucination_rate,
            "policy_violation_rate": policy_violation_rate,
            "mean_rca_processing_latency_ms": mean_latency,
        }


__all__ = ["PromptContentRCAService"]
