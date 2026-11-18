from __future__ import annotations

import json
import os
import unittest
from pathlib import Path


class TestExperimentEvidence(unittest.TestCase):
    def setUp(self) -> None:
        # Ensure evidence directory and run experiment.
        self.evidence_dir = Path(os.environ.get("BOOKMAS_EVIDENCE_DIR", "/evidence"))
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        evidence_file = self.evidence_dir / "results.json"
        if evidence_file.exists():
            evidence_file.unlink()

        # Import and run the main entrypoint.
        from run import main as run_main

        run_main()
        self.evidence_path = evidence_file

    def test_evidence_file_exists_and_valid_json(self) -> None:
        self.assertTrue(self.evidence_path.exists(), "results.json must be created")
        with self.evidence_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIsInstance(data, dict)

    def test_schema_and_runs(self) -> None:
        with self.evidence_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # Top-level keys
        self.assertEqual(data.get("chapter"), 8)
        self.assertEqual(
            data.get("experiment_id"), "exp-8-ai-driven-rca-hypothesis-generation-v1"
        )

        env = data.get("environment")
        self.assertIsInstance(env, dict)
        self.assertIn("os", env)
        self.assertIn("python", env)

        runs = data.get("runs")
        self.assertIsInstance(runs, list)
        self.assertGreaterEqual(len(runs), 8)  # 4 workloads * 2 variants

        # Collect coverage information about workloads and variants.
        workloads_by_variant = {}
        for run in runs:
            self.assertIsInstance(run, dict)
            variant = run.get("variant")
            self.assertIn(variant, ("baseline", "treatment"))
            workload_id = run.get("workload_id")
            self.assertIsInstance(workload_id, str)
            workloads_by_variant.setdefault(variant, set()).add(workload_id)

            # run_id and success
            run_id = run.get("run_id")
            self.assertIsInstance(run_id, str)
            self.assertIsInstance(run.get("success"), bool)

            # metrics must be a dict of numbers.
            metrics = run.get("metrics")
            self.assertIsInstance(metrics, dict)
            self.assertIn("time_to_first_plausible_root_cause", metrics)
            self.assertIn("ai_pipeline_runtime", metrics)
            self.assertIn("wall_clock_runtime", metrics)

            for key, value in metrics.items():
                self.assertIsInstance(
                    value,
                    (int, float),
                    msg=f"Metric {key} must be numeric, got {type(value)}",
                )

        # Each workload must have at least one baseline and one treatment run.
        self.assertIn("baseline", workloads_by_variant)
        self.assertIn("treatment", workloads_by_variant)
        baseline_wls = workloads_by_variant["baseline"]
        treatment_wls = workloads_by_variant["treatment"]
        self.assertGreaterEqual(len(baseline_wls), 4)
        self.assertGreaterEqual(len(treatment_wls), 4)
        self.assertTrue(baseline_wls.issuperset(treatment_wls) or treatment_wls.issuperset(baseline_wls))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
