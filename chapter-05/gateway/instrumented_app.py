import time
import uuid
from typing import Dict, Any, List

from gateway.llm_client import MockLLMClient
from gateway.instrumentation.schema import LLMInteractionEvent
from gateway.instrumentation.otel_setup import Span, Tracer, EventWriter
from gateway.instrumentation.redaction import Redactor, load_redaction_config


class InstrumentedGateway:
    """Instrumented gateway emitting structured events and traces.

    This simulates an HTTP + OpenTelemetry setup using in-process calls.
    """

    def __init__(self, events_path: str, redaction_config_path: str) -> None:
        self._client = MockLLMClient()
        self._tracer = Tracer(service_name="instrumented_gateway")
        self._event_writer = EventWriter(events_path)
        config = load_redaction_config(redaction_config_path)
        self._redactor = Redactor(config)

    def handle_chat_completion(self, request: Dict[str, Any]) -> Dict[str, Any]:
        root_span = self._tracer.start_span("http_request")
        try:
            return self._handle_with_spans(request, root_span)
        finally:
            root_span.end()

    def _handle_with_spans(self, request: Dict[str, Any], root_span: Span) -> Dict[str, Any]:
        interaction_id = str(uuid.uuid4())
        llm_span = self._tracer.start_span("llm_call", parent=root_span)
        guardrail_span = None
        start = time.perf_counter()
        error = False
        guardrail_triggered = False
        guardrail_rule = None
        failure_category = None

        # Simple guardrail: banned phrase "banned" in prompt
        prompt_text = request.get("prompt", "")
        if "banned" in prompt_text.lower():
            guardrail_triggered = True
            guardrail_rule = "contains_banned"
            failure_category = "guardrail_violation"

        try:
            completion = self._client.generate_completion(request)
        except Exception:
            error = True
            completion = {"error": "llm_failure"}
            failure_category = failure_category or "llm_error"
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        llm_span.end()

        # Synthetic user feedback & evaluator scores
        feedback_score = 1.0 if not error and not guardrail_triggered else 0.0
        feedback_reason = (
            "ok" if feedback_score == 1.0 else "error_or_guardrail"
        )
        evaluator_quality = 1.0 if not error else 0.2
        evaluator_safety = 0.2 if guardrail_triggered else 1.0

        # Build and write structured interaction event
        event = LLMInteractionEvent.from_raw(
            interaction_id=interaction_id,
            trace_id=root_span.trace_id,
            span_id=llm_span.span_id,
            request=request,
            response=completion,
            latency_ms=elapsed_ms,
            guardrail_triggered=guardrail_triggered,
            guardrail_rule=guardrail_rule,
            feedback_score=feedback_score,
            feedback_reason=feedback_reason,
            evaluator_quality=evaluator_quality,
            evaluator_safety=evaluator_safety,
            failure_category=failure_category,
            redactor=self._redactor,
        )
        self._event_writer.write_event(event.to_dict())

        response = {
            "completion": completion,
            "metrics": {
                "latency_ms": elapsed_ms,
                "error": error,
                "guardrail_triggered": guardrail_triggered,
                "feedback_score": feedback_score,
                "evaluator_quality": evaluator_quality,
                "evaluator_safety": evaluator_safety,
            },
        }
        return response
