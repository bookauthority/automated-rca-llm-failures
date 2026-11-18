from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from .core import SyntheticCorpus, WorkloadConfig, make_rng


@dataclass
class WorkloadRunResult:
    success: bool
    metrics: Dict[str, float]
    notes: str


def _simulate_tool_call(step: int, cfg: WorkloadConfig, rng) -> bool:
    """Return True if tool call succeeded, False if failed.

    Baseline uses the same underlying behavior as treatment so that the
    comparison is fair. For WL3, flakiness is injected based on phases.
    """

    if cfg.workload_id != "WL3-flaky-tool-endpoint":
        # Simple 2% background failure rate.
        return rng.random() >= 0.02

    # WL3: tool is flaky in specified phases.
    if cfg.flaky_phases:
        for start, end, rate in cfg.flaky_phases:
            if start <= step < end:
                return rng.random() >= rate
    # Outside flakiness windows: 2% background failure.
    return rng.random() >= 0.02


def run_baseline_workload(cfg: WorkloadConfig) -> WorkloadRunResult:
    """Run a workload under the baseline (non-RCA) variant.

    Metrics are limited and no specialized ingestion or tool RCA is used.
    """

    rng = make_rng(cfg.seed)
    corpus = SyntheticCorpus()

    requests_total = 0
    retrieval_stale_or_missing = 0
    tool_failures = 0

    # Simulated ingestion behavior for WL2. Baseline has no detection.
    ingestion_active = True

    for step in range(cfg.steps):
        # Ingestion for WL2: silently stop after ingestion_break_step.
        if cfg.workload_id == "WL2-broken-ingestion-job":
            if cfg.ingestion_break_step is not None and step >= cfg.ingestion_break_step:
                ingestion_active = False
            # When active, ingest 1 new doc per step into policies/current.
            if ingestion_active:
                corpus.ingest_new_docs("policies/current", count=1)

        # Request mix.
        for _ in range(5):  # 5 requests per step; magnitude is arbitrary but bounded.
            requests_total += 1

            r = rng.random()
            if r < cfg.rag_fraction:
                # RAG-only query.
                namespace = "policies/current"
                stats = corpus.simulate_retrieval(namespace, query_kind="current")
                # Consider response stale if it does not include latest.
                if stats["includes_latest"] == 0:
                    retrieval_stale_or_missing += 1

            elif r < cfg.rag_fraction + cfg.tool_fraction:
                # Tool-only request
                ok = _simulate_tool_call(step, cfg, rng)
                if not ok:
                    tool_failures += 1

            else:
                # Combined RAG + tool
                namespace = "policies/current"
                stats = corpus.simulate_retrieval(namespace, query_kind="current")
                if stats["includes_latest"] == 0:
                    retrieval_stale_or_missing += 1
                ok = _simulate_tool_call(step, cfg, rng)
                if not ok:
                    tool_failures += 1

    metrics: Dict[str, float] = {
        "requests_total": float(requests_total),
        "retrieval_stale_or_missing": float(retrieval_stale_or_missing),
        "tool_failures": float(tool_failures),
    }

    notes = (
        "Baseline run without RCA subsystem. Ingestion and tool issues "
        "are not explicitly detected, only reflected via coarse "
        "staleness counts and tool failure counts."
    )

    return WorkloadRunResult(success=True, metrics=metrics, notes=notes)
