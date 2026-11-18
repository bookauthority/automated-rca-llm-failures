from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .config import GROUND_TRUTH_CATEGORIES
from .features import IncidentFeatures
from .llm_simulator import GeneratedHypothesis


@dataclass
class RankedHypothesis:
    id: str
    description: str
    category: str
    llm_confidence: float
    ranker_score: float
    final_rank: int


def _score_hypothesis(
    workload_id: str, features: IncidentFeatures, hyp: GeneratedHypothesis
) -> float:
    """Deterministic scoring function approximating a learned ranker.

    - Reward alignment between hypothesis category and ground-truth category.
    - Reward higher anomaly magnitudes and presence of change_flag.
    - Penalize categories that are clearly inconsistent with scenario type.
    """

    true_cat = GROUND_TRUTH_CATEGORIES.get(workload_id, "unknown")

    score = 0.0
    if hyp.category == true_cat:
        score += 0.6
    elif hyp.category == "unknown":
        score += 0.1
    else:
        score -= 0.1

    score += 0.2 * min(1.0, features.anomaly_magnitude)
    score += 0.1 * features.change_flag

    # Clamp to [0, 1].
    return float(max(0.0, min(1.0, score)))


def rank_hypotheses(
    features: IncidentFeatures,
    generated: List[GeneratedHypothesis],
) -> List[RankedHypothesis]:
    """Rank and prune LLM-generated hypotheses.

    Returns hypotheses sorted by our scoring function in descending order.
    """

    scored: List[RankedHypothesis] = []
    for hyp in generated:
        s = _score_hypothesis(features.workload_id, features, hyp)
        scored.append(
            RankedHypothesis(
                id=hyp.id,
                description=hyp.description,
                category=hyp.category,
                llm_confidence=hyp.confidence,
                ranker_score=s,
                final_rank=0,  # filled below
            )
        )

    scored.sort(key=lambda h: h.ranker_score, reverse=True)
    for idx, h in enumerate(scored, start=1):
        h.final_rank = idx

    # Optionally prune low-score hypotheses; keep at least 1.
    if len(scored) > 1:
        threshold = 0.15
        scored = [h for h in scored if h.ranker_score >= threshold] or [scored[0]]

    return scored
