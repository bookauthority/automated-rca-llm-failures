import json
import math
import os
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List

from gateway.baseline_app import BaselineGateway
from gateway.instrumented_app import InstrumentedGateway


@dataclass
class WorkloadConfig:
    duration_seconds: float = 2.0  # keep very small for sandbox
    concurrency: int = 1
    target_rps: float = 5.0


REQUEST_MIX = [
    {"type": "short_qa", "weight": 0.4, "example": "What is the capital of France?"},
    {
        "type": "rag_like",
        "weight": 0.25,
        "example": "According to the internal policy corpus, what is our PTO policy?",
    },
    {
        "type": "multi_turn_chat",
        "weight": 0.2,
        "example": "Help me draft an email to my manager about project delays.",
    },
    {
        "type": "tool_like",
        "weight": 0.15,
        "example": "Call the calculate_total_cost tool with parameters items=3 price=19.99.",
    },
]


FAILURE_PATTERNS = [
    {
        "name": "guardrail_violation",
        "frequency": 0.05,
        "behavior": "inject banned phrase",
    },
    {
        "name": "llm_timeout",
        "frequency": 0.03,
        "behavior": "inject timeout keyword",
    },
]


def _choose_request_type(rng: random.Random) -> Dict[str, Any]:
    total = sum(item["weight"] for item in REQUEST_MIX)
    r = rng.random() * total
    acc = 0.0
    for item in REQUEST_MIX:
        acc += item["weight"]
        if r <= acc:
            return item
    return REQUEST_MIX[-1]


def _maybe_inject_failure(prompt: str, rng: random.Random) -> (str, str):
    reason = "none"
    r = rng.random()
    if r < FAILURE_PATTERNS[0]["frequency"]:
        reason = "guardrail_violation"
        return prompt + " banned", reason
    if r < FAILURE_PATTERNS[0]["frequency"] + FAILURE_PATTERNS[1]["frequency"]:
        reason = "llm_timeout"
        return prompt + " timeout", reason
    return prompt, reason


def run_workload(
    variant: str,
    output_metrics_path: Path,
    output_events_path: Path,
    seed: int,
) -> Dict[str, Any]:
    rng = random.Random(seed)
    cfg = WorkloadConfig()

    if variant == "baseline":
        gateway = BaselineGateway()
    elif variant == "treatment":
        # Use local instrumentation config
        events_path_str = str(output_events_path)
        redaction_cfg_path = str(Path("config") / "instrumentation.yaml")
        gateway = InstrumentedGateway(events_path_str, redaction_cfg_path)
    else:
        raise ValueError(f"unknown variant: {variant}")

    latencies: List[float] = []
    errors = 0
    total_requests = 0

    start_time = time.perf_counter()
    end_time = start_time + cfg.duration_seconds

    while time.perf_counter() < end_time:
        # For simplicity, ignore true concurrency; just fire requests in a loop
        req_type = _choose_request_type(rng)
        prompt = req_type["example"]
        prompt, failure_reason = _maybe_inject_failure(prompt, rng)
        request = {
            "prompt": prompt,
            "type": req_type["type"],
            "user_id": f"user-{seed}",
            "session_id": f"session-{seed}",
        }
        started = time.perf_counter()
        resp = gateway.handle_chat_completion(request)
        elapsed = (time.perf_counter() - started) * 1000.0
        latencies.append(elapsed)
        m = resp.get("metrics", {})
        if m.get("error"):
            errors += 1
        total_requests += 1

        # Throttle to approximate target RPS
        if cfg.target_rps > 0:
            target_interval = 1.0 / cfg.target_rps
            spent = time.perf_counter() - started
            if spent < target_interval:
                time.sleep(max(0.0, target_interval - spent))

    latencies_sorted = sorted(latencies) if latencies else [0.0]
    p95_idx = max(0, int(math.ceil(0.95 * len(latencies_sorted))) - 1)
    p95 = latencies_sorted[p95_idx]
    mean = sum(latencies_sorted) / len(latencies_sorted) if latencies_sorted else 0.0

    error_rate = errors / total_requests if total_requests else 0.0

    metrics: Dict[str, Any] = {
        "gateway_p95_latency_ms": p95,
        "gateway_mean_latency_ms": mean,
        "gateway_error_rate": error_rate,
        "total_requests": total_requests,
        "start_time": time.time(),
        "end_time": time.time(),
        "success": True,
    }

    # Additional instrumentation-aware metrics for treatment
    if variant == "treatment":
        events_count = 0
        try:
            with output_events_path.open("r", encoding="utf-8") as f:
                for _ in f:
                    events_count += 1
        except FileNotFoundError:
            events_count = 0
        events_per_req = events_count / total_requests if total_requests else 0.0
        metrics["events_per_request_mean"] = events_per_req

    with output_metrics_path.open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    return metrics
