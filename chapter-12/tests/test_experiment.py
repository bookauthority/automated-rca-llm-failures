import json
import os
import unittest
from pathlib import Path


class TestExperimentEvidence(unittest.TestCase):
    def setUp(self) -> None:
        # Ensure we write to a temporary evidence directory inside the project
        self.evidence_dir = Path("./.test_evidence").resolve()
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        os.environ["BOOKMAS_EVIDENCE_DIR"] = str(self.evidence_dir)

        # Run the experiment
        import run as experiment_run

        experiment_run.main()

        self.results_path = self.evidence_dir / "results.json"

    def tearDown(self) -> None:
        # Clean up evidence directory
        if self.evidence_dir.exists():
            for p in self.evidence_dir.glob("**/*"):
                try:
                    p.unlink()
                except IsADirectoryError:
                    pass
            for p in sorted(self.evidence_dir.glob("**/*"), reverse=True):
                if p.is_dir():
                    try:
                        p.rmdir()
                    except OSError:
                        pass

    def test_results_file_exists_and_schema(self) -> None:
        self.assertTrue(self.results_path.exists(), "results.json should be created")

        with self.results_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # Top-level keys
        self.assertIsInstance(data, dict)
        self.assertIn("chapter", data)
        self.assertIn("experiment_id", data)
        self.assertIn("environment", data)
        self.assertIn("runs", data)

        self.assertEqual(data["chapter"], 12)
        self.assertEqual(data["experiment_id"], "exp-12-automated-remediation-guardrails-mttr")

        # Environment checks
        env = data["environment"]
        self.assertIsInstance(env, dict)
        self.assertIn("os", env)
        self.assertIn("python", env)
        self.assertIsInstance(env["os"], str)
        self.assertIsInstance(env["python"], str)

        runs = data["runs"]
        self.assertIsInstance(runs, list)
        self.assertGreaterEqual(len(runs), 2, "At least one baseline and one treatment run expected")

        variants = {r.get("variant") for r in runs}
        self.assertIn("baseline", variants)
        self.assertIn("treatment", variants)

        # Validate each run
        for run in runs:
            self.assertIn("variant", run)
            self.assertIsInstance(run["variant"], str)
            self.assertIn(run["variant"], ["baseline", "treatment"])

            self.assertIn("workload_id", run)
            self.assertIsInstance(run["workload_id"], str)

            self.assertIn("run_id", run)
            self.assertIsInstance(run["run_id"], str)

            self.assertIn("success", run)
            self.assertIsInstance(run["success"], bool)

            self.assertIn("metrics", run)
            metrics = run["metrics"]
            self.assertIsInstance(metrics, dict)

            # All metric values must be finite numbers
            self.assertGreater(len(metrics), 0, "Metrics must not be empty")
            for name, value in metrics.items():
                self.assertIsInstance(name, str)
                self.assertIsInstance(value, (int, float))
                self.assertFalse(isinstance(value, bool))
                self.assertTrue(
                    value == value and value not in (float("inf"), float("-inf")),
                    f"Metric {name} must be finite",
                )

    def test_shared_workload_id_and_seed_in_run_ids(self) -> None:
        with self.results_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        runs = data["runs"]
        workload_ids = {r["workload_id"] for r in runs}
        self.assertEqual(len(workload_ids), 1, "All runs should share the same workload_id")

        # Check that baseline and treatment use the same seed encoding in run_id
        baseline_ids = [r["run_id"] for r in runs if r["variant"] == "baseline"]
        treatment_ids = [r["run_id"] for r in runs if r["variant"] == "treatment"]

        self.assertGreaterEqual(len(baseline_ids), 1)
        self.assertGreaterEqual(len(treatment_ids), 1)

        # Ensure that at least one pair of baseline/treatment run_ids share the same seed tag
        def seed_tag(run_id: str) -> str:
            # Expected format: workload_seed_<seed>_variant
            parts = run_id.split("_seed_")
            if len(parts) != 2:
                return ""
            tail = parts[1]
            return tail.split("_")[0]

        baseline_seeds = {seed_tag(rid) for rid in baseline_ids}
        treatment_seeds = {seed_tag(rid) for rid in treatment_ids}
        self.assertTrue(baseline_seeds & treatment_seeds, "Baseline and treatment should share at least one seed")


if __name__ == "__main__":
    unittest.main()
