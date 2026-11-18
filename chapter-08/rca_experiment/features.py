from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, List

from .config import WorkloadConfig, SEEDS


@dataclass
class IncidentFeatures:
    """Engineered features for a single incident.

    These approximate aggregations, temporal patterns, and context flags.
    All values are numeric and deterministic given a seed.
    """

    workload_id: str
    window_request_rate: float
    window_error_rate: float
    window_latency_p95: float
    change_flag: float
    anomaly_magnitude: float
    temporal_pattern_score: float

    def as_vector(self) -> List[float]:
        return [
            self.window_request_rate,
            self.window_error_rate,
            self.window_latency_p95,
            self.change_flag,
            self.anomaly_magnitude,
            self.temporal_pattern_score,
        ]


def _rng_for(workload: WorkloadConfig, variant: str) -> random.Random:
    base_seed = SEEDS[workload.workload_id]
    # Distinguish baseline vs treatment but keep deterministic per workload.
    return random.Random(base_seed + (0 if variant == "baseline" else 1000))


def compute_incident_features(workload: WorkloadConfig, variant: str) -> IncidentFeatures:
    """Compute deterministic synthetic features for the workload.

    The variant is included only to allow tiny, bounded perturbations between
    baseline and treatment computations while keeping them comparable.
    """

    rng = _rng_for(workload, variant)
    # Base scales depend on difficulty: harder incidents have subtler signals.
    base_rate = 100.0 * (1.0 - 0.3 * workload.difficulty)
    base_error = 0.01 + 0.05 * workload.difficulty
    base_latency = 200.0 + 300.0 * workload.difficulty

    noise = workload.base_noise

    window_request_rate = base_rate * (1.0 + noise * (rng.random() - 0.5))
    window_error_rate = base_error * (1.0 + 2.0 * noise * (rng.random() - 0.5))
    window_latency_p95 = base_latency * (1.0 + 1.5 * noise * (rng.random() - 0.5))

    # change_flag = whether a config/prompt/model change occurred in window.
    change_flag = 1.0 if rng.random() < 0.6 else 0.0

    # anomaly_magnitude scales with difficulty and randomness.
    anomaly_magnitude = (0.5 + workload.difficulty) * (1.0 + noise * (rng.random() - 0.5))

    # temporal_pattern_score: simple periodic pattern + randomness.
    angle = (SEEDS[workload.workload_id] % 360) * math.pi / 180.0
    temporal_pattern_score = math.sin(angle) * (1.0 + 0.3 * workload.difficulty)
    temporal_pattern_score += noise * (rng.random() - 0.5)

    return IncidentFeatures(
        workload_id=workload.workload_id,
        window_request_rate=window_request_rate,
        window_error_rate=window_error_rate,
        window_latency_p95=window_latency_p95,
        change_flag=change_flag,
        anomaly_magnitude=anomaly_magnitude,
        temporal_pattern_score=temporal_pattern_score,
    )


def feature_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute cosine similarity between two feature vectors.

    Returns a value between -1 and 1.
    """

    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for a, b in zip(vec_a, vec_b):
        dot += a * b
        norm_a += a * a
        norm_b += b * b
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / math.sqrt(norm_a * norm_b)


def simulate_pipeline_runtime(features: IncidentFeatures, pipeline_complexity: float) -> float:
    """Synthetic runtime in seconds for the AI pipeline.

    The runtime is a deterministic, bounded function of the anomaly magnitude,
    temporal pattern, and a pipeline_complexity scalar.
    """

    base = 0.2 + 0.3 * pipeline_complexity
    extra = 0.4 * features.anomaly_magnitude + 0.1 * abs(features.temporal_pattern_score)
    # Bound runtime to <= 2 seconds to ensure fast tests.
    return float(min(2.0, base + extra))
