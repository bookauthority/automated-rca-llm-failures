import time
from typing import Dict, Any

from gateway.llm_client import MockLLMClient


class BaselineGateway:
    """Minimal LLM gateway without RCA-oriented instrumentation.

    It provides a single `handle_chat_completion` method that mimics a
    `/v1/chat/completions` HTTP endpoint but is fully in-process.

    It logs only coarse metrics via returned values; the caller is
    responsible for aggregating them.
    """

    def __init__(self) -> None:
        self._client = MockLLMClient()

    def handle_chat_completion(self, request: Dict[str, Any]) -> Dict[str, Any]:
        start = time.perf_counter()
        error = False
        try:
            completion = self._client.generate_completion(request)
        except Exception:
            error = True
            completion = {"error": "llm_failure"}
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        response = {
            "completion": completion,
            "metrics": {
                "latency_ms": elapsed_ms,
                "error": error,
            },
        }
        return response
