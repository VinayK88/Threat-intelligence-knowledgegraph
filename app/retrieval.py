from __future__ import annotations

import math
import re
from collections import Counter
from typing import Dict, Iterable, List, Tuple

from .graph import ThreatGraph
from .models import EvidencePath, QueryResponse


STOP = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with",
    "which", "what", "show", "me", "our", "any", "are", "is", "that", "have",
    "has", "from", "by", "using", "use"
}


def tokenize(text: str) -> List[str]:
    return [
        t for t in re.findall(r"[a-zA-Z0-9._-]+", text.lower())
        if len(t) > 1 and t not in STOP
    ]


def _entity_document(node: dict) -> str:
    aliases = " ".join(node.get("aliases", []))
    attrs = " ".join(f"{k} {v}" for k, v in node.get("attributes", {}).items())
    return " ".join([
        node.get("name", ""),
        node.get("type", ""),
        node.get("description", ""),
        aliases,
        attrs,
    ])


def rank_entities(graph: ThreatGraph, question: str, top_k: int = 8) -> List[dict]:
    q_tokens = tokenize(question)
    if not q_tokens:
        return []

    query_counts = Counter(q_tokens)
    scored = []

    for entity_id, node in graph.g.nodes(data=True):
        doc_tokens = tokenize(_entity_document(node))
        if not doc_tokens:
            continue

        counts = Counter(doc_tokens)
        overlap = sum(min(query_counts[t], counts[t]) for t in query_counts)
        rarity_bonus = sum(1.0 / math.sqrt(max(1, counts[t])) for t in query_counts if t in counts)
        exact_name_bonus = 2.0 if node.get("name", "").lower() in question.lower() else 0.0

        score = overlap + 0.3 * rarity_bonus + exact_name_bonus
        if score > 0:
            result = dict(node)
            result["retrieval_score"] = round(score, 4)
            scored.append(result)

    return sorted(scored, key=lambda x: x["retrieval_score"], reverse=True)[:top_k]


def _expand_candidate_ids(graph: ThreatGraph, seed_ids: Iterable[str], max_nodes: int = 20) -> List[str]:
    ids = []
    seen = set()

    for seed in seed_ids:
        if seed not in seen:
            ids.append(seed)
            seen.add(seed)

        # one-hop expansion
        for _, target in graph.g.out_edges(seed):
            if target not in seen:
                ids.append(target)
                seen.add(target)
                if len(ids) >= max_nodes:
                    return ids
        for source, _ in graph.g.in_edges(seed):
            if source not in seen:
                ids.append(source)
                seen.add(source)
                if len(ids) >= max_nodes:
                    return ids

    return ids


def build_evidence(graph: ThreatGraph, question: str, top_k: int = 8) -> QueryResponse:
    matches = rank_entities(graph, question, top_k=top_k)
    seed_ids = [m["id"] for m in matches]
    expanded = _expand_candidate_ids(graph, seed_ids)

    paths: List[EvidencePath] = []
    # Build useful multi-hop paths among top retrieval seeds and observations.
    observation_ids = [
        node_id for node_id, node in graph.g.nodes(data=True)
        if node.get("type") == "observation"
    ]

    for seed in seed_ids[:5]:
        for obs in observation_ids:
            if seed == obs:
                continue
            for path in graph.simple_paths(seed, obs, cutoff=4, limit=3):
                paths.append(path)

    # Deduplicate path signatures.
    unique = {}
    for path in paths:
        sig = tuple(path.nodes)
        if sig not in unique or path.confidence > unique[sig].confidence:
            unique[sig] = path

    ranked_paths = sorted(unique.values(), key=lambda p: p.confidence, reverse=True)[:10]

    context_lines = []
    for node_id in expanded[:20]:
        node = graph.get_entity(node_id)
        if node:
            context_lines.append(
                f"[{node['type']}] {node['name']}: {node.get('description','')}"
            )

    for edge in graph.strongest_edges_between(expanded)[:20]:
        s = graph.get_entity(edge["source"])
        t = graph.get_entity(edge["target"])
        if s and t:
            context_lines.append(
                f"{s['name']} --{edge['relationship']} "
                f"(confidence={edge['confidence']:.2f})--> {t['name']}"
            )

    return QueryResponse(
        question=question,
        matched_entities=matches,
        evidence_paths=ranked_paths,
        context="\n".join(context_lines),
    )
