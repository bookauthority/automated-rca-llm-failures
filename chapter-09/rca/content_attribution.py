from __future__ import annotations

from typing import Dict

from .simulation import InteractionEvent


def attribute_content_failure(event: InteractionEvent) -> Dict[str, float | str | Dict[str, float]]:
    """Layered attribution decision tree.

    Uses only runtime signals (no ground-truth labels) to estimate how likely
    each layer is to be responsible: prompt, retrieval, model, policy.
    """

    scores = {"prompt": 0.0, "retrieval": 0.0, "model": 0.0, "policy": 0.0}

    # Retrieval contribution.
    if event.retrieval_state == "degraded":
        scores["retrieval"] += 0.6

    # Prompt contribution.
    pv = event.prompt_template_version
    if "regressed" in pv or "heuristic-fix" in pv:
        scores["prompt"] += 0.4

    # Policy contribution.
    if event.policy_decision in {"block", "modify"} and event.policy_reason_codes:
        scores["policy"] += 0.7

    # Model baseline contribution: small constant.
    scores["model"] += 0.1

    total = sum(scores.values())
    if total <= 0:
        norm_scores = {k: 0.0 for k in scores}
    else:
        norm_scores = {k: v / total for k, v in scores.items()}

    primary_cause = max(norm_scores.items(), key=lambda kv: kv[1])[0]

    return {
        "primary_cause": primary_cause,
        "cause_scores": norm_scores,
    }


__all__ = ["attribute_content_failure"]
