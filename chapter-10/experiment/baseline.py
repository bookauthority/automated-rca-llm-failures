from __future__ import annotations

import random
from typing import Dict, List, Tuple

from .models import make_models_for_phase
from .workloads import WorkloadConfig, generate_requests, get_workload_config


def _routing_weights_for_phase(phase: str) -> Dict[str, float]:
    """Baseline routing weights per phase.

    - Phase 0: only stable.
    - Phase 1: stable 0.85, good canary 0.15.
    - Phase 2: stable 0.85, bad canary 0.15.
    - Phase 3: routing misconfig (too much bad canary): stable 0.4, bad 0.6.
    - Phase 4: back to stable-only.
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
    # Fallback to last key
    return next(reversed(weights.keys()))


def _phases() -> List[str]:
    return ["phase0", "phase1", "phase2", "phase3", "phase4"]


def run_baseline_for_workload(workload_id: str) -> Dict:
    """Run the baseline simulation for a given workload.

    Returns a dict with run_id, success, metrics, and num_requests.
    """

    workload = get_workload_config(workload_id)

    # Use a stable seed derived from workload_id to make baseline deterministic
    rng = random.Random(1000 + hash(workload_id) % 1000)

    total_latency = 0.0
    total_quality = 0.0
    total_tokens = 0
    n_requests = 0

    for phase in _phases():
        models = make_models_for_phase(phase)
        weights = _routing_weights_for_phase(phase)
        requests = generate_requests(workload, phase, rng)
        for _req in requests:
            model_id = _sample_model(rng, weights)
            model = models[model_id]
            latency, tokens, quality = model.generate_response(rng)
            total_latency += latency
            total_quality += quality
            total_tokens += tokens
            n_requests += 1

    if n_requests == 0:
        mean_latency = 0.0
        mean_quality = 0.0
        mean_tokens = 0.0
    else:
        mean_latency = total_latency / n_requests
        mean_quality = total_quality / n_requests
        mean_tokens = float(total_tokens) / n_requests

    metrics = {
        "mean_latency_ms": float(mean_latency),
        "mean_quality": float(mean_quality),
        "mean_tokens": float(mean_tokens),
    }

    return {
        "run_id": f"baseline_{workload_id}_1",
        "success": True,
        "metrics": metrics,
        "num_requests": n_requests,
    }
