from __future__ import annotations

from typing import List, Dict


def summarize_latency(latencies: List[float]) -> Dict[str, float]:
    if not latencies:
        return {"mean": 0.0, "p50": 0.0, "p95": 0.0}
    xs = sorted(latencies)
    n = len(xs)
    mean = sum(xs) / n

    def _percentile(p: float) -> float:
        if n == 1:
            return xs[0]
        k = int(p * (n - 1))
        return xs[k]

    return {
        "mean": float(mean),
        "p50": float(_percentile(0.5)),
        "p95": float(_percentile(0.95)),
    }
