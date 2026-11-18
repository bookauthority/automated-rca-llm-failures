import json
import os
import unittest
from pathlib import Path


class TestExperimentEvidence(unittest.TestCase):
    def setUp(self) -> None:
        # Ensure a clean evidence directory under /evidence for the test.
        self.evidence_dir = Path(os.environ.get("BOOKMAS_EVIDENCE_DIR", "/evidence"))
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.results_path = self.evidence_dir / "results.json"
        if self.results_path.exists():
            self.results_path.unlink()

        # Run the main script to generate evidence.
        import run as experiment_run  # type: ignore

        experiment_run.main()

    def test_evidence_file_exists_and_valid_json(self) -> None:
        self.assertTrue(self.results_path.exists(), "results.json should be created")
        with self.results_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIsInstance(data, dict)

    def test_schema_basic_fields(self) -> None:
        with self.results_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # Required top-level fields
        self.assertIn("chapter", data)
        self.assertIn("experiment_id", data)
        self.assertIn("environment", data)
        self.assertIn("runs", data)

        self.assertEqual(data["chapter"], 10)
        self.assertEqual(data["experiment_id"], "exp-model-drift-routing-rca-ch10")

        env = data["environment"]
        self.assertIsInstance(env, dict)
        self.assertIn("os", env)
        self.assertIn("python", env)

    def test_runs_structure_and_metrics(self) -> None:
        with self.results_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        runs = data["runs"]
        self.assertIsInstance(runs, list)
        self.assertGreaterEqual(len(runs), 2)

        # Track presence of baseline and treatment for each workload
        coverage = {}

        for run in runs:
            self.assertIn("variant", run)
            self.assertIn("workload_id", run)
            self.assertIn("run_id", run)
            self.assertIn("success", run)
            self.assertIn("metrics", run)

            variant = run["variant"]
            workload_id = run["workload_id"]
            self.assertIn(variant, ("baseline", "treatment"))
            self.assertIsInstance(workload_id, str)

            # Metrics must be a flat mapping of numeric values
            metrics = run["metrics"]
            self.assertIsInstance(metrics, dict)
            self.assertGreater(len(metrics), 0)
            for key, value in metrics.items():
                self.assertIsInstance(
                    value,
                    (int, float),
                    msg=f"Metric {key} must be numeric, got {type(value)}",
                )

            key = (workload_id, variant)
            coverage[key] = True

        # Ensure at least one baseline and one treatment run per workload
        workloads = {w for (w, _v) in coverage.keys()}
        for w in workloads:
            self.assertIn((w, "baseline"), coverage)
            self.assertIn((w, "treatment"), coverage)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
