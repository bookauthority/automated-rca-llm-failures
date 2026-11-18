from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from .clustering import cluster_incident
from .config import WorkloadConfig
from .features import IncidentFeatures, compute_incident_features, simulate_pipeline_runtime
from .llm_simulator import generate_hypotheses
from .ranking import rank_hypotheses


@dataclass
class TreatmentResult:
    time_to_first_plausible_root_cause: float
    ai_pipeline_runtime: float


def run_treatment_rca(
    workload: WorkloadConfig,
    historical: Dict[str, IncidentFeatures],
) -> TreatmentResult:
    """Run the AI-assisted RCA pipeline for a single incident.

    Steps (all simulated, deterministic):
    - Feature engineering
    - Clustering / similarity search
    - LLM-style hypothesis generation
    - Ranking & pruning
    - Derive time-to-first-plausible-root-cause and pipeline runtime.
    """

    features = compute_incident_features(workload, variant="treatment")
    incident_id = workload.workload_id + "::incident"

    cluster_result = cluster_incident(incident_id, features, historical)
    llm_output = generate_hypotheses(incident_id, features, cluster_result)
    ranked = rank_hypotheses(features, llm_output.hypotheses)

    # AI-assisted process should find plausible root cause faster than baseline.
    # Use anomaly magnitude and alignment of top hypothesis to approximate.
    if ranked:
        top = ranked[0]
        # Faster when score is high and anomaly is strong.
        base = 12.0
        score_factor = (1.0 - top.ranker_score) * 6.0
        anomaly_factor = max(0.0, 2.0 - 2.0 * min(1.0, features.anomaly_magnitude))
        t_first = base + score_factor + anomaly_factor
    else:
        t_first = 25.0

    t_first = float(max(3.0, min(90.0, t_first)))

    # Synthetic runtime of the AI pipeline.
    runtime = simulate_pipeline_runtime(features, pipeline_complexity=1.0)

    return TreatmentResult(
        time_to_first_plausible_root_cause=t_first,
        ai_pipeline_runtime=runtime,
    )
