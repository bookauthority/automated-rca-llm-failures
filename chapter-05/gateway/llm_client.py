import hashlib
import random
from typing import Dict, Any


class MockLLMClient:
    """Deterministic mock LLM backend.

    The output is derived from a hash of the prompt and some simple
    rules so that both baseline and treatment see identical behavior
    for the same inputs.
    """

    def __init__(self) -> None:
        # Use a fixed random seed so that any randomness is deterministic
        self._rand = random.Random(12345)

    def generate_completion(self, request: Dict[str, Any]) -> Dict[str, Any]:
        prompt = request.get("prompt", "")
        kind = request.get("type", "short_qa")
        # Derive a pseudo-random but deterministic choice from the prompt
        h = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        bucket = int(h[:8], 16) % 100

        if "timeout" in prompt.lower():
            # Simulate an occasional timeout by raising an exception
            raise RuntimeError("simulated_timeout")

        if kind == "short_qa":
            if "capital of france" in prompt.lower():
                text = "The capital of France is Paris."
            else:
                text = f"Answer for: {prompt[:50]}"
        elif kind == "rag_like":
            text = f"According to internal policy, the PTO policy is generous for: {prompt[:40]}"
        elif kind == "multi_turn_chat":
            text = f"Here is a draft email based on: {prompt[:40]}"
        elif kind == "tool_like":
            text = f"Tool call acknowledged for: {prompt[:40]}"
        else:
            text = f"Generic response for: {prompt[:40]}"

        # Inject occasional low-quality output based on hash bucket
        if bucket < 5:
            text = "gibberish-response"  # to trigger low evaluator/feedback

        return {
            "model": "mock-llm-v1",
            "content": text,
        }
