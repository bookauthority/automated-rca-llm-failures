from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List

from .simulation import InteractionEvent


@dataclass
class PromptRegressionSignal:
    prompt_template_version: str
    hallucination_rate: float


def compute_hallucination_rate(events: Iterable[InteractionEvent]) -> float:
    total = 0
    hall = 0
    for e in events:
        total += 1
        if e.hallucination_consensus_label in {"mild", "severe"}:
            hall += 1
    if total == 0:
        return 0.0
    return hall / float(total)


def detect_prompt_regressions(events: Iterable[InteractionEvent]) -> List[PromptRegressionSignal]:
    """Simple regression detector.

    For each prompt version, compute hallucination rate. In a production
    system we would compare version N vs N-1 with proper tests; here we just
    return the per-version rates to be used for metrics or external
    comparison.
    """

    by_version: Dict[str, List[InteractionEvent]] = defaultdict(list)
    for e in events:
        by_version[e.prompt_template_version].append(e)

    signals: List[PromptRegressionSignal] = []
    for version, group in by_version.items():
        hr = compute_hallucination_rate(group)
        signals.append(PromptRegressionSignal(prompt_template_version=version, hallucination_rate=hr))
    return signals


__all__ = ["PromptRegressionSignal", "detect_prompt_regressions", "compute_hallucination_rate"]
