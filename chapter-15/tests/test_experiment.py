from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import run as experiment_run


class TestExperimentEvidenceSchema(unittest.TestCase):
    def setUp(self) -> None:
        # Create a temporary evidence directory so tests do not depend on
        # global /evidence state.
        self.tmpdir = tempfile.mkdtemp(prefix="evidence_test_")
        os.environ["BOOKMAS_EVIDENCE_DIR"] = self.tmpdir

        # Run the experiment harness to generate results.json in the
        # temporary directory.
        experiment_run.main()

        self.results_path = Path(self.tmpdir) / "results.json"
        self.assertTrue(self.results_path.exists(), "results.json was not created")

        with self.results_path.open("r", encoding="utf-8") as f:
            self.payload = json.load(f)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)
        os.environ.pop("BOOKMAS_EVIDENCE_DIR", None)

    def test_top_level_structure(self) -> None:
        payload = self.payload

        self.assertIn("chapter", payload)
        self.assertIsInstance(payload["chapter"], int)
        self.assertEqual(payload["chapter"], 15)

        self.assertIn("experiment_id", payload)
        self.assertIsInstance(payload["experiment_id"], str)
        self.assertEqual(
            payload["experiment_id"],
            "ch15-end-to-end-rca-case-studies-e2e-llm-incidents-v1",
        )

        self.assertIn("environment", payload)
        self.assertIsInstance(payload["environment"], dict)
        self.assertIn("os", payload["environment"])
        self.assertIn("python", payload["environment"])

        self.assertIn("runs", payload)
        self.assertIsInstance(payload["runs"], list)
        self.assertGreater(len(payload["runs"]), 0)

    def test_runs_have_required_fields_and_numeric_metrics(self) -> None:
        runs = self.payload["runs"]

        required_fields = {"variant", "workload_id", "run_id", "success", "metrics"}

        for run in runs:
            self.assertIsInstance(run, dict)
            self.assertTrue(required_fields.issubset(run.keys()))

            self.assertIn(run["variant"], ("baseline", "treatment"))
            self.assertIsInstance(run["workload_id"], str)
            self.assertIsInstance(run["run_id"], str)
            self.assertIsInstance(run["success"], bool)

            metrics = run["metrics"]
            self.assertIsInstance(metrics, dict)
            # Ensure there is at least one metric
            self.assertGreater(len(metrics), 0)

            for name, value in metrics.items():
                # All metric values must be finite JSON numbers (float or int).
                self.assertIsInstance(
                    value,
                    (int, float),
                    msg=f"Metric {name} is not numeric: {value!r}",
                )

    def test_each_workload_has_baseline_and_treatment(self) -> None:
        runs = self.payload["runs"]

        workloads = {
            "workload-cs1-hallucination-spike-after-data-refresh": {"baseline": 0, "treatment": 0},
            "workload-cs2-latency-and-cost-regressions-routing-misconfig": {"baseline": 0, "treatment": 0},
            "workload-cs3-cascading-failures-broken-tool-integration": {"baseline": 0, "treatment": 0},
        }

        for run in runs:
            workload_id = run["workload_id"]
            variant = run["variant"]
            if workload_id in workloads and variant in ("baseline", "treatment"):
                workloads[workload_id][variant] += 1

        for workload_id, counts in workloads.items():
            with self.subTest(workload=workload_id):
                self.assertGreaterEqual(
                    counts["baseline"],
                    1,
                    msg=f"No baseline runs found for {workload_id}",
                )
                self.assertGreaterEqual(
                    counts["treatment"],
                    1,
                    msg=f"No treatment runs found for {workload_id}",
                )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
