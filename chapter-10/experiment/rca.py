from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class AggregateMetrics:
    count: int = 0
    total_latency: float = 0.0
    total_quality: float = 0.0
    total_tokens: float = 0.0

    def update(self, latency: float, tokens: int, quality: float) -> None:
        self.count += 1
        self.total_latency += latency
        self.total_quality += quality
        self.total_tokens += float(tokens)

    def means(self) -> Tuple[float, float, float]:
        if self.count == 0:
            return 0.0, 0.0, 0.0
        return (
            self.total_latency / self.count,
            self.total_quality / self.count,
            self.total_tokens / self.count,
        )


@dataclass
class RCAEngine:
    """Very simple RCA engine for model drift/routing issues.

    It aggregates per-model metrics and compares canary vs. stable models.
    """

    stable_model_id: str = "model_v1_stable"
    aggregates: Dict[str, AggregateMetrics] = field(default_factory=dict)
    # Simple counts of detected regression episodes
    detected_regressions: int = 0

    def record(self, model_id: str, latency: float, tokens: int, quality: float) -> None:
        if model_id not in self.aggregates:
            self.aggregates[model_id] = AggregateMetrics()
        self.aggregates[model_id].update(latency, tokens, quality)

    def _compare_to_stable(self, model_id: str) -> Dict[str, float]:
        if self.stable_model_id not in self.aggregates:
            return {"delta_quality": 0.0, "delta_latency": 0.0, "delta_tokens": 0.0}
        stable = self.aggregates[self.stable_model_id]
        target = self.aggregates.get(model_id)
        if not target or target.count == 0:
            return {"delta_quality": 0.0, "delta_latency": 0.0, "delta_tokens": 0.0}
        s_lat, s_qual, s_tok = stable.means()
        t_lat, t_qual, t_tok = target.means()
        return {
            "delta_quality": t_qual - s_qual,
            "delta_latency": t_lat - s_lat,
            "delta_tokens": t_tok - s_tok,
        }

    def analyze(self) -> Dict[str, Dict[str, float]]:
        """Analyze per-model metrics and detect regressions.

        This is intentionally simplistic: if a non-stable model has
        significantly lower quality or significantly higher latency than the
        stable model, we count a regression. Attribution is limited to a
        numeric count that treatment can expose as
        `rca_detected_regressions`.
        """

        results: Dict[str, Dict[str, float]] = {}
        self.detected_regressions = 0
        for model_id in self.aggregates:
            if model_id == self.stable_model_id:
                continue
            deltas = self._compare_to_stable(model_id)
            dq = deltas["delta_quality"]
            dl = deltas["delta_latency"]
            # Regression thresholds (tuned for these synthetic values)
            quality_regressed = dq < -0.05
            latency_regressed = dl > 5.0
            if quality_regressed or latency_regressed:
                self.detected_regressions += 1
            deltas["quality_regressed"] = 1.0 if quality_regressed else 0.0
            deltas["latency_regressed"] = 1.0 if latency_regressed else 0.0
            results[model_id] = deltas
        return results
