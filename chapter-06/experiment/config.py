EXPERIMENT_ID = "exp-06-signal-collection-event-correlation-at-scale-v1"

# Workload configurations are light-weight; they encode only what the generator needs

WORKLOADS = [
    {
        "id": "W1-steady-state-mixed-traffic",
        "name": "W1-steady-state-mixed-traffic",
        "type": "steady",
        "total_requests": 200,
        "incident_fraction": 0.1,
        "seed": 42,
    },
    {
        "id": "W2-burst-traffic-with-incident-spike",
        "name": "W2-burst-traffic-with-incident-spike",
        "type": "burst",
        "phases": [
            {"name": "warmup", "requests": 60, "incident_fraction": 0.05},
            {"name": "burst-1", "requests": 120, "incident_fraction": 0.3},
            {"name": "burst-2", "requests": 160, "incident_fraction": 0.4},
            {"name": "cooldown", "requests": 80, "incident_fraction": 0.1},
        ],
        "seed": 123,
    },
    {
        "id": "W3-synthetic-incident-replay-benchmark",
        "name": "W3-synthetic-incident-replay-benchmark",
        "type": "replay",
        "seed": 7,
        # number of synthetic incidents and related events per incident
        "incidents": 5,
        "requests_per_incident": 10,
    },
]
