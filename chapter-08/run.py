from __future__ import annotations

import json
import os
import platform
from pathlib import Path

from rca_experiment.runner import run_experiment


def main() -> None:
    evidence_dir = os.environ.get("BOOKMAS_EVIDENCE_DIR", "/evidence")
    evidence_path = Path(evidence_dir) / "results.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)

    results = run_experiment()

    environment = {
        "os": platform.system(),
        "python": platform.python_version(),
    }

    evidence = {
        "chapter": 8,
        "experiment_id": "exp-8-ai-driven-rca-hypothesis-generation-v1",
        "environment": environment,
        "runs": results["runs"],
        "notes": results.get("notes", ""),
    }

    with evidence_path.open("w", encoding="utf-8") as f:
        json.dump(evidence, f, indent=2, sort_keys=True)


if __name__ == "__main__":  # pragma: no cover
    main()
