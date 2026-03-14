"""Lightweight GraphRAG implementation for knowledge management.

This module provides:
- Entity extraction from notes
- Relationship (triple) storage
- Graph-based retrieval
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from loguru import logger


@dataclass
class Entity:
    """Represents an extracted entity."""
    name: str
    entity_type: str
    source_file: str
    context: str = ""


@dataclass
class Relationship:
    """Represents a relationship triple (subject, predicate, object)."""
    subject: str
    predicate: str
    obj: str
    source_file: str
    confidence: float = 1.0


@dataclass
class GraphConfig:
    """Configuration for graph extraction."""
    enabled: bool = False
    entity_types: list[str] = field(default_factory=lambda: ["person", "project", "technology", "organization", "location"])
    max_entities_per_chunk: int = 10
    min_confidence: float = 0.7


class GraphStore:
    """Lightweight graph storage using JSON file."""
    
    def __init__(self, persist_path: Path):
        self.persist_path = persist_path
        self.entities: dict[str, Entity] = {}
        self.relationships: list[Relationship] = []
        self._entity_index: dict[str, set[str]] = {}
        self._load()
    
    def _load(self) -> None:
        if self.persist_path.exists():
            try:
                with open(self.persist_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for e in data.get("entities", []):
                        self.entities[e["id"]] = Entity(**e)
                    for r in data.get("relationships", []):
                        self.relationships.append(Relationship(**r))
                    self._rebuild_index()
            except Exception as e:
                logger.warning(f"Failed to load graph data: {e}")
    
    def _save(self) -> None:
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "entities": [
                {"id": k, "name": v.name, "entity_type": v.entity_type, 
                 "source_file": v.source_file, "context": v.context}
                for k, v in self.entities.items()
            ],
            "relationships": [
                {"subject": r.subject, "predicate": r.predicate, "obj": r.obj,
                 "source_file": r.source_file, "confidence": r.confidence}
                for r in self.relationships
            ]
        }
        with open(self.persist_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _rebuild_index(self) -> None:
        self._entity_index.clear()
        for eid, entity in self.entities.items():
            key = entity.name.lower()
            if key not in self._entity_index:
                self._entity_index[key] = set()
            self._entity_index[key].add(eid)
    
    def add_entities(self, entities: list[Entity]) -> int:
        count = 0
        for entity in entities:
            eid = f"{entity.source_file}:{entity.name}"
            if eid not in self.entities:
                self.entities[eid] = entity
                count += 1
        if count > 0:
            self._rebuild_index()
        return count
    
    def add_relationships(self, relationships: list[Relationship]) -> int:
        count = 0
        for rel in relationships:
            if rel.confidence >= 0.7:
                self.relationships.append(rel)
                count += 1
        return count
    
    def find_entity(self, name: str) -> list[Entity]:
        name_lower = name.lower()
        results = []
        for entity in self.entities.values():
            if name_lower in entity.name.lower():
                results.append(entity)
        return results
    
    def find_relationships(self, entity_name: str) -> list[Relationship]:
        results = []
        name_lower = entity_name.lower()
        for rel in self.relationships:
            if name_lower in rel.subject.lower() or name_lower in rel.obj.lower():
                results.append(rel)
        return results
    
    def get_related_entities(self, entity_name: str) -> list[tuple[str, str]]:
        """Get entities related to the given entity with relationship types."""
        rels = self.find_relationships(entity_name)
        related = []
        name_lower = entity_name.lower()
        for rel in rels:
            if name_lower in rel.subject.lower():
                related.append((rel.obj, rel.predicate))
            elif name_lower in rel.obj.lower():
                related.append((rel.subject, rel.predicate))
        return related
    
    def clear(self) -> None:
        self.entities.clear()
        self.relationships.clear()
        self._entity_index.clear()
    
    def get_stats(self) -> dict[str, Any]:
        return {
            "entity_count": len(self.entities),
            "relationship_count": len(self.relationships),
            "entity_types": list(set(e.entity_type for e in self.entities.values())),
        }
