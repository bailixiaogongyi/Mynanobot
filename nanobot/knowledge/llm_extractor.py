"""LLM-based entity extractor for GraphRAG.

This module provides LLM-based entity and relationship extraction
with fallback to pattern-based extraction.
"""

import json
import re
from typing import Any
from loguru import logger

from nanobot.knowledge.graph_store import Entity, Relationship, GraphStore


LLM_EXTRACT_PROMPT = """你是一个知识图谱抽取专家。从以下文本中提取实体和关系。

## 实体类型
- person: 人名（开发者、负责人、作者等）
- project: 项目名（产品、系统、平台等）
- technology: 技术栈（编程语言、框架、工具等）
- organization: 组织（公司、团队、部门等）
- location: 地点（城市、国家、地址等）

## 关系类型
- 使用技术: 项目/产品使用的技术
- 负责: 某人负责某项目
- 属于: 某实体属于另一实体
- 创建于: 项目/产品的创建时间或地点
- 关联: 相关但不属于以上类型的关系

## 输出格式（JSON）
{{"entities": [{{"name": "实体名", "type": "实体类型", "context": "上下文"}}], "relationships": [{{"subject": "主体", "predicate": "关系", "object": "客体", "confidence": 0.9}}]}}

## 文本内容
{text}

## 输出（仅JSON，不要其他内容）:
"""


class LLMEntityExtractor:
    """LLM-based entity extractor with pattern fallback."""
    
    def __init__(
        self,
        graph_store: GraphStore,
        provider: Any = None,
        use_llm: bool = True,
        batch_size: int = 10,
        min_confidence: float = 0.7,
        fallback_on_error: bool = True,
    ):
        self.graph_store = graph_store
        self.provider = provider
        self.use_llm = use_llm
        self.batch_size = batch_size
        self.min_confidence = min_confidence
        self.fallback_on_error = fallback_on_error
        self._pattern_extractor = None
    
    def _get_pattern_extractor(self):
        """Lazy load pattern-based extractor for fallback."""
        if self._pattern_extractor is None:
            from nanobot.knowledge.entity_extractor import EntityExtractor
            self._pattern_extractor = EntityExtractor(self.graph_store)
        return self._pattern_extractor
    
    async def extract_from_chunk(self, chunk: dict[str, Any]) -> tuple[list[Entity], list[Relationship]]:
        """Extract entities and relationships from a chunk using LLM.
        
        Args:
            chunk: Dict with 'content', 'source', 'id' keys
            
        Returns:
            Tuple of (entities, relationships)
        """
        content = chunk.get("content", "")
        source = chunk.get("source", "unknown")
        
        if not content or len(content.strip()) < 10:
            return [], []
        
        if self.use_llm and self.provider:
            try:
                return await self._extract_with_llm(content, source)
            except Exception as e:
                logger.warning(f"LLM extraction failed: {e}, falling back to pattern")
                if self.fallback_on_error:
                    return self._extract_with_pattern(chunk)
                return [], []
        else:
            return self._extract_with_pattern(chunk)
    
    async def _extract_with_llm(self, text: str, source: str) -> tuple[list[Entity], list[Relationship]]:
        """Extract entities using LLM."""
        prompt = LLM_EXTRACT_PROMPT.format(text=text[:3000])
        
        messages = [
            {"role": "system", "content": "你是一个专业的知识图谱抽取专家，擅长从文本中提取实体和关系。请严格按照JSON格式输出。"},
            {"role": "user", "content": prompt},
        ]
        
        response = await self.provider.chat(
            messages=messages,
            model=None,
            temperature=0.1,
            max_tokens=2000,
        )
        
        if not response.content:
            return [], []
        
        entities = []
        relationships = []
        
        try:
            json_str = response.content.strip()
            if json_str.startswith("```"):
                json_str = re.sub(r"^```\w*\n?", "", json_str)
                json_str = re.sub(r"\n?```$", "", json_str)
            
            data = json.loads(json_str)
            
            for e in data.get("entities", []):
                name = e.get("name", "").strip()
                if name and len(name) >= 2:
                    entities.append(Entity(
                        name=name,
                        entity_type=e.get("type", "unknown"),
                        source_file=source,
                        context=e.get("context", "")[:200],
                    ))
            
            for r in data.get("relationships", []):
                subject = r.get("subject", "").strip()
                predicate = r.get("predicate", "").strip()
                obj = r.get("object", "").strip()
                confidence = r.get("confidence", 0.8)
                
                if subject and predicate and obj:
                    relationships.append(Relationship(
                        subject=subject,
                        predicate=predicate,
                        obj=obj,
                        source_file=source,
                        confidence=min(confidence, 1.0),
                    ))
        
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            return [], []
        
        return entities, relationships
    
    def _extract_with_pattern(self, chunk: dict[str, Any]) -> tuple[list[Entity], list[Relationship]]:
        """Extract entities using pattern matching (fallback)."""
        extractor = self._get_pattern_extractor()
        return extractor.extract_from_chunk(chunk)
    
    async def extract_batch(
        self, 
        chunks: list[dict[str, Any]]
    ) -> dict[str, int]:
        """Extract entities from a batch of chunks.
        
        Args:
            chunks: List of document chunks
            
        Returns:
            Statistics dict
        """
        total_entities = 0
        total_relationships = 0
        
        for i in range(0, len(chunks), self.batch_size):
            batch = chunks[i:i + self.batch_size]
            
            for chunk in batch:
                entities, relationships = await self.extract_from_chunk(chunk)
                
                added_entities = self.graph_store.add_entities(entities)
                added_rels = self.graph_store.add_relationships(
                    [r for r in relationships if r.confidence >= self.min_confidence]
                )
                
                total_entities += added_entities
                total_relationships += added_rels
        
        self.graph_store._save()
        
        return {
            "entities_added": total_entities,
            "relationships_added": total_relationships,
            "chunks_processed": len(chunks),
        }
