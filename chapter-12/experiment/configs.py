from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class RiskPolicy:
    # Simple risk policy keyed by incident_type
    risk_by_incident_type: Dict[str, str]

    # Automation behavior: for each risk level, whether to auto-apply
    auto_apply: Dict[str, bool]

    # For each risk level, whether human approval is required before execution
    requires_approval: Dict[str, bool]

    # Max concurrent automated actions allowed (blast radius proxy)
    max_concurrent_automated_actions: int


def baseline_risk_policy() -> RiskPolicy:
    """Baseline: no orchestrator; modeled by never auto-applying.

    We still provide a policy object for structural symmetry, but the
    ManualResponder ignores it and behaves with fixed latencies.
    """

    risk_by_type = {
        "prompt_regression": "medium",
        "routing_misconfiguration": "medium",
        "rag_retrieval_degradation": "medium",
        "tool_failure": "low",
        "latency_cost_regression": "medium",
    }
    auto_apply = {"low": False, "medium": False, "high": False}
    requires_approval = {"low": True, "medium": True, "high": True}
    return RiskPolicy(
        risk_by_incident_type=risk_by_type,
        auto_apply=auto_apply,
        requires_approval=requires_approval,
        max_concurrent_automated_actions=0,
    )


def treatment_risk_policy() -> RiskPolicy:
    """Treatment: guarded automated orchestrator.

    - Low risk: auto-apply without approval.
    - Medium risk: auto-apply, but require approval (modeled latency).
    - High risk: do not auto-apply.
    """

    risk_by_type = {
        "prompt_regression": "medium",
        "routing_misconfiguration": "low",
        "rag_retrieval_degradation": "medium",
        "tool_failure": "low",
        "latency_cost_regression": "medium",
    }
    auto_apply = {"low": True, "medium": True, "high": False}
    requires_approval = {"low": False, "medium": True, "high": True}
    return RiskPolicy(
        risk_by_incident_type=risk_by_type,
        auto_apply=auto_apply,
        requires_approval=requires_approval,
        max_concurrent_automated_actions=3,
    )
