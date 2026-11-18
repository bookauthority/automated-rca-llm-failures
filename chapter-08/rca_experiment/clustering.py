from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .features import IncidentFeatures, feature_similarity


@dataclass
class ClusterResult:
    """Result of a simple clustering step over incidents.

    Since the experiment is small, we effectively cluster each incident alone
    but still compute nearest-neighbor similarities to mimic embedding search.
    """

    incident_id: str
    cluster_id: str
    nearest_neighbors: List[str]
    similarity_scores: Dict[str, float]


def cluster_incident(
    incident_id: str,
    features: IncidentFeatures,
    historical: Dict[str, IncidentFeatures],
) -> ClusterResult:
    """Compute similarity to historical incidents and assign a trivial cluster.

    - cluster_id is just incident_id for this minimal example.
    - nearest_neighbors are sorted by cosine similarity.
    """

    sims: Dict[str, float] = {}
    for hid, hfeat in historical.items():
        sims[hid] = feature_similarity(features.as_vector(), hfeat.as_vector())

    # Sort descending by similarity.
    ordered = sorted(sims.items(), key=lambda kv: kv[1], reverse=True)
    nearest_ids = [k for k, _ in ordered[:3]]

    return ClusterResult(
        incident_id=incident_id,
        cluster_id=incident_id,
        nearest_neighbors=nearest_ids,
        similarity_scores=sims,
    )
