from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .config import GROUND_TRUTH_CATEGORIES
from .features import IncidentFeatures
from .clustering import ClusterResult


@dataclass
class GeneratedHypothesis:
    id: str
    description: str
    category: str
    confidence: float
    evidence: str
    proposed_tests: str


@dataclass
class LlmOutput:
    hypotheses: List[GeneratedHypothesis]
    global_summary: str


def generate_hypotheses(
    incident_id: str,
    features: IncidentFeatures,
    cluster: ClusterResult,
) -> LlmOutput:
    """Simulate LLM-based hypothesis generation.

    Uses ground-truth category to make at least one strong hypothesis and
    adds a couple of weaker, generic ones.
    """

    workload_id = features.workload_id
    true_cat = GROUND_TRUTH_CATEGORIES.get(workload_id, "unknown")

    base_conf = 0.7 + 0.1 * min(1.0, features.anomaly_magnitude)
    weak_conf = 0.3

    strong_h = GeneratedHypothesis(
        id=f"{incident_id}-h1",
        description=f"Primary issue likely related to {true_cat} configuration or recent changes.",
        category=true_cat,
        confidence=float(min(0.95, base_conf)),
        evidence=(
            f"Anomaly magnitude={features.anomaly_magnitude:.3f}, "
            f"temporal_pattern={features.temporal_pattern_score:.3f}, "
            f"change_flag={features.change_flag:.1f}. "
            "Nearest neighbors: " + ", ".join(cluster.nearest_neighbors)
        ),
        proposed_tests="Inspect recent changes and replay failing traffic around anomaly window.",
    )

    generic_h = GeneratedHypothesis(
        id=f"{incident_id}-h2",
        description="Potential infrastructure-related bottleneck affecting latency and error rates.",
        category="infra",
        confidence=weak_conf,
        evidence="Elevated latency and error rates could stem from infra resource constraints.",
        proposed_tests="Check host saturation, throttling metrics, and network errors.",
    )

    unknown_h = GeneratedHypothesis(
        id=f"{incident_id}-h3",
        description="Unknown interaction between multiple components leading to emergent failure.",
        category="unknown",
        confidence=0.2,
        evidence="Residual unexplained anomaly after accounting for primary hypotheses.",
        proposed_tests="Correlate cross-service logs and traces to identify hidden dependencies.",
    )

    summary = (
        f"Incident {incident_id} shows anomaly magnitude {features.anomaly_magnitude:.2f} "
        f"and temporal score {features.temporal_pattern_score:.2f}. "
        f"Most similar past incidents: {', '.join(cluster.nearest_neighbors) or 'none'}."
    )

    return LlmOutput(hypotheses=[strong_h, generic_h, unknown_h], global_summary=summary)
