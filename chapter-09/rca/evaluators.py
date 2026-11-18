from __future__ import annotations

from typing import Dict, List

from .simulation import InteractionEvent


def llm_judge(event: InteractionEvent) -> Dict[str, float | str]:
    """Simulated LLM judge.

    Uses existing fields from the event, but in a real system this would call
    out to an external LLM with a judging prompt.
    """

    sev_map = {"none": 0.0, "mild": 0.5, "severe": 1.0}
    severity_score_llm = sev_map.get(event.hallucination_consensus_label, 0.0)

    return {
        "hallucination_label_llm": event.hallucination_label_llm,
        "support_alignment_score": 1.0 - severity_score_llm,
        "severity_score_llm": severity_score_llm,
    }


def heuristic_judge(event: InteractionEvent) -> Dict[str, float | str | List[str]]:
    """Non-LLM heuristic judge using simple rules.

    - Treat degraded retrieval as more prone to hallucination.
    - Map consensus label to a simple heuristic score.
    """

    base = 0.1
    if event.retrieval_state == "degraded":
        base += 0.3
    if event.hallucination_consensus_label == "severe":
        base += 0.3
    elif event.hallucination_consensus_label == "mild":
        base += 0.15

    base = max(0.0, min(1.0, base))

    if base > 0.6:
        label = "yes"
    elif base > 0.3:
        label = "partial"
    else:
        label = "no"

    return {
        "hallucination_label_non_llm": label,
        "heuristic_scores": base,
        "rule_violations": [],
    }


__all__ = ["llm_judge", "heuristic_judge"]
