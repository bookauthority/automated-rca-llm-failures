from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Tuple

# Workload identifiers (shared between baseline and treatment)
WL1_ID = "WL1-normal-mixed-traffic"
WL2_ID = "WL2-broken-ingestion-job"
WL3_ID = "WL3-flaky-tool-endpoint"


@dataclass
class WorkloadConfig:
    """Configuration for a simulated workload.

    Attributes
    ----------
    workload_id:
        Identifier such as WL1, WL2, WL3.
    seed:
        Base seed for deterministic RNG.
    steps:
        Number of discrete time steps in the simulation.
    rag_fraction:
        Fraction of requests that use RAG only.
    tool_fraction:
        Fraction that use tools only.
    combined_fraction:
        Fraction that use both RAG and tools.
    ingestion_break_step:
        For WL2: step at which ingestion silently breaks (None if NA).
    flaky_tool_start_step:
        For WL3: step where flakiness begins (None if NA).
    flaky_tool_end_step:
        For WL3: step where flakiness ends (None if NA).
    flaky_phases:
        For WL3: list of (start_step, end_step, failure_rate) intervals.
    """

    workload_id: str
    seed: int
    steps: int
    rag_fraction: float
    tool_fraction: float
    combined_fraction: float
    ingestion_break_step: int | None = None
    flaky_tool_start_step: int | None = None
    flaky_tool_end_step: int | None = None
    flaky_phases: List[Tuple[int, int, float]] | None = None


# --- Simple synthetic corpus and retrieval model ---------------------------------


class SyntheticCorpus:
    """In-memory corpus partitioned into namespaces.

    Retrieval is simulated via simple keyword lookups on toy documents
    represented by integers and namespace tags.
    """

    def __init__(self) -> None:
        # Each namespace contains a list of document IDs (ints).
        self.namespaces: Dict[str, List[int]] = {
            "policies/current": list(range(100, 130)),
            "policies/archive": list(range(200, 230)),
            "products": list(range(300, 360)),
        }
        # Latest ingested doc index per namespace (for freshness checks).
        self.latest_doc_index: Dict[str, int] = {
            ns: len(ids) - 1 for ns, ids in self.namespaces.items()
        }

    def ingest_new_docs(self, namespace: str, count: int) -> None:
        """Append new synthetic docs to a namespace."""

        existing = self.namespaces.setdefault(namespace, [])
        if existing:
            start_id = max(existing) + 1
        else:
            start_id = 1_000
        for i in range(count):
            existing.append(start_id + i)
        self.latest_doc_index[namespace] = len(existing) - 1

    def simulate_retrieval(self, namespace: str, query_kind: str) -> Dict[str, int]:
        """Return retrieval stats for a query.

        Parameters
        ----------
        namespace:
            Corpus partition to query.
        query_kind:
            Either "current" (asks for latest documents) or
            "generic" (asks for any document).

        Returns
        -------
        dict with keys:
            total_docs: doc count in namespace
            hits: number of documents deemed relevant
            includes_latest: 1 if latest doc is included, else 0
        """

        docs = self.namespaces.get(namespace, [])
        total = len(docs)
        if total == 0:
            return {"total_docs": 0, "hits": 0, "includes_latest": 0}

        if query_kind == "current":
            # Simulate that current queries should hit the last few docs.
            hits = min(5, total)
            includes_latest = 1 if total > 0 else 0
        else:
            hits = min(3, total)
            includes_latest = 0

        return {
            "total_docs": total,
            "hits": hits,
            "includes_latest": includes_latest,
        }


# --- Workload configuration helpers ---------------------------------------------


def make_wl1_config(seed: int) -> WorkloadConfig:
    # 30 minutes at 1 synthetic step per minute => 30 steps.
    return WorkloadConfig(
        workload_id=WL1_ID,
        seed=seed,
        steps=30,
        rag_fraction=0.7,
        tool_fraction=0.2,
        combined_fraction=0.1,
    )


def make_wl2_config(seed: int) -> WorkloadConfig:
    # 45 minutes, ingestion breaks at minute 15 -> step 15.
    return WorkloadConfig(
        workload_id=WL2_ID,
        seed=seed,
        steps=45,
        rag_fraction=0.7,
        tool_fraction=0.2,
        combined_fraction=0.1,
        ingestion_break_step=15,
    )


def make_wl3_config(seed: int) -> WorkloadConfig:
    # 45 minutes, flakiness between minute 10 and 35.
    flaky_start = 10
    # Two phases with different failure rates, as per high-level spec.
    phase1_duration = 10
    phase2_duration = 15
    phase1 = (flaky_start, flaky_start + phase1_duration, 0.4)
    phase2 = (
        flaky_start + phase1_duration,
        flaky_start + phase1_duration + phase2_duration,
        0.2,
    )
    return WorkloadConfig(
        workload_id=WL3_ID,
        seed=seed,
        steps=45,
        rag_fraction=0.2,
        tool_fraction=0.6,
        combined_fraction=0.2,
        flaky_tool_start_step=flaky_start,
        flaky_tool_end_step=flaky_start + phase1_duration + phase2_duration,
        flaky_phases=[phase1, phase2],
    )


# --- Utility functions ----------------------------------------------------------


def make_rng(seed: int) -> random.Random:
    return random.Random(seed)
