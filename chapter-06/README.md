# Experiment 06 – Signal Collection and Event Correlation at Scale

This self-contained Python 3.11+ project implements a **baseline batch pipeline** and a **streaming-style treatment pipeline** for LLM RCA signal ingestion and event correlation, with synthetic workloads and minimal but real metrics.

The project is intentionally lightweight and uses only the Python standard library so that it can run in the restricted, offline sandbox environment. It **does not try to hit the real throughput targets** from the chapter spec (50k events/minute, etc.), but it preserves the *structural* differences between baseline and treatment and exposes comparable metrics.

Key ideas implemented:

- A common **RCA event schema** across:
  - LLM interaction events
  - Infrastructure metric events
  - Trace span events
- A **synthetic workload generator** for three workloads:
  - W1 – steady state mixed traffic
  - W2 – bursty traffic with incident spikes
  - W3 – synthetic incident replay (deterministic, file-based)
- **Baseline pipeline**:
  - Writes generator events to JSONL files (as if logs/object storage)
  - Periodically (simulated) performs batch ingestion and offline correlation
- **Treatment pipeline**:
  - Uses an in-process queue to simulate a streaming broker
  - Normalizes events and correlates them in near-real-time with small windows
- **Metrics and evidence**:
  - Each run records at least one real numeric metric (event counts, latency samples) per workload and variant.
  - Evidence is written to `/evidence/results.json` (or `$BOOKMAS_EVIDENCE_DIR/results.json`).

This experiment is **safe and bounded**: workloads are heavily scaled down, time is compressed, and all data is synthetic and deterministic.

## Layout

```
.
├── README.md
├── requirements.txt
├── run.py
├── experiment
│   ├── __init__.py
│   ├── config.py
│   ├── events.py
│   ├── workloads.py
│   ├── baseline_pipeline.py
│   ├── streaming_pipeline.py
│   ├── correlation.py
│   ├── metrics.py
│   └── util.py
└── tests
    ├── __init__.py
    └── test_experiment.py
```

## Running the experiment

From the project root:

```bash
python run.py
```

This will:

1. Run **baseline** and **treatment** for each workload (W1, W2, W3).
2. Collect metrics for each run.
3. Write a consolidated evidence file to:
   - `$BOOKMAS_EVIDENCE_DIR/results.json` if the environment variable is set, otherwise
   - `/evidence/results.json` (creating `/evidence` if needed).

The evidence file follows this exact schema:

```json
{
  "chapter": 6,
  "experiment_id": "exp-06-signal-collection-event-correlation-at-scale-v1",
  "environment": {"os": "...", "python": "..."},
  "runs": [
    {
      "variant": "baseline",
      "workload_id": "W1-steady-state-mixed-traffic",
      "run_id": "baseline_W1_1",
      "success": true,
      "metrics": {
        "events_total": 1234,
        "correlation_latency_mean": 0.0123
      }
    }
  ],
  "notes": "... optional string ..."
}
```

- `metrics` must contain **only numeric values** (no strings, lists, objects, or nulls).
- At least one shared numeric metric is reported for every run.
- Any explanatory text or non-numeric data appears **outside** of `metrics`.

## Workloads

Workloads are simplified versions of the detailed spec, tuned for fast execution:

- **W1-steady-state-mixed-traffic**
  - Fixed small number of synthetic LLM requests per run.
  - 10% incident-tagged traffic.
- **W2-burst-traffic-with-incident-spike**
  - Phased RPS profile with a small burst.
  - Higher fraction of incident traffic during burst phases.
- **W3-synthetic-incident-replay-benchmark**
  - Deterministic replay from an in-memory synthetic dataset (no external files needed in this sandbox).

All randomness is seeded for reproducibility.

## Pipelines

### Baseline

- Simulates **file-based batch ingestion**:
  - Generator produces events and writes them to disk.
  - A simple batch job loads all events at once, normalizes, then correlates.
- Correlation algorithm:
  - Group events by `incident_id` and `request_id`.
  - Compute simple incident contexts and measure latency as:
    - `correlation_time - generator_ts`.

### Treatment (Streaming-style)

- Uses a standard-library `queue.Queue` to simulate a durable broker.
- A producer thread feeds events into the queue.
- A consumer thread processes events one by one:
  - Normalize event
  - Update correlation state with short time windows
- Latency is measured at per-event granularity as soon as an event is attached to a context.

## Metrics

In this sandbox we focus on **metrics we can genuinely measure**:

- `events_total` – total number of events processed in a run.
- `llm_events_total` – number of LLM interaction events.
- `incident_events_total` – number of incident-related events.
- `correlation_latency_mean` – mean event-level correlation latency (seconds).
- `correlation_latency_p95` – simple percentile approximation for correlation latency.

These are produced for both baseline and treatment, for each workload.

We **do not fabricate** any unmeasurable metrics (e.g., CPU utilization for the host OS). They are simply omitted from `metrics`.

## Testing

Run unit tests:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

The tests verify:

- Evidence file exists and is valid JSON.
- Evidence schema is satisfied:
  - `chapter`, `experiment_id`, `environment`, `runs` present.
  - At least one baseline and one treatment run for each workload.
  - `metrics` is a dict of finite numeric values.
- Basic sanity on event counts and latency metrics.

The project uses only the Python standard library; `requirements.txt` is intentionally empty of runtime dependencies.
