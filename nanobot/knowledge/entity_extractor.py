"""Entity extraction from note content.

This module provides pattern-based and LLM-based entity extraction.
"""

import re
from typing import Any
from loguru import logger

from nanobot.knowledge.graph_store import Entity, Relationship, GraphStore


ENTITY_PATTERNS = {
    "project": [
        r"项目[名称称]?[：:]\s*([^\n，。,\.]+)",
        r"(?:项目|Project)[:\s]+([A-Z][a-zA-Z0-9]+)",
        r"(?:#|##)\s*([^\n]+(?:项目|Project))",
    ],
    "person": [
        r"(?:负责人|开发者|作者|创建人)[:\s]+([^\n，。,\.]+)",
        r"@(\w+)",
        r"([A-Z][a-z]+)\s+(?:负责|开发|创建|编写)",
    ],
    "technology": [
        r"使用[了\s]+([A-Za-z]+(?:\+?\+?[A-Za-z0-9]+)+)",
        r"技术栈[：:]\s*([^\n]+)",
        r"(?:基于|使用|采用)[的\s]+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)",
    ],
    "organization": [
        r"(?:公司|团队|组织|部门)[:\s]+([^\n，。,\.]+)",
        r"([^\s]+(?:公司|集团|工作室|团队))",
    ],
    "location": [
        r"(?:位于|在|地址)[：:]\s*([^\n，。,\.]+)",
        r"([^\s]+(?:市|省|区|县|国))",
    ],
}


class EntityExtractor:
    """Extracts entities and relationships from text."""
    
    def __init__(self, graph_store: GraphStore):
        self.graph_store = graph_store
    
    def extract_from_chunk(self, chunk: dict[str, Any]) -> tuple[list[Entity], list[Relationship]]:
        """Extract entities and relationships from a chunk.
        
        Args:
            chunk: Dict with 'content', 'source', 'id' keys
            
        Returns:
            Tuple of (entities, relationships)
        """
        content = chunk.get("content", "")
        source = chunk.get("source", "unknown")
        chunk_id = chunk.get("id", "")
        
        entities = self._extract_entities(content, source)
        
        relationships = self._extract_relationships(content, source, entities)
        
        return entities, relationships
    
    def _extract_entities(self, content: str, source: str) -> list[Entity]:
        entities = []
        
        for entity_type, patterns in ENTITY_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    name = match.group(1).strip()
                    if len(name) >= 2 and len(name) <= 50:
                        context = content[max(0, match.start()-20):match.end()+20]
                        entities.append(Entity(
                            name=name,
                            entity_type=entity_type,
                            source_file=source,
                            context=context
                        ))
        
        return entities
    
    def _extract_relationships(self, content: str, source: str, entities: list[Entity]) -> list[Relationship]:
        relationships = []
        
        entity_names = [e.name for e in entities]
        
        predicates = {
            "使用技术": ["使用", "基于", "采用", "开发"],
            "属于项目": ["属于", "属于", "是"],
            "负责人": ["负责", "管理", "主导"],
            "创建于": ["创建", "建立", "开发"],
            "位于": ["位于", "坐落于"],
            "关联": ["关联", "相关", "涉及"],
        }
        
        for i, entity1 in enumerate(entity_names):
            for j, entity2 in enumerate(entity_names):
                if i == j:
                    continue
                
                e1 = entities[i]
                e2 = entities[j]
                
                for pred_name, pred_variants in predicates.items():
                    for pred in pred_variants:
                        pattern = f"{re.escape(entity1)}.*?{pred}.*?{re.escape(entity2)}"
                        if re.search(pattern, content):
                            relationships.append(Relationship(
                                subject=entity1,
                                predicate=pred_name,
                                obj=entity2,
                                source_file=source,
                                confidence=0.8
                            ))
                            break
        
        return relationships
    
    def extract_from_text(self, text: str, source: str) -> tuple[list[Entity], list[Relationship]]:
        """Extract entities and relationships from plain text.
        
        Args:
            text: Text content
            source: Source identifier
            
        Returns:
            Tuple of (entities, relationships)
        """
        chunk = {"content": text, "source": source, "id": f"text_{hash(text)}"}
        return self.extract_from_chunk(chunk)
    
    def index_entities(self, chunks: list[dict[str, Any]]) -> dict[str, int]:
        """Index all entities from chunks.
        
        Args:
            chunks: List of document chunks
            
        Returns:
            Statistics dict
        """
        total_entities = 0
        total_relationships = 0
        
        for chunk in chunks:
            entities, relationships = self.extract_from_chunk(chunk)
            
            added_entities = self.graph_store.add_entities(entities)
            added_rels = self.graph_store.add_relationships(relationships)
            
            total_entities += added_entities
            total_relationships += added_rels
        
        self.graph_store._save()
        
        return {
            "entities_added": total_entities,
            "relationships_added": total_relationships,
        }
    
    async def extract_batch(self, chunks: list[dict[str, Any]]) -> dict[str, int]:
        """Async version of index_entities for consistency.
        
        Args:
            chunks: List of document chunks
            
        Returns:
            Statistics dict
        """
        return self.index_entities(chunks)
