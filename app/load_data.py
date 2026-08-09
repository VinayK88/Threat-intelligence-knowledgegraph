from __future__ import annotations

import json
from pathlib import Path

from .graph import ThreatGraph
from .models import Entity, Relationship


def load_graph(path: str = "data/sample_intel.json") -> ThreatGraph:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    graph = ThreatGraph()

    for entity in payload["entities"]:
        graph.add_entity(Entity(**entity))

    for relationship in payload["relationships"]:
        graph.add_relationship(Relationship(**relationship))

    return graph
