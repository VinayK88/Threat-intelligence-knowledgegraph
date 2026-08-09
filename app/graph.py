from __future__ import annotations

from collections import Counter
from typing import Dict, Iterable, List, Optional

import networkx as nx

from .models import Entity, Relationship, EvidencePath


class ThreatGraph:
    def __init__(self):
        self.g = nx.MultiDiGraph()

    def add_entity(self, entity: Entity) -> None:
        self.g.add_node(entity.id, **entity.model_dump())

    def add_relationship(self, relationship: Relationship) -> None:
        if relationship.source not in self.g or relationship.target not in self.g:
            raise ValueError("relationship references unknown entity")
        self.g.add_edge(
            relationship.source,
            relationship.target,
            key=relationship.type,
            **relationship.model_dump(),
        )

    def get_entity(self, entity_id: str) -> Optional[dict]:
        if entity_id not in self.g:
            return None
        return dict(self.g.nodes[entity_id])

    def neighborhood(self, entity_id: str, limit: int = 25) -> dict:
        entity = self.get_entity(entity_id)
        if not entity:
            return {}

        neighbors = []
        for _, target, key, data in self.g.out_edges(entity_id, keys=True, data=True):
            neighbors.append({
                "direction": "out",
                "relationship": key,
                "entity": dict(self.g.nodes[target]),
                "confidence": data.get("confidence", 0.5),
            })
        for source, _, key, data in self.g.in_edges(entity_id, keys=True, data=True):
            neighbors.append({
                "direction": "in",
                "relationship": key,
                "entity": dict(self.g.nodes[source]),
                "confidence": data.get("confidence", 0.5),
            })

        return {"entity": entity, "neighbors": neighbors[:limit]}

    def stats(self) -> dict:
        types = Counter(data.get("type", "unknown") for _, data in self.g.nodes(data=True))
        return {
            "nodes": self.g.number_of_nodes(),
            "edges": self.g.number_of_edges(),
            "entity_types": dict(sorted(types.items())),
        }

    def simple_paths(self, source: str, target: str, cutoff: int = 5, limit: int = 10) -> List[EvidencePath]:
        if source not in self.g or target not in self.g:
            return []

        # Flatten to DiGraph for path enumeration, preserving strongest relationship per hop.
        dg = nx.DiGraph()
        for u, v, data in self.g.edges(data=True):
            conf = float(data.get("confidence", 0.5))
            current = dg.get_edge_data(u, v)
            if not current or conf > current.get("confidence", 0):
                dg.add_edge(
                    u,
                    v,
                    relationship=data.get("type", "related_to"),
                    confidence=conf,
                )

        results: List[EvidencePath] = []
        try:
            for node_path in nx.all_simple_paths(dg, source, target, cutoff=cutoff):
                rels = []
                confidence = 1.0
                for a, b in zip(node_path, node_path[1:]):
                    edge = dg[a][b]
                    rels.append(edge.get("relationship", "related_to"))
                    confidence *= float(edge.get("confidence", 0.5))
                results.append(
                    EvidencePath(
                        nodes=node_path,
                        relationships=rels,
                        confidence=round(confidence, 4),
                    )
                )
                if len(results) >= limit:
                    break
        except nx.NetworkXNoPath:
            return []

        return sorted(results, key=lambda x: x.confidence, reverse=True)

    def strongest_edges_between(self, node_ids: Iterable[str]) -> List[dict]:
        ids = set(node_ids)
        edges = []
        for u, v, data in self.g.edges(data=True):
            if u in ids and v in ids:
                edges.append({
                    "source": u,
                    "target": v,
                    "relationship": data.get("type", "related_to"),
                    "confidence": float(data.get("confidence", 0.5)),
                })
        return sorted(edges, key=lambda e: e["confidence"], reverse=True)
