from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

from .configs import baseline_risk_policy, treatment_risk_policy, RiskPolicy


# -------------------- Data structures --------------------


@dataclass
class Incident:
    incident_id: str
    incident_type: str
    severity: str
    detected_at_min: float
    canonical_remediation: str


@dataclass
class RCAOutput:
    incident_id: str
    detected_at_min: float
    incident_type: str
    severity: str
    suspected_root_causes: List[str]
    recommended_actions: List[str]
    confidence_score: float


@dataclass
class RemediationAction:
    action_id: str
    timestamp_min: float
    source: str  # "manual" or "orchestrator"
    action_type: str
    target: str
    parameters: Dict[str, float]
    risk_level: str  # "low" | "medium" | "high"
    approved_by: Optional[str]
    result: str  # "success" | "rolled_back" | "failed"
    violated_guardrail: Optional[str]
    marked_incorrect: bool


@dataclass
class IncidentMetrics:
    incident: Incident
    detection_timestamp_min: float
    resolution_timestamp_min: float
    mttr_minutes: float
    time_to_first_mitigation_minutes: float
    remediation_actions: List[RemediationAction] = field(default_factory=list)
    had_incorrect_remediation: bool = False
    had_unsafe_change: bool = False
    num_rollbacks: int = 0
    recurrence_within_window: bool = False
    orchestrator_decision_latency_seconds_mean: float = 0.0
    human_approval_latency_minutes_mean: float = 0.0


@dataclass
class RunResult:
    run_id: str
    metrics: Dict[str, float]
    success: bool = True


# -------------------- Incident generation --------------------


class IncidentGenerator:
    """Deterministic incident generator using a simple LCG RNG.

    We avoid the global random module to keep behavior isolated and
    easily reproducible across runs.
    """

    def __init__(self, seed: int) -> None:
        self.state = seed % 2 ** 31

    def _rand(self) -> float:
        # Simple linear congruential generator
        self.state = (1103515245 * self.state + 12345) % 2 ** 31
        return self.state / float(2 ** 31)

    def choice_weighted(self, items: List[Tuple[str, float]]) -> str:
        total = sum(w for _, w in items)
        r = self._rand() * total
        acc = 0.0
        for value, weight in items:
            acc += weight
            if r <= acc:
                return value
        return items[-1][0]

    def generate_incidents(self, duration_min: int, avg_per_hour: float) -> List[Incident]:
        # Poisson-like inter-arrival using exponential distribution approximation
        incidents: List[Incident] = []
        current_time = 0.0
        lam = avg_per_hour / 60.0  # per-minute rate

        # Incident type distribution and canonical remediations
        types = [
            ("prompt_regression", 0.25),
            ("routing_misconfiguration", 0.20),
            ("rag_retrieval_degradation", 0.20),
            ("tool_failure", 0.20),
            ("latency_cost_regression", 0.15),
        ]
        canonical: Dict[str, str] = {
            "prompt_regression": "rollback_prompt",
            "routing_misconfiguration": "update_routing",
            "rag_retrieval_degradation": "rollback_embedding",
            "tool_failure": "disable_tool",
            "latency_cost_regression": "rollback_model",
        }

        counter = 0
        while current_time < duration_min:
            u = max(self._rand(), 1e-8)
            # Exponential inter-arrival in minutes
            step = -math.log(u) / max(lam, 1e-8)
            current_time += step
            if current_time >= duration_min:
                break
            itype = self.choice_weighted(types)
            sev = self._sample_severity(itype)
            incident_id = f"inc_{counter}"
            incidents.append(
                Incident(
                    incident_id=incident_id,
                    incident_type=itype,
                    severity=sev,
                    detected_at_min=current_time,
                    canonical_remediation=canonical[itype],
                )
            )
            counter += 1
        return incidents

    def _sample_severity(self, incident_type: str) -> str:
        # Simple heuristic mapping with randomness
        r = self._rand()
        if incident_type in {"prompt_regression", "rag_retrieval_degradation"}:
            if r < 0.2:
                return "low"
            elif r < 0.8:
                return "medium"
            return "high"
        if incident_type in {"routing_misconfiguration", "latency_cost_regression"}:
            if r < 0.1:
                return "low"
            elif r < 0.7:
                return "medium"
            return "high"
        # tool_failure
        if r < 0.4:
            return "low"
        elif r < 0.9:
            return "medium"
        return "high"


# -------------------- RCA and action mapping --------------------


class RCAEngine:
    def __init__(self, rng: IncidentGenerator) -> None:
        self.rng = rng

    def make_rca(self, incident: Incident) -> RCAOutput:
        # Confidence varies by type and a little randomness
        base_conf = {
            "prompt_regression": 0.9,
            "routing_misconfiguration": 0.9,
            "rag_retrieval_degradation": 0.85,
            "tool_failure": 0.8,
            "latency_cost_regression": 0.85,
        }[incident.incident_type]
        noise = (self.rng._rand() - 0.5) * 0.1
        confidence = max(0.5, min(0.99, base_conf + noise))
        suspected = [incident.incident_type]
        recommended = [incident.canonical_remediation]
        return RCAOutput(
            incident_id=incident.incident_id,
            detected_at_min=incident.detected_at_min,
            incident_type=incident.incident_type,
            severity=incident.severity,
            suspected_root_causes=suspected,
            recommended_actions=recommended,
            confidence_score=confidence,
        )


class ActionMapper:
    """Map RCA recommended_actions to concrete action types and targets."""

    def __init__(self) -> None:
        # In a real system this would be config-driven
        self._map: Dict[str, Tuple[str, str]] = {
            "rollback_prompt": ("rollback_prompt", "prompt_template_v_prev"),
            "update_routing": ("update_routing", "router_model_A"),
            "rollback_embedding": ("rollback_embedding", "embedding_index_prev"),
            "disable_tool": ("toggle_feature_flag", "tool_X_enabled"),
            "rollback_model": ("rollback_model", "model_version_prev"),
        }

    def map(self, rca: RCAOutput) -> Tuple[str, str]:
        # we assume a single canonical action for now
        recommended = rca.recommended_actions[0]
        action_type, target = self._map[recommended]
        return action_type, target


# -------------------- Baseline: ManualResponder --------------------


class ManualResponder:
    """Simulated manual remediation following runbooks.

    Behavior:
    - For each incident, after a decision latency, attempt the canonical
      remediation as a single action.
    - Execution latency is added after decision latency.
    - No explicit guardrails.
    """

    def __init__(self, rng: IncidentGenerator) -> None:
        self.rng = rng

    def simulate_incident(self, incident: Incident, rca: RCAOutput) -> IncidentMetrics:
        # Decision latency: 1.5 to 4.0 minutes depending on severity
        sev_factor = {"low": 1.2, "medium": 1.0, "high": 0.8}[incident.severity]
        base_decision = 2.5 * sev_factor
        jitter = (self.rng._rand() - 0.5) * 1.0
        decision_latency = max(0.5, base_decision + jitter)

        # Execution latency: 0.5 to 1.5 minutes
        exec_latency = 0.5 + self.rng._rand()

        first_action_time = incident.detected_at_min + decision_latency
        resolution_time = first_action_time + exec_latency

        mapper = ActionMapper()
        action_type, target = mapper.map(rca)

        # In baseline we assume they always pick the canonical remediation
        canonical_type = incident.canonical_remediation
        mapped_canonical, _ = ActionMapper()._map[canonical_type]
        marked_incorrect = action_type != mapped_canonical

        action = RemediationAction(
            action_id=f"act_{incident.incident_id}_0",
            timestamp_min=first_action_time,
            source="manual",
            action_type=action_type,
            target=target,
            parameters={},
            risk_level="medium",  # rough default
            approved_by=None,
            result="success",
            violated_guardrail=None,
            marked_incorrect=marked_incorrect,
        )

        mttr = resolution_time - incident.detected_at_min
        ttfm = first_action_time - incident.detected_at_min

        metrics = IncidentMetrics(
            incident=incident,
            detection_timestamp_min=incident.detected_at_min,
            resolution_timestamp_min=resolution_time,
            mttr_minutes=mttr,
            time_to_first_mitigation_minutes=ttfm,
            remediation_actions=[action],
        )
        metrics.had_incorrect_remediation = marked_incorrect
        metrics.had_unsafe_change = False
        metrics.num_rollbacks = 0
        metrics.recurrence_within_window = False
        metrics.orchestrator_decision_latency_seconds_mean = 0.0
        metrics.human_approval_latency_minutes_mean = 0.0
        return metrics


# -------------------- Treatment: RemediationOrchestrator --------------------


class RemediationOrchestrator:
    """Guarded automated remediation orchestrator.

    - Consumes RCA outputs.
    - Uses RiskPolicy to decide when/how to apply actions.
    - Models human approval latency where required.
    - Tracks simple guardrail violations via max_concurrent_automated_actions.
    - Can schedule rollbacks for incorrect actions.
    """

    def __init__(self, rng: IncidentGenerator, policy: RiskPolicy) -> None:
        self.rng = rng
        self.policy = policy

    def simulate_incident(self, incident: Incident, rca: RCAOutput) -> IncidentMetrics:
        mapper = ActionMapper()
        action_type, target = mapper.map(rca)

        incident_type = incident.incident_type
        risk = self.policy.risk_by_incident_type.get(incident_type, "medium")

        auto_apply = self.policy.auto_apply.get(risk, False)
        requires_approval = self.policy.requires_approval.get(risk, True)

        # Decision latency: orchestrator is fast (seconds), modeled as <= 0.1 min
        decision_latency_min = 0.02 + self.rng._rand() * 0.05

        approval_latency_min = 0.0
        if auto_apply and requires_approval:
            # synthetic human approval: 0.5 to 2 minutes
            approval_latency_min = 0.5 + self.rng._rand() * 1.5

        # Execution latency: 0.2 to 0.8 minutes
        exec_latency_min = 0.2 + self.rng._rand() * 0.6

        first_action_time = (
            incident.detected_at_min
            + decision_latency_min
            + approval_latency_min
        )

        # Check guardrail: concurrent automated actions
        concurrent_before = 0  # simplified for single-incident view
        violated_guardrail = None
        if auto_apply and concurrent_before + 1 > self.policy.max_concurrent_automated_actions:
            violated_guardrail = "max_concurrent_automated_actions"

        # Determine correctness: compare to canonical
        canonical_type = incident.canonical_remediation
        mapped_canonical, _ = ActionMapper()._map[canonical_type]
        marked_incorrect = action_type != mapped_canonical

        result = "success"
        num_rollbacks = 0

        # If incorrect and auto-applied, we schedule a rollback after some delay
        if auto_apply and marked_incorrect:
            result = "rolled_back"
            num_rollbacks = 1

        action = RemediationAction(
            action_id=f"act_{incident.incident_id}_0",
            timestamp_min=first_action_time,
            source="orchestrator",
            action_type=action_type,
            target=target,
            parameters={},
            risk_level=risk,
            approved_by=("user_approval" if requires_approval and auto_apply else None),
            result=result,
            violated_guardrail=violated_guardrail,
            marked_incorrect=marked_incorrect,
        )

        # Resolution time depends on whether the canonical remediation was applied
        if auto_apply and not marked_incorrect:
            # Fast resolution: just exec latency
            resolution_time = first_action_time + exec_latency_min
        elif auto_apply and marked_incorrect:
            # rollback, then assume canonical fix applied after manual follow-up
            rollback_delay = 0.5 + self.rng._rand() * 1.0
            manual_fix_delay = 1.0 + self.rng._rand() * 1.5
            resolution_time = (
                first_action_time
                + exec_latency_min
                + rollback_delay
                + manual_fix_delay
            )
        else:
            # Not auto-applied: behaves somewhat like baseline manual workflow
            manual_decision = 2.0 + self.rng._rand() * 1.5
            manual_exec = 0.8 + self.rng._rand() * 0.7
            resolution_time = incident.detected_at_min + manual_decision + manual_exec

        mttr = resolution_time - incident.detected_at_min
        ttfm = first_action_time - incident.detected_at_min if auto_apply else (
            resolution_time - incident.detected_at_min
        )

        metrics = IncidentMetrics(
            incident=incident,
            detection_timestamp_min=incident.detected_at_min,
            resolution_timestamp_min=resolution_time,
            mttr_minutes=mttr,
            time_to_first_mitigation_minutes=ttfm,
            remediation_actions=[action],
        )

        metrics.had_incorrect_remediation = marked_incorrect
        metrics.had_unsafe_change = violated_guardrail is not None
        metrics.num_rollbacks = num_rollbacks
        metrics.recurrence_within_window = False
        metrics.orchestrator_decision_latency_seconds_mean = decision_latency_min * 60.0
        metrics.human_approval_latency_minutes_mean = approval_latency_min
        return metrics


# -------------------- Aggregation helpers --------------------


def aggregate_run_metrics(incidents: List[IncidentMetrics]) -> Dict[str, float]:
    """Compute run-level aggregate metrics required for evidence.

    We focus on key measures and ensure they are all numeric.
    """

    def safe_mean(values: List[float]) -> float:
        return float(statistics.mean(values)) if values else 0.0

    def safe_median(values: List[float]) -> float:
        return float(statistics.median(values)) if values else 0.0

    mttrs = [m.mttr_minutes for m in incidents]
    ttfm = [m.time_to_first_mitigation_minutes for m in incidents]
    num_remediations = [len(m.remediation_actions) for m in incidents]
    incorrect_flags = [1.0 if m.had_incorrect_remediation else 0.0 for m in incidents]
    unsafe_flags = [1.0 if m.had_unsafe_change else 0.0 for m in incidents]
    rollback_counts = [float(m.num_rollbacks) for m in incidents]
    recurrence_flags = [1.0 if m.recurrence_within_window else 0.0 for m in incidents]
    approval_latencies = [m.human_approval_latency_minutes_mean for m in incidents]
    decision_latencies_sec = [m.orchestrator_decision_latency_seconds_mean for m in incidents]

    n = float(len(incidents)) if incidents else 1.0
    metrics: Dict[str, float] = {
        "mttr_minutes_mean": safe_mean(mttrs),
        "mttr_minutes_median": safe_median(mttrs),
        "time_to_first_mitigation_minutes_mean": safe_mean(ttfm),
        "num_remediations_per_incident_mean": safe_mean(num_remediations),
        "incorrect_remediation_rate": sum(incorrect_flags) / n,
        "unsafe_change_rate": sum(unsafe_flags) / n,
        "rollback_rate": (sum(1.0 for c in rollback_counts if c > 0.0) / n),
        "incident_recurrence_rate": sum(recurrence_flags) / n,
        "human_approval_latency_minutes_mean": safe_mean(approval_latencies),
        "orchestrator_decision_latency_seconds_mean": safe_mean(decision_latencies_sec),
    }
    return metrics


# -------------------- High-level experiment driver --------------------


def run_baseline(workload_id: str, seed: int) -> RunResult:
    rng = IncidentGenerator(seed)
    generator = IncidentGenerator(seed)
    incidents = generator.generate_incidents(duration_min=120, avg_per_hour=12.0)
    rca_engine = RCAEngine(rng)
    responder = ManualResponder(rng)

    metrics_list: List[IncidentMetrics] = []
    for inc in incidents:
        rca = rca_engine.make_rca(inc)
        metrics = responder.simulate_incident(inc, rca)
        metrics_list.append(metrics)

    aggregated = aggregate_run_metrics(metrics_list)
    run_id = f"{workload_id}_seed_{seed}_baseline"
    return RunResult(run_id=run_id, metrics=aggregated, success=True)


def run_treatment(workload_id: str, seed: int) -> RunResult:
    rng = IncidentGenerator(seed + 1)  # small offset to avoid identical RNG stream
    generator = IncidentGenerator(seed)
    incidents = generator.generate_incidents(duration_min=120, avg_per_hour=12.0)
    rca_engine = RCAEngine(rng)
    orchestrator = RemediationOrchestrator(rng, treatment_risk_policy())

    metrics_list: List[IncidentMetrics] = []
    for inc in incidents:
        rca = rca_engine.make_rca(inc)
        metrics = orchestrator.simulate_incident(inc, rca)
        metrics_list.append(metrics)

    aggregated = aggregate_run_metrics(metrics_list)
    run_id = f"{workload_id}_seed_{seed}_treatment"
    return RunResult(run_id=run_id, metrics=aggregated, success=True)


def run_experiment_pair(workload_id: str, seed: int) -> Tuple[Dict[str, object], Dict[str, object]]:
    baseline_res = run_baseline(workload_id, seed)
    treatment_res = run_treatment(workload_id, seed)

    baseline_dict = {
        "run_id": baseline_res.run_id,
        "metrics": baseline_res.metrics,
        "success": baseline_res.success,
    }
    treatment_dict = {
        "run_id": treatment_res.run_id,
        "metrics": treatment_res.metrics,
        "success": treatment_res.success,
    }
    return baseline_dict, treatment_dict
