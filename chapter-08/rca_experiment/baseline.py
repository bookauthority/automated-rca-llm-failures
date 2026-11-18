from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List

from .config import GROUND_TRUTH_CATEGORIES
from .features import IncidentFeatures


@dataclass
class BaselineHypothesis:
    description: str
    category: str
    confidence: float


@dataclass
class BaselineResult:
    hypotheses: List[BaselineHypothesis]
    time_to_first_plausible_root_cause: float


def run_baseline_rca(features: IncidentFeatures) -> BaselineResult:
    """Simulate manual RCA using simple heuristics.

    This function generates a primary hypothesis that sometimes matches the
    ground truth but with lower probability/effectiveness than the AI-assisted
    pipeline. The time to first plausible root cause is derived from
    difficulty and the quality of the guessed category.
    """

    workload_id = features.workload_id
    true_cat = GROUND_TRUTH_CATEGORIES.get(workload_id, "unknown")

    # Baseline picks among a few common categories based on rough signals.
    if features.change_flag >= 0.5 and features.anomaly_magnitude > 0.8:
        guessed_cat = true_cat  # more likely to be right when signals are strong
        base_conf = 0.65
    else:
        # Fallback generic guess by latency vs error inference.
        if features.window_latency_p95 > 350.0:
            guessed_cat = "infra"
        else:
            guessed_cat = "unknown"
        base_conf = 0.4

    # Time to first plausible root cause: slower when wrong category.
    difficulty = 0.5 + 0.5 * (1.0 - min(1.0, features.anomaly_magnitude))
    if guessed_cat == true_cat:
        time_seconds = 25.0 * difficulty
    else:
        time_seconds = 40.0 * difficulty

    time_seconds = float(max(5.0, min(120.0, time_seconds)))

    primary = BaselineHypothesis(
        description=f"Manual analysis suggests issue category '{guessed_cat}'.",
        category=guessed_cat,
        confidence=float(min(0.95, base_conf + 0.05 * features.change_flag)),
    )

    # Secondary catch-all hypothesis.
    secondary = BaselineHypothesis(
        description="There may be contributing factors from infrastructure or external services.",
        category="infra",
        confidence=0.3,
    )

    return BaselineResult(
        hypotheses=[primary, secondary],
        time_to_first_plausible_root_cause=time_seconds,
    )
