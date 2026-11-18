import json
import os
import unittest


class TestExperimentEvidence(unittest.TestCase):
    """Validate the evidence schema and basic invariants.

    These tests assume that run.py has already been executed and that
    /evidence/results.json exists. If it does not, the tests will attempt
    to read from the default path and fail clearly.
    """

    def setUp(self) -> None:
        base_dir = os.environ.get("BOOKMAS_EVIDENCE_DIR", "/evidence")
        self.results_path = os.path.join(base_dir, "results.json")
        self.assertTrue(
            os.path.exists(self.results_path),
            msg=(
                f"Expected evidence file at {self.results_path}. "
                "Run `python run.py` before executing tests."
            ),
        )
        with open(self.results_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

    def test_top_level_schema(self) -> None:
        d = self.data
        self.assertIn("chapter", d)
        self.assertEqual(d["chapter"], 11)
        self.assertIn("experiment_id", d)
        self.assertEqual(d["experiment_id"], "exp-11-data-retrieval-tooling-rca-v1")
        self.assertIn("environment", d)
        self.assertIsInstance(d["environment"], dict)
        self.assertIn("runs", d)
        self.assertIsInstance(d["runs"], list)

    def test_runs_cover_variants_and_workloads(self) -> None:
        runs = self.data["runs"]
        self.assertGreaterEqual(len(runs), 6)  # 3 workloads * 2 variants

        workloads = set()
        variants = set()

        for run in runs:
            self.assertIn("variant", run)
            self.assertIn(run["variant"], ("baseline", "treatment"))
            self.assertIn("workload_id", run)
            workloads.add(run["workload_id"])
            variants.add(run["variant"])

            self.assertIn("run_id", run)
            self.assertIsInstance(run["run_id"], str)
            self.assertIn("success", run)
            self.assertIsInstance(run["success"], bool)

            # Metrics must be present and all values must be numeric.
            self.assertIn("metrics", run)
            metrics = run["metrics"]
            self.assertIsInstance(metrics, dict)
            self.assertGreater(len(metrics), 0)
            for k, v in metrics.items():
                self.assertIsInstance(
                    v,
                    (int, float),
                    msg=f"Metric {k} must be numeric, got {type(v)}",
                )

        expected_workloads = {
            "WL1-normal-mixed-traffic",
            "WL2-broken-ingestion-job",
            "WL3-flaky-tool-endpoint",
        }
        self.assertTrue(expected_workloads.issubset(workloads))
        self.assertIn("baseline", variants)
        self.assertIn("treatment", variants)

    def test_rca_metrics_present_for_treatment(self) -> None:
        # For treatment runs, we expect at least the same core metrics
        # as baseline, and RCA-specific metrics may be present depending
        # on workload.
        runs = self.data["runs"]
        for run in runs:
            metrics = run["metrics"]
            self.assertIn("requests_total", metrics)
            self.assertIn("retrieval_stale_or_missing", metrics)
            self.assertIn("tool_failures", metrics)

            if run["variant"] == "treatment":
                # For WL2 and WL3, at least one RCA detection metric
                # should be present if the incident actually occurred.
                if run["workload_id"] == "WL2-broken-ingestion-job":
                    # Not strictly required to succeed, but if present,
                    # must be numeric and non-negative.
                    key = "rca_detection_latency_units_data_ingestion"
                    if key in metrics:
                        self.assertGreaterEqual(metrics[key], 0.0)
                if run["workload_id"] == "WL3-flaky-tool-endpoint":
                    key = "rca_detection_latency_units_tool_flakiness"
                    if key in metrics:
                        self.assertGreaterEqual(metrics[key], 0.0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
