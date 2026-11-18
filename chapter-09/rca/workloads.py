from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class PhaseConfig:
    name: str
    duration_minutes: int
    configuration: Dict[str, str]
    change_description: str | None = None


@dataclass(frozen=True)
class Workload:
    name: str
    workload_id: str
    description: str
    phases: List[PhaseConfig]
    request_rate_rps: float


def define_workloads() -> List[Workload]:
    """Define W1, W2, W3 as simplified deterministic workloads.

    We ignore actual timestamps/durations in seconds and instead map
    `duration_minutes` to a number of synthetic requests, preserving relative
    ratios between phases.
    """

    # Helper to convert minutes into a small integer number of requests.
    def minutes_to_requests(minutes: int, rps: float) -> int:
        # Use a compressed time-scale so the experiment finishes quickly.
        # We interpret 1 "simulated minute" as 3 real requests here.
        base = minutes * 3
        if base <= 0:
            return 1
        return base

    # W1: prompt regression detection
    w1_phases = [
        PhaseConfig(
            name="W1-baseline-prompt-v1",
            duration_minutes=20,
            configuration={
                "prompt_template_version": "answering-assistant-v1",
                "retrieval_state": "healthy",
                "model_version": "model-A-stable",
                "policy_config": "policy-v1",
            },
        ),
        PhaseConfig(
            name="W1-prompt-regression-v2",
            duration_minutes=20,
            configuration={
                "prompt_template_version": "answering-assistant-v2-regressed",
                "retrieval_state": "healthy",
                "model_version": "model-A-stable",
                "policy_config": "policy-v1",
            },
            change_description=(
                "Prompt updated to emphasize creativity and verbosity, "
                "de-emphasizing faithfulness to context."
            ),
        ),
        PhaseConfig(
            name="W1-prompt-fix-v3",
            duration_minutes=20,
            configuration={
                "prompt_template_version": "answering-assistant-v3-fixed",
                "retrieval_state": "healthy",
                "model_version": "model-A-stable",
                "policy_config": "policy-v1",
            },
            change_description=(
                "Prompt revised to require strict grounding to retrieved "
                "context and avoid fabrication."
            ),
        ),
    ]

    w1 = Workload(
        name="W1-prompt-regression-detection",
        workload_id="W1-prompt-regression-detection",
        description=(
            "Synthetic workload focusing on detecting and diagnosing "
            "prompt/template regressions."
        ),
        phases=w1_phases,
        request_rate_rps=1.0,
    )

    # W2: RAG hallucination incident
    w2_phases = [
        PhaseConfig(
            name="W2-healthy-rag",
            duration_minutes=30,
            configuration={
                "retrieval_state": "healthy",
                "index_version": "index-v1",
                "embedding_model_version": "embed-A",
                "prompt_template_version": "rag-assistant-v1",
                "model_version": "model-A-stable",
                "policy_config": "policy-v1",
            },
        ),
        PhaseConfig(
            name="W2-retrieval-degradation",
            duration_minutes=30,
            configuration={
                "retrieval_state": "degraded",
                "index_version": "index-v2-buggy",
                "embedding_model_version": "embed-B-misaligned",
                "prompt_template_version": "rag-assistant-v1",
                "model_version": "model-A-stable",
                "policy_config": "policy-v1",
            },
            change_description=(
                "Bad ingestion/indexing: missing docs and misaligned "
                "embedding model cause recall drop."
            ),
        ),
        PhaseConfig(
            name="W2-prompt-compensation",
            duration_minutes=30,
            configuration={
                "retrieval_state": "degraded",
                "index_version": "index-v2-buggy",
                "embedding_model_version": "embed-B-misaligned",
                "prompt_template_version": "rag-assistant-v2-heuristic-fix",
                "model_version": "model-A-stable",
                "policy_config": "policy-v1",
            },
            change_description=(
                "Prompt tweaked to encourage answers even with incomplete "
                "context, increasing hallucinations."
            ),
        ),
    ]

    w2 = Workload(
        name="W2-rag-hallucination-incident",
        workload_id="W2-rag-hallucination-incident",
        description=(
            "Controlled RAG hallucination incident with retrieval "
            "degradation and prompt compensation."
        ),
        phases=w2_phases,
        request_rate_rps=2.0,
    )

    # W3: policy failures
    w3_phases = [
        PhaseConfig(
            name="W3-healthy-policy",
            duration_minutes=20,
            configuration={
                "policy_config": "policy-v1",
                "policy_engine": "moderation-engine-A",
                "prompt_template_version": "policy-aware-assistant-v1",
                "retrieval_state": "healthy",
                "model_version": "model-A-stable",
            },
        ),
        PhaseConfig(
            name="W3-overblocking-policy-change",
            duration_minutes=20,
            configuration={
                "policy_config": "policy-v2-stricter",
                "policy_engine": "moderation-engine-A",
                "prompt_template_version": "policy-aware-assistant-v1",
                "retrieval_state": "healthy",
                "model_version": "model-A-stable",
            },
            change_description=(
                "Stricter rules block some benign content, increasing "
                "policy violations without more hallucinations."
            ),
        ),
        PhaseConfig(
            name="W3-underblocking-policy-bug",
            duration_minutes=20,
            configuration={
                "policy_config": "policy-v3-buggy",
                "policy_engine": "moderation-engine-A",
                "prompt_template_version": "policy-aware-assistant-v1",
                "retrieval_state": "healthy",
                "model_version": "model-A-stable",
            },
            change_description=(
                "Buggy rules fail to block some disallowed content, "
                "leading to policy-violation incidents."
            ),
        ),
    ]

    w3 = Workload(
        name="W3-policy-failure-incident",
        workload_id="W3-policy-failure-incident",
        description=(
            "Scenario targeting policy, moderation, and compliance filter "
            "RCA."
        ),
        phases=w3_phases,
        request_rate_rps=1.0,
    )

    return [w1, w2, w3]


__all__ = ["Workload", "PhaseConfig", "define_workloads"]
