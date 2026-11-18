from __future__ import annotations

import json
import os
import platform
from pathlib import Path

from experiment.runner import run_all_experiments


CHAPTER_NUMBER = 15
EXPERIMENT_ID = "ch15-end-to-end-rca-case-studies-e2e-llm-incidents-v1"


def main() -> None:
    """Execute all workloads and write the results.json evidence file.

    This function respects the BOOKMAS_EVIDENCE_DIR environment variable,
    defaulting to /evidence in the sandbox.
    """

    evidence_dir_str = os.environ.get("BOOKMAS_EVIDENCE_DIR", "/evidence")
    evidence_dir = Path(evidence_dir_str)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    results_path = evidence_dir / "results.json"

    runs, notes = run_all_experiments()

    environment_info = {
        "os": platform.platform(),
        "python": platform.python_version(),
    }

    payload = {
        "chapter": CHAPTER_NUMBER,
        "experiment_id": EXPERIMENT_ID,
        "environment": environment_info,
        "runs": runs,
        "notes": notes,
    }

    with results_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=False)


if __name__ == "__main__":
    main()
