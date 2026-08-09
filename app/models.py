from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Entity(BaseModel):
    id: str
    name: str
    type: str
    description: str = ""
    aliases: List[str] = Field(default_factory=list)
    attributes: Dict[str, Any] = Field(default_factory=dict)


class Relationship(BaseModel):
    source: str
    target: str
    type: str
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    source_name: str = "synthetic"
    notes: str = ""


class QueryRequest(BaseModel):
    question: str
    top_k: int = Field(default=8, ge=1, le=25)


class EvidencePath(BaseModel):
    nodes: List[str]
    relationships: List[str]
    confidence: float


class QueryResponse(BaseModel):
    question: str
    matched_entities: List[Dict[str, Any]]
    evidence_paths: List[EvidencePath]
    context: str
