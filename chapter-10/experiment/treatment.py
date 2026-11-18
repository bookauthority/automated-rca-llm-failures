from __future__ import annotations

import random
from typing import Dict, List

from .models import make_models_for_phase
from .rca import RCAEngine
from .workloads import WorkloadConfig, generate_requests, get_workload_config


def _routing_weights_for_phase_treatment(phase: str) -> Dict[str, float]:
    """Treatment routing weights per phase.

    Similar to baseline, but we keep them separate so that an RCA engine
    could in principle inspect these. For now they are the same as
    baseline to keep the comparison fair; RCA detects the same
    regressions, but only the treatment variant computes them.
    """

    if phase == "phase0":
        return {"model_v1_stable": 1.0}
    if phase == "phase1":
        return {"model_v1_stable": 0.85, "model_v2_candidate_good": 0.15}
    if phase == "phase2":
        return {"model_v1_stable": 0.85, "model_v3_candidate_bad": 0.15}
    if phase == "phase3":
        return {"model_v1_stable": 0.4, "model_v3_candidate_bad": 0.6}
    if phase == "phase4":
        return {"model_v1_stable": 1.0}
    raise ValueError(f"Unknown phase: {phase}")


def _sample_model(rng: random.Random, weights: Dict[str, float]) -> str:
    total = sum(weights.values())
    r = rng.random() * total
    cumulative = 0.0
    for model_id, w in weights.items():
        cumulative += w
        if r <= cumulative:
            return model_id
    return next(reversed(weights.keys()))


def _phases() -> List[str]:
    return ["phase0", "phase1", "phase2", "phase3", "phase4"]


def run_treatment_for_workload(workload_id: str) -> Dict:
    """Run the treatment simulation for a given workload.

    Returns a dict with run_id, success, metrics, and num_requests.
    Treatment uses an RCAEngine to compute additional metrics.
    """

    workload = get_workload_config(workload_id)

    # Use a different but deterministic seed than baseline, still derived
    # from workload_id.
    rng = random.Random(2000 + hash(workload_id) % 1000)

    rca = RCAEngine()

    total_latency = 0.0
    total_quality = 0.0
    total_tokens = 0
    n_requests = 0

    for phase in _phases():
        models = make_models_for_phase(phase)
        weights = _routing_weights_for_phase_treatment(phase)
        requests = generate_requests(workload, phase, rng)
        for _req in requests:
            model_id = _sample_model(rng, weights)
            model = models[model_id]
            latency, tokens, quality = model.generate_response(rng)
            total_latency += latency
            total_quality += quality
            total_tokens += tokens
            n_requests += 1
            rca.record(model_id, latency, tokens, quality)

    if n_requests == 0:
        mean_latency = 0.0
        mean_quality = 0.0
        mean_tokens = 0.0
    else:
        mean_latency = total_latency / n_requests
        mean_quality = total_quality / n_requests
        mean_tokens = float(total_tokens) / n_requests

    rca_results = rca.analyze()
    detected_regressions = float(rca.detected_regressions)

    metrics = {
        "mean_latency_ms": float(mean_latency),
        "mean_quality": float(mean_quality),
        "mean_tokens": float(mean_tokens),
        "rca_detected_regressions": detected_regressions,
    }

    # Optionally we could further export details from rca_results in a
    # non-metric field, but metrics must remain flat numeric values.

    return {
        "run_id": f"treatment_{workload_id}_1",
        "success": True,
        "metrics": metrics,
        "num_requests": n_requests,
    }
