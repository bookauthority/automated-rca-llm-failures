from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List

from .simulation import InteractionEvent


@dataclass
class PolicySignal:
    policy_config: str
    violation_rate: float


def compute_policy_violation_rate(events: Iterable[InteractionEvent]) -> float:
    total = 0
    viol = 0
    for e in events:
        total += 1
        if e.policy_decision == "block" and "policy_violation" in e.policy_reason_codes:
            viol += 1
    if total == 0:
        return 0.0
    return viol / float(total)


def detect_policy_misconfig(events: Iterable[InteractionEvent]) -> List[PolicySignal]:
    by_cfg: Dict[str, List[InteractionEvent]] = defaultdict(list)
    for e in events:
        by_cfg[e.policy_config].append(e)

    signals: List[PolicySignal] = []
    for cfg, group in by_cfg.items():
        vr = compute_policy_violation_rate(group)
        signals.append(PolicySignal(policy_config=cfg, violation_rate=vr))
    return signals


__all__ = ["PolicySignal", "detect_policy_misconfig", "compute_policy_violation_rate"]
