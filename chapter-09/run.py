import json
import os
import platform
import time
from typing import Any, Dict, List

from rca.experiment_runner import run_all_workloads


def main() -> None:
    chapter = 9
    experiment_id = "chap9-prompt-policy-hallucination-rca-v1"

    evidence_dir = os.environ.get("BOOKMAS_EVIDENCE_DIR", "/evidence")
    os.makedirs(evidence_dir, exist_ok=True)
    results_path = os.path.join(evidence_dir, "results.json")

    env_info = {
        "os": platform.platform(),
        "python": platform.python_version(),
    }

    start_all = time.perf_counter()
    runs: List[Dict[str, Any]] = run_all_workloads()
    total_runtime = time.perf_counter() - start_all

    output: Dict[str, Any] = {
        "chapter": chapter,
        "experiment_id": experiment_id,
        "environment": env_info,
        "runs": runs,
        "notes": (
            "Offline deterministic simulation of baseline vs treatment RCA "
            "for prompt, policy, and hallucination failures. "
            f"Total_runtime_seconds={total_runtime:.6f}."
        ),
    }

    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()
