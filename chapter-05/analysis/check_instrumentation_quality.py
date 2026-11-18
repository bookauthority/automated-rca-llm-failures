import json
from pathlib import Path
from typing import Dict, Any


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def run_analysis(
    baseline_metrics_path: Path,
    treatment_metrics_path: Path,
    events_path: Path,
    output_report_path: Path,
) -> Dict[str, Any]:
    baseline = _load_json(baseline_metrics_path)
    treatment = _load_json(treatment_metrics_path)

    # Very lightweight schema-like checks on events
    events = []
    if events_path.exists():
        with events_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    events.append(obj)
                except json.JSONDecodeError:
                    continue

    total_events = len(events)
    schema_ok = 0
    for e in events:
        if (
            isinstance(e, dict)
            and "interaction_id" in e
            and "request" in e
            and "response" in e
        ):
            schema_ok += 1

    schema_compliance_rate = (schema_ok / total_events) if total_events else 0.0

    summary: Dict[str, Any] = {
        "baseline": {
            "gateway_p95_latency_ms": baseline.get("gateway_p95_latency_ms", 0.0),
            "gateway_mean_latency_ms": baseline.get("gateway_mean_latency_ms", 0.0),
            "gateway_error_rate": baseline.get("gateway_error_rate", 0.0),
        },
        "treatment": {
            "gateway_p95_latency_ms": treatment.get("gateway_p95_latency_ms", 0.0),
            "gateway_mean_latency_ms": treatment.get("gateway_mean_latency_ms", 0.0),
            "gateway_error_rate": treatment.get("gateway_error_rate", 0.0),
            "schema_compliance_rate": schema_compliance_rate,
        },
        "notes": "Minimal offline analysis; many advanced metrics from the chapter spec (e.g., trace linkage, OTLP export errors) are not computed here.",
    }

    with output_report_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return summary
