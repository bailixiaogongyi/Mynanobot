"""Knowledge management module for hybrid retrieval.

This module provides a hybrid retrieval system combining:
- BM25 keyword search (exact matching)
- Semantic vector search (bge-small-zh-v1.5)
- Time range filtering
- RRF (Reciprocal Rank Fusion) for result merging
- Lightweight GraphRAG for entity/relationship extraction
- LLM-based entity extraction (optional)
"""

from nanobot.knowledge.hybrid_retriever import HybridRetriever
from nanobot.knowledge.note_processor import NoteProcessor
from nanobot.knowledge.bm25_persist import BM25Persist
from nanobot.knowledge.incremental_indexer import IncrementalIndexer
from nanobot.knowledge.cache import QueryCache
from nanobot.knowledge.graph_store import GraphStore, Entity, Relationship
from nanobot.knowledge.entity_extractor import EntityExtractor
from nanobot.knowledge.llm_extractor import LLMEntityExtractor

__all__ = [
    "HybridRetriever",
    "NoteProcessor",
    "BM25Persist",
    "IncrementalIndexer",
    "QueryCache",
    "GraphStore",
    "Entity",
    "Relationship",
    "EntityExtractor",
    "LLMEntityExtractor",
]
