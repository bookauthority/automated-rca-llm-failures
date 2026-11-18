from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .core import SyntheticCorpus, WorkloadConfig, make_rng


@dataclass
class WorkloadRunResult:
    success: bool
    metrics: Dict[str, float]
    notes: str


@dataclass
class RCAEvent:
    time_step: int
    kind: str
    payload: Dict[str, float]


@dataclass
class IncidentDetection:
    incident_type: str
    detected_step: int
    details: Dict[str, float]


class RCASubsystem:
    """Very small in-memory RCA engine for data and tooling.

    This mimics structured events and simple anomaly detection:

    - Tracks ingestion status and retrieval coverage for a namespace.
    - Monitors tool failure rates for flakiness.
    - Emits synthetic 'incident detections' with detection step.
    """

    def __init__(self, detection_window: int = 5) -> None:
        self.events: List[RCAEvent] = []
        self.detections: List[IncidentDetection] = []
        self.detection_window = detection_window
        self.retrieval_history: List[Dict[str, float]] = []
        self.tool_fail_history: List[Dict[str, float]] = []
        self.ingestion_last_update_step: Optional[int] = None

    def record_ingestion(self, step: int, namespace: str, docs_added: int) -> None:
        self.events.append(
            RCAEvent(step, "ingestion_batch", {"docs_added": float(docs_added)})
        )
        if docs_added > 0:
            self.ingestion_last_update_step = step

    def record_retrieval(self, step: int, includes_latest: int) -> None:
        self.events.append(
            RCAEvent(step, "retrieval_query", {"includes_latest": float(includes_latest)})
        )
        self.retrieval_history.append(
            {"step": float(step), "includes_latest": float(includes_latest)}
        )
        self._maybe_detect_ingestion_incident(step)

    def record_tool_call(self, step: int, success: bool) -> None:
        self.events.append(
            RCAEvent(step, "tool_call", {"success": float(1 if success else 0)})
        )
        self.tool_fail_history.append(
            {"step": float(step), "success": float(1 if success else 0)}
        )
        self._maybe_detect_tool_incident(step)

    def _maybe_detect_ingestion_incident(self, step: int) -> None:
        if self.ingestion_last_update_step is None:
            return
        # If we have not ingested docs for more than detection_window steps
        # and retrievals increasingly miss latest, flag incident.
        if step - self.ingestion_last_update_step < self.detection_window:
            return

        window = [r for r in self.retrieval_history if step - self.detection_window < r["step"] <= step]
        if not window:
            return
        miss_rate = sum(1.0 for r in window if r["includes_latest"] == 0.0) / float(len(window))
        if miss_rate > 0.6 and not any(d.incident_type == "data_ingestion" for d in self.detections):
            self.detections.append(
                IncidentDetection(
                    incident_type="data_ingestion",
                    detected_step=step,
                    details={"miss_rate": float(miss_rate)},
                )
            )

    def _maybe_detect_tool_incident(self, step: int) -> None:
        window = [h for h in self.tool_fail_history if step - self.detection_window < h["step"] <= step]
        if not window:
            return
        fail_rate = sum(1.0 for h in window if h["success"] == 0.0) / float(len(window))
        if fail_rate > 0.3 and not any(d.incident_type == "tool_flakiness" for d in self.detections):
            self.detections.append(
                IncidentDetection(
                    incident_type="tool_flakiness",
                    detected_step=step,
                    details={"fail_rate": float(fail_rate)},
                )
            )


def _simulate_tool_call(step: int, cfg: WorkloadConfig, rng, rca: RCASubsystem) -> bool:
    """Same underlying behavior as baseline, but instrumented for RCA."""

    if cfg.workload_id != "WL3-flaky-tool-endpoint":
        success = rng.random() >= 0.02
        rca.record_tool_call(step, success)
        return success

    if cfg.flaky_phases:
        for start, end, rate in cfg.flaky_phases:
            if start <= step < end:
                success = rng.random() >= rate
                rca.record_tool_call(step, success)
                return success
    success = rng.random() >= 0.02
    rca.record_tool_call(step, success)
    return success


def run_treatment_workload(cfg: WorkloadConfig) -> WorkloadRunResult:
    """Run a workload under the treatment (RCA-enabled) variant."""

    rng = make_rng(cfg.seed)
    corpus = SyntheticCorpus()
    rca = RCASubsystem(detection_window=5)

    requests_total = 0
    retrieval_stale_or_missing = 0
    tool_failures = 0

    ingestion_active = True

    data_ingestion_detection_latency = None
    tool_flakiness_detection_latency = None

    for step in range(cfg.steps):
        # Ingestion and RCA instrumentation for WL2.
        if cfg.workload_id == "WL2-broken-ingestion-job":
            if cfg.ingestion_break_step is not None and step >= cfg.ingestion_break_step:
                ingestion_active = False
            if ingestion_active:
                corpus.ingest_new_docs("policies/current", count=1)
                rca.record_ingestion(step, "policies/current", docs_added=1)
            else:
                # Explicitly record zero docs ingested.
                rca.record_ingestion(step, "policies/current", docs_added=0)

        # Simulate requests.
        for _ in range(5):
            requests_total += 1
            r = rng.random()

            if r < cfg.rag_fraction:
                namespace = "policies/current"
                stats = corpus.simulate_retrieval(namespace, query_kind="current")
                if stats["includes_latest"] == 0:
                    retrieval_stale_or_missing += 1
                rca.record_retrieval(step, stats["includes_latest"])

            elif r < cfg.rag_fraction + cfg.tool_fraction:
                ok = _simulate_tool_call(step, cfg, rng, rca)
                if not ok:
                    tool_failures += 1

            else:
                namespace = "policies/current"
                stats = corpus.simulate_retrieval(namespace, query_kind="current")
                if stats["includes_latest"] == 0:
                    retrieval_stale_or_missing += 1
                rca.record_retrieval(step, stats["includes_latest"])
                ok = _simulate_tool_call(step, cfg, rng, rca)
                if not ok:
                    tool_failures += 1

        # After processing this step, see if any new detections occurred and
        # compute detection latency in synthetic time units.
        for detection in rca.detections:
            if detection.incident_type == "data_ingestion" and data_ingestion_detection_latency is None:
                # Ground-truth incident start for WL2 is ingestion_break_step.
                if cfg.workload_id == "WL2-broken-ingestion-job" and cfg.ingestion_break_step is not None:
                    data_ingestion_detection_latency = float(
                        detection.detected_step - cfg.ingestion_break_step
                    )
            if detection.incident_type == "tool_flakiness" and tool_flakiness_detection_latency is None:
                if (
                    cfg.workload_id == "WL3-flaky-tool-endpoint"
                    and cfg.flaky_tool_start_step is not None
                ):
                    tool_flakiness_detection_latency = float(
                        detection.detected_step - cfg.flaky_tool_start_step
                    )

    metrics: Dict[str, float] = {
        "requests_total": float(requests_total),
        "retrieval_stale_or_missing": float(retrieval_stale_or_missing),
        "tool_failures": float(tool_failures),
    }

    # Only include RCA-specific metrics when they are actually measurable.
    if data_ingestion_detection_latency is not None:
        metrics["rca_detection_latency_units_data_ingestion"] = float(
            data_ingestion_detection_latency
        )
    if tool_flakiness_detection_latency is not None:
        metrics["rca_detection_latency_units_tool_flakiness"] = float(
            tool_flakiness_detection_latency
        )

    notes = (
        "Treatment run with RCA subsystem. Emits synthetic ingestion, "
        "retrieval, and tool events, and derives incident detection "
        "latencies in discrete time steps."
    )

    return WorkloadRunResult(success=True, metrics=metrics, notes=notes)
