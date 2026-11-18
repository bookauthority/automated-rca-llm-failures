from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Tuple


@dataclass
class SimulatedModel:
    """A simple stochastic model of LLM behavior.

    Each call returns (latency_ms, tokens, quality_score).
    The distributions differ by model and phase to mimic drift.
    """

    name: str
    base_latency_ms: float
    latency_jitter_ms: float
    base_quality: float
    quality_jitter: float
    base_tokens: float
    token_jitter: float

    def generate_response(self, rng: random.Random) -> Tuple[float, int, float]:
        # Latency with bounded jitter
        latency = self.base_latency_ms + self.latency_jitter_ms * (rng.random() - 0.5) * 2.0
        latency = max(1.0, latency)

        # Tokens with Poisson-like integer variability (approx using normal)
        tokens = self.base_tokens + self.token_jitter * (rng.random() - 0.5) * 2.0
        tokens = max(1.0, tokens)
        tokens_int = int(round(tokens))

        # Quality score between 0 and 1
        quality = self.base_quality + self.quality_jitter * (rng.random() - 0.5) * 2.0
        quality = max(0.0, min(1.0, quality))

        return latency, tokens_int, quality


def make_models_for_phase(phase: str) -> dict:
    """Return a mapping of model_id to SimulatedModel for a given phase.

    Phases roughly correspond to:
    - phase0: warm-up, only stable model used
    - phase1: good canary rollout
    - phase2: bad canary rollout (model drift/regression)
    - phase3: routing misconfiguration (same models, but weights differ)
    - phase4: upstream change (modeled as modest quality shift for all)

    The treatment/baseline orchestrators decide which phases to run; this
    helper just defines consistent model behavior by name per phase.
    """

    # Stable baseline model, generally good and consistent
    stable = SimulatedModel(
        name="model_v1_stable",
        base_latency_ms=20.0,
        latency_jitter_ms=5.0,
        base_quality=0.85,
        quality_jitter=0.05,
        base_tokens=80.0,
        token_jitter=10.0,
    )

    # Good candidate: slightly better quality, similar latency
    good = SimulatedModel(
        name="model_v2_candidate_good",
        base_latency_ms=21.0,
        latency_jitter_ms=6.0,
        base_quality=0.88,
        quality_jitter=0.05,
        base_tokens=82.0,
        token_jitter=10.0,
    )

    # Bad candidate: worse quality, higher latency and tokens
    bad = SimulatedModel(
        name="model_v3_candidate_bad",
        base_latency_ms=35.0,
        latency_jitter_ms=8.0,
        base_quality=0.70,
        quality_jitter=0.08,
        base_tokens=110.0,
        token_jitter=15.0,
    )

    # For simplicity, we use the same definitions per phase; the orchestration
    # code will change routing and which candidate is enabled. For phase4,
    # we conceptually represent an upstream change by slightly reducing
    # quality across all models in the orchestrator rather than here.

    return {
        stable.name: stable,
        good.name: good,
        bad.name: bad,
    }
