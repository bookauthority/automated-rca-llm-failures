import datetime as _dt
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional


@dataclass
class LLMInteractionEvent:
    interaction_id: str
    trace_id: str
    span_id: str
    timestamp: str
    request: Dict[str, Any]
    response: Dict[str, Any]
    routing: Dict[str, Any]
    rca_signals: Dict[str, Any]

    @classmethod
    def from_raw(
        cls,
        interaction_id: str,
        trace_id: str,
        span_id: str,
        request: Dict[str, Any],
        response: Dict[str, Any],
        latency_ms: float,
        guardrail_triggered: bool,
        guardrail_rule: Optional[str],
        feedback_score: float,
        feedback_reason: str,
        evaluator_quality: float,
        evaluator_safety: float,
        failure_category: Optional[str],
        redactor,
    ) -> "LLMInteractionEvent":
        ts = _dt.datetime.utcnow().isoformat() + "Z"

        user_id = request.get("user_id", "")
        session_id = request.get("session_id", "")
        red_req = {
            "user_id_hash": redactor.hash_value(user_id),
            "session_id_hash": redactor.hash_value(session_id),
            "prompt_redacted": redactor.redact_text(request.get("prompt", "")),
            "prompt_tokens": len(request.get("prompt", "").split()),
            "metadata": {
                "type": request.get("type"),
            },
        }

        red_resp = {
            "model": response.get("model", "unknown"),
            "completion_redacted": redactor.redact_text(response.get("content", "")),
            "completion_tokens": len(response.get("content", "").split()),
            "latency_ms": latency_ms,
        }

        routing = {
            "route": request.get("route", "default"),
            "model_variant": response.get("model", "mock-llm-v1"),
        }

        rca_signals = {
            "user_feedback": {
                "score": feedback_score,
                "reason": feedback_reason,
            },
            "guardrail": {
                "triggered": guardrail_triggered,
                "rule_id": guardrail_rule,
            },
            "evaluator_scores": {
                "quality": evaluator_quality,
                "safety": evaluator_safety,
            },
            "failure_category": failure_category,
        }

        return cls(
            interaction_id=interaction_id,
            trace_id=trace_id,
            span_id=span_id,
            timestamp=ts,
            request=red_req,
            response=red_resp,
            routing=routing,
            rca_signals=rca_signals,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
