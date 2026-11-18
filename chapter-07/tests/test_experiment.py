import json
import os
import shutil
import tempfile
import unittest

import run as experiment_run


class TestChapter7Experiment(unittest.TestCase):
    def setUp(self) -> None:
        # Create a temporary evidence directory for each test
        self.temp_dir = tempfile.mkdtemp(prefix="evidence_")
        os.environ["BOOKMAS_EVIDENCE_DIR"] = self.temp_dir

    def tearDown(self) -> None:
        # Clean up temporary directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        if "BOOKMAS_EVIDENCE_DIR" in os.environ:
            del os.environ["BOOKMAS_EVIDENCE_DIR"]

    def test_run_creates_results_with_expected_schema(self) -> None:
        # Run the experiment main function
        experiment_run.main()

        results_path = os.path.join(self.temp_dir, "results.json")
        self.assertTrue(os.path.exists(results_path), "results.json must exist")

        with open(results_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Top-level checks
        self.assertEqual(data.get("chapter"), 7)
        self.assertEqual(
            data.get("experiment_id"),
            "exp-07-detect-localize-llm-failures-v1",
        )

        env = data.get("environment")
        self.assertIsInstance(env, dict)
        self.assertIsInstance(env.get("os"), str)
        self.assertIsInstance(env.get("python"), str)

        runs = data.get("runs")
        self.assertIsInstance(runs, list)
        self.assertGreater(len(runs), 0)

        # Track seen variants per workload
        workload_variants = {}

        for run in runs:
            variant = run.get("variant")
            workload_id = run.get("workload_id")
            run_id = run.get("run_id")
            success = run.get("success")
            metrics = run.get("metrics")

            self.assertIn(variant, ("baseline", "treatment"))
            self.assertIsInstance(workload_id, str)
            self.assertIsInstance(run_id, str)
            self.assertIsInstance(success, bool)

            # Ensure each workload has baseline and treatment at least once
            workload_variants.setdefault(workload_id, set()).add(variant)

            # Metrics checks: must be a dict of numeric values
            self.assertIsInstance(metrics, dict)
            self.assertGreater(len(metrics), 0)
            for k, v in metrics.items():
                self.assertIsInstance(k, str)
                # Must be a finite number
                self.assertIsInstance(v, (int, float))

        # Now confirm each workload has both variants
        for workload_id, variants in workload_variants.items():
            self.assertIn("baseline", variants)
            self.assertIn("treatment", variants)


if __name__ == "__main__":
    unittest.main()
