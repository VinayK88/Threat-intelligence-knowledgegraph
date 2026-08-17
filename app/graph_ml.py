from __future__ import annotations

from dataclasses import asdict, dataclass
import random

import networkx as nx
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .graph import ThreatGraph

MODEL_NAME = "LogisticGraphLinkPredictor"
MODEL_VERSION = "cti-link-predictor-v1"
RANDOM_STATE = 31

FEATURE_NAMES = (
    "source_out_degree",
    "target_in_degree",
    "common_neighbors",
    "jaccard_neighbors",
    "two_hop_paths",
    "reverse_edge",
    "same_entity_type",
    "type_pair_prior",
)


@dataclass(frozen=True)
class LinkCandidate:
    source: str
    target: str
    source_type: str
    target_type: str
    probability: float
    evidence: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def _simple_graph(graph: ThreatGraph) -> nx.DiGraph:
    dg = nx.DiGraph()
    for node, data in graph.g.nodes(data=True):
        dg.add_node(node, **data)
    for source, target in graph.g.edges():
        dg.add_edge(source, target)
    return dg


def _type_pair_prior(g: nx.DiGraph, source: str, target: str) -> float:
    source_type = str(g.nodes[source].get("type", "unknown"))
    target_type = str(g.nodes[target].get("type", "unknown"))
    possible = 0
    observed = 0
    for left in g.nodes:
        if str(g.nodes[left].get("type", "unknown")) != source_type:
            continue
        for right in g.nodes:
            if left == right or str(g.nodes[right].get("type", "unknown")) != target_type:
                continue
            possible += 1
            if g.has_edge(left, right):
                observed += 1
    # Smoothed prior prevents tiny synthetic type groups from becoming certainty.
    return (observed + 1.0) / (possible + 3.0)


def feature_vector(g: nx.DiGraph, source: str, target: str) -> np.ndarray:
    source_out = set(g.successors(source)) - {target}
    target_in = set(g.predecessors(target)) - {source}
    source_neighbors = (set(g.predecessors(source)) | set(g.successors(source))) - {target}
    target_neighbors = (set(g.predecessors(target)) | set(g.successors(target))) - {source}
    union = source_neighbors | target_neighbors
    common = source_neighbors & target_neighbors
    two_hop = sum(g.has_edge(mid, target) for mid in source_out if mid != target)
    source_type = str(g.nodes[source].get("type", "unknown"))
    target_type = str(g.nodes[target].get("type", "unknown"))
    return np.asarray(
        [
            float(len(source_out)),
            float(len(target_in)),
            float(len(common)),
            float(len(common) / len(union)) if union else 0.0,
            float(two_hop),
            float(g.has_edge(target, source)),
            float(source_type == target_type),
            float(_type_pair_prior(g, source, target)),
        ],
        dtype=float,
    )


def _positive_pairs(g: nx.DiGraph) -> list[tuple[str, str]]:
    return sorted((str(source), str(target)) for source, target in g.edges() if source != target)


def _negative_pairs(g: nx.DiGraph, count: int, seed: int = RANDOM_STATE) -> list[tuple[str, str]]:
    candidates = [
        (str(source), str(target))
        for source in g.nodes
        for target in g.nodes
        if source != target and not g.has_edge(source, target)
    ]
    rng = random.Random(seed)
    rng.shuffle(candidates)
    return candidates[:count]


def train_link_predictor(graph: ThreatGraph):
    full = _simple_graph(graph)
    positives = _positive_pairs(full)
    negatives = _negative_pairs(full, len(positives))
    pairs = positives + negatives
    labels = np.asarray([1] * len(positives) + [0] * len(negatives), dtype=int)
    indices = np.arange(len(pairs))
    train_idx, test_idx = train_test_split(
        indices,
        test_size=0.30,
        stratify=labels,
        random_state=RANDOM_STATE,
    )

    # Remove held-out positive relationships so evaluation mimics a missing-link task.
    observed = full.copy()
    for index in test_idx:
        if labels[index] == 1:
            source, target = pairs[int(index)]
            if observed.has_edge(source, target):
                observed.remove_edge(source, target)

    x_train = np.vstack([feature_vector(observed, *pairs[int(i)]) for i in train_idx])
    y_train = labels[train_idx]
    x_test = np.vstack([feature_vector(observed, *pairs[int(i)]) for i in test_idx])
    y_test = labels[test_idx]

    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(class_weight="balanced", max_iter=1000, random_state=RANDOM_STATE),
    )
    model.fit(x_train, y_train)
    prediction = model.predict(x_test)
    probability = model.predict_proba(x_test)[:, 1]
    metrics = {
        "model": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "positive_edges": len(positives),
        "negative_examples": len(negatives),
        "heldout_pairs": int(len(test_idx)),
        "precision": round(float(precision_score(y_test, prediction, zero_division=0)), 3),
        "recall": round(float(recall_score(y_test, prediction, zero_division=0)), 3),
        "f1": round(float(f1_score(y_test, prediction, zero_division=0)), 3),
        "roc_auc": round(float(roc_auc_score(y_test, probability)), 3),
        "boundary": "Held-out synthetic edges validate ranking mechanics only; predicted links require analyst evidence before acceptance.",
    }

    all_x = np.vstack([feature_vector(full, *pair) for pair in pairs])
    model.fit(all_x, labels)
    return model, metrics, full


def rank_missing_links(graph: ThreatGraph, limit: int = 10) -> list[LinkCandidate]:
    model, _, g = train_link_predictor(graph)
    pairs = _negative_pairs(g, max(1, g.number_of_nodes() * (g.number_of_nodes() - 1)))
    x = np.vstack([feature_vector(g, *pair) for pair in pairs])
    probabilities = model.predict_proba(x)[:, 1]
    rows: list[LinkCandidate] = []
    for (source, target), probability, vector in zip(pairs, probabilities, x):
        evidence = []
        if vector[FEATURE_NAMES.index("common_neighbors")] > 0:
            evidence.append("shared graph neighbors")
        if vector[FEATURE_NAMES.index("two_hop_paths")] > 0:
            evidence.append("directed two-hop path")
        if vector[FEATURE_NAMES.index("type_pair_prior")] >= 0.2:
            evidence.append("entity-type relationship prior")
        rows.append(
            LinkCandidate(
                source=source,
                target=target,
                source_type=str(g.nodes[source].get("type", "unknown")),
                target_type=str(g.nodes[target].get("type", "unknown")),
                probability=round(float(probability), 4),
                evidence=tuple(evidence),
            )
        )
    rows.sort(key=lambda row: (row.probability, row.source, row.target), reverse=True)
    return rows[:limit]


def graph_ml_report(graph: ThreatGraph, limit: int = 10) -> dict[str, object]:
    _, metrics, _ = train_link_predictor(graph)
    return {
        "model": metrics,
        "features": list(FEATURE_NAMES),
        "candidate_links": [row.to_dict() for row in rank_missing_links(graph, limit=limit)],
        "decision_boundary": "Graph ML proposes missing relationships for investigation; it never writes relationships into the knowledge graph automatically.",
    }
