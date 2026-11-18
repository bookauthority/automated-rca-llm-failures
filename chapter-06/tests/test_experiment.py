import json
import os
import math
import unittest

import run as experiment_run
from experiment.config import EXPERIMENT_ID, WORKLOADS


class TestExperimentEvidenceSchema(unittest.TestCase):
    def setUp(self) -> None:
        # Ensure a fresh evidence dir under /evidence
        self.evidence_dir = os.environ.get("BOOKMAS_EVIDENCE_DIR", "/evidence")
        os.makedirs(self.evidence_dir, exist_ok=True)

    def test_run_produces_valid_evidence(self) -> None:
        evidence = experiment_run.run_experiment()

        # Basic top-level fields
        self.assertIsInstance(evidence, dict)
        self.assertEqual(evidence.get("chapter"), 6)
        self.assertEqual(evidence.get("experiment_id"), EXPERIMENT_ID)

        env = evidence.get("environment")
        self.assertIsInstance(env, dict)
        self.assertIn("os", env)
        self.assertIn("python", env)

        runs = evidence.get("runs")
        self.assertIsInstance(runs, list)
        self.assertGreaterEqual(len(runs), 2 * len(WORKLOADS))

        # Ensure at least one baseline and one treatment run per workload
        by_workload = {}
        for r in runs:
            self.assertIn("variant", r)
            self.assertIn("workload_id", r)
            self.assertIn("run_id", r)
            self.assertIn("success", r)
            self.assertIn("metrics", r)

            self.assertIsInstance(r["variant"], str)
            self.assertIsInstance(r["workload_id"], str)
            self.assertIsInstance(r["run_id"], str)
            self.assertIsInstance(r["success"], bool)

            metrics = r["metrics"]
            self.assertIsInstance(metrics, dict)
            # metrics must be purely numeric and finite
            for k, v in metrics.items():
                self.assertIsInstance(v, (int, float), msg=f"Metric {k} not numeric")
                self.assertFalse(math.isnan(v), msg=f"Metric {k} is NaN")
                self.assertFalse(math.isinf(v), msg=f"Metric {k} is infinite")

            wl = r["workload_id"]
            by_workload.setdefault(wl, set()).add(r["variant"])

        for wl_cfg in WORKLOADS:
            wl_id = wl_cfg["id"]
            variants = by_workload.get(wl_id, set())
            self.assertIn("baseline", variants, msg=f"No baseline run for {wl_id}")
            self.assertIn("treatment", variants, msg=f"No treatment run for {wl_id}")

        # Check that evidence was actually written to disk
        out_path = os.path.join(self.evidence_dir, "results.json")
        self.assertTrue(os.path.exists(out_path))
        with open(out_path, "r", encoding="utf-8") as f:
            on_disk = json.load(f)
        self.assertEqual(on_disk.get("experiment_id"), EXPERIMENT_ID)

    def test_metrics_have_reasonable_values(self) -> None:
        evidence = experiment_run.run_experiment()
        runs = evidence["runs"]
        for r in runs:
            m = r["metrics"]
            # event counts must be non-negative
            self.assertGreaterEqual(m.get("events_total", 0), 0.0)
            self.assertGreaterEqual(m.get("llm_events_total", 0), 0.0)
            self.assertGreaterEqual(m.get("incident_events_total", 0), 0.0)
            # latency metrics must be >= 0
            self.assertGreaterEqual(m.get("correlation_latency_mean", 0), 0.0)
            self.assertGreaterEqual(m.get("correlation_latency_p95", 0), 0.0)


if __name__ == "__main__":
    unittest.main()
