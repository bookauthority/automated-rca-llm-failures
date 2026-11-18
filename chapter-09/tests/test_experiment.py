import json
import os
import tempfile
import unittest


class TestExperimentEvidenceSchema(unittest.TestCase):
    def setUp(self) -> None:
        # Use a temporary directory as BOOKMAS_EVIDENCE_DIR.
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.evidence_dir = self.tmpdir.name

    def _run_experiment(self) -> str:
        # Set env var so run.py writes into our temp directory.
        os.environ["BOOKMAS_EVIDENCE_DIR"] = self.evidence_dir

        # Import run.py as a module and invoke main().
        import run as experiment_run  # type: ignore

        experiment_run.main()

        results_path = os.path.join(self.evidence_dir, "results.json")
        self.assertTrue(os.path.exists(results_path), "results.json not created")
        return results_path

    def test_evidence_schema_and_metrics(self) -> None:
        path = self._run_experiment()

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Top-level keys.
        self.assertIsInstance(data, dict)
        self.assertEqual(data.get("chapter"), 9)
        self.assertEqual(
            data.get("experiment_id"), "chap9-prompt-policy-hallucination-rca-v1"
        )

        env = data.get("environment")
        self.assertIsInstance(env, dict)
        self.assertIn("os", env)
        self.assertIn("python", env)

        runs = data.get("runs")
        self.assertIsInstance(runs, list)
        self.assertGreaterEqual(len(runs), 6)  # 3 workloads * 2 variants

        seen = {}
        for run in runs:
            self.assertIsInstance(run, dict)
            variant = run.get("variant")
            workload_id = run.get("workload_id")
            run_id = run.get("run_id")
            success = run.get("success")
            metrics = run.get("metrics")

            self.assertIn(variant, {"baseline", "treatment"})
            self.assertIsInstance(workload_id, str)
            self.assertIsInstance(run_id, str)
            self.assertIsInstance(success, bool)
            self.assertIsInstance(metrics, dict)

            # Each metric value must be a number.
            for k, v in metrics.items():
                self.assertIsInstance(
                    v,
                    (int, float),
                    msg=f"Metric {k} must be numeric, got {type(v)}",
                )

            key = (workload_id, variant)
            seen.setdefault(workload_id, set()).add(variant)

        # Ensure at least one baseline and one treatment run per workload.
        for workload_id, variants in seen.items():
            self.assertIn("baseline", variants)
            self.assertIn("treatment", variants)

        # Check that num_requests is positive for all runs.
        for run in runs:
            metrics = run["metrics"]
            self.assertIn("num_requests", metrics)
            self.assertGreater(metrics["num_requests"], 0.0)


if __name__ == "__main__":
    unittest.main()
