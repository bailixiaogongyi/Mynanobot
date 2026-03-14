"""Hybrid retriever combining BM25, vector search, and time filtering."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

import jieba
from rank_bm25 import BM25Okapi

if TYPE_CHECKING:
    import chromadb
    from sentence_transformers import SentenceTransformer

from nanobot.knowledge.bm25_persist import BM25Persist
from nanobot.knowledge.cache import QueryCache

logger = logging.getLogger(__name__)


@runtime_checkable
class EmbedderProtocol(Protocol):
    """Protocol for embedding models."""

    def encode(self, texts: list[str], normalize_embeddings: bool = False) -> Any:
        """Encode texts to embeddings."""
        ...


class HybridRetriever:
    """Hybrid retriever combining BM25, vector search, and time filtering.

    This class provides a unified retrieval interface that combines:
    - BM25 keyword search for exact matching
    - Semantic vector search for conceptual similarity
    - Time range filtering for temporal queries
    - RRF (Reciprocal Rank Fusion) for result merging

    Attributes:
        persist_dir: Directory for persistent storage.
        model_name: Name of the embedding model.
        use_bm25: Whether to use BM25 search.
        use_vector: Whether to use vector search.
        rrf_k: RRF fusion parameter k.
    """

    DEFAULT_MODEL = "BAAI/bge-small-zh-v1.5"
    DEFAULT_RRF_K = 60
    DEFAULT_CACHE_TTL = 86400
    COLLECTION_NAME = "notes"

    def __init__(
        self,
        persist_dir: Path,
        model_name: str = DEFAULT_MODEL,
        use_bm25: bool = True,
        use_vector: bool = True,
        use_graph: bool = False,
        rrf_k: int = DEFAULT_RRF_K,
        cache_enabled: bool = True,
        cache_max_size: int = 100,
        cache_ttl_seconds: int = DEFAULT_CACHE_TTL,
        use_llm_extract: bool = False,
        llm_extract_batch: int = 10,
        llm_extract_threshold: float = 0.7,
        fallback_on_llm_error: bool = True,
        provider: Any = None,
    ):
        self.persist_dir = Path(persist_dir)
        self.model_name = model_name
        self.use_bm25 = use_bm25
        self.use_vector = use_vector
        self.use_graph = use_graph
        self.rrf_k = rrf_k
        self.use_llm_extract = use_llm_extract
        self.llm_extract_batch = llm_extract_batch
        self.llm_extract_threshold = llm_extract_threshold
        self.fallback_on_llm_error = fallback_on_llm_error

        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self.bm25: BM25Okapi | None = None
        self.bm25_docs: list[dict[str, Any]] = []
        self.bm25_id_map: dict[int, str] = {}

        self._embedder: SentenceTransformer | None = None
        self._chroma: chromadb.Client | None = None
        self._collection: chromadb.Collection | None = None

        self.time_index: dict[str, float] = {}

        self._cache: QueryCache | None = None
        if cache_enabled:
            self._cache = QueryCache(
                max_size=cache_max_size,
                ttl_seconds=cache_ttl_seconds
            )

        self._bm25_persist = BM25Persist(self.persist_dir)
        
        self._graph_store = None
        self._entity_extractor = None
        if self.use_graph:
            self._init_graph(
                use_llm_extract=self.use_llm_extract,
                llm_extract_batch=self.llm_extract_batch,
                llm_extract_threshold=self.llm_extract_threshold,
                fallback_on_llm_error=self.fallback_on_llm_error,
                provider=self.provider if hasattr(self, 'provider') else None,
            )

    def _init_graph(
        self,
        use_llm_extract: bool = False,
        llm_extract_batch: int = 10,
        llm_extract_threshold: float = 0.7,
        fallback_on_llm_error: bool = True,
        provider: Any = None,
    ) -> None:
        """Initialize graph store and entity extractor.
        
        Args:
            use_llm_extract: Whether to use LLM for entity extraction
            llm_extract_batch: Batch size for LLM extraction
            llm_extract_threshold: Minimum confidence threshold
            fallback_on_llm_error: Fallback to pattern extraction on LLM error
            provider: LLM provider for extraction
        """
        try:
            from nanobot.knowledge.graph_store import GraphStore
            
            graph_path = self.persist_dir / "graph.json"
            self._graph_store = GraphStore(graph_path)
            
            if use_llm_extract and provider:
                from nanobot.knowledge.llm_extractor import LLMEntityExtractor
                self._entity_extractor = LLMEntityExtractor(
                    graph_store=self._graph_store,
                    provider=provider,
                    use_llm=True,
                    batch_size=llm_extract_batch,
                    min_confidence=llm_extract_threshold,
                    fallback_on_error=fallback_on_llm_error,
                )
                logger.info(f"GraphRAG initialized with LLM extraction")
            else:
                from nanobot.knowledge.entity_extractor import EntityExtractor
                self._entity_extractor = EntityExtractor(self._graph_store)
                logger.info(f"GraphRAG initialized with pattern extraction")
            
            logger.info(f"GraphRAG stats: {self._graph_store.get_stats()}")
        except Exception as e:
            logger.warning(f"Failed to initialize GraphRAG: {e}")
            self.use_graph = False

    def _get_embedder(self) -> SentenceTransformer:
        """Lazily load the embedding model."""
        if self._embedder is None:
            try:
                import os
                from sentence_transformers import SentenceTransformer

                # Support HuggingFace mirror for users in China
                hf_endpoint = os.environ.get("HF_ENDPOINT", "https://huggingface.co")
                if hf_endpoint != "https://huggingface.co":
                    logger.info(f"Using HuggingFace mirror: {hf_endpoint}")

                logger.info(f"Loading embedding model: {self.model_name}")
                self._embedder = SentenceTransformer(self.model_name, device="cpu")
                logger.info("Embedding model loaded successfully")
            except ImportError as e:
                raise ImportError(
                    "sentence-transformers is required for vector search. "
                    "Install it with: pip install sentence-transformers"
                ) from e
        return self._embedder

    def _get_collection(self) -> chromadb.Collection:
        """Get or create ChromaDB collection."""
        if self._collection is None:
            try:
                import chromadb
                from chromadb.config import Settings

                self._chroma = chromadb.PersistentClient(
                    path=str(self.persist_dir / "chroma"),
                    settings=Settings(anonymized_telemetry=False)
                )
                self._collection = self._chroma.get_or_create_collection(
                    name=self.COLLECTION_NAME,
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info(f"ChromaDB collection '{self.COLLECTION_NAME}' ready")
            except ImportError as e:
                raise ImportError(
                    "chromadb is required for vector search. "
                    "Install it with: pip install chromadb"
                ) from e
        return self._collection

    def index_documents(self, docs: list[dict[str, Any]]) -> dict[str, int]:
        """Index documents for both BM25 and vector search.

        Args:
            docs: List of documents with keys:
                - id: Unique document identifier
                - content: Document text content
                - metadata: Optional metadata dict
                - timestamp: Optional Unix timestamp

        Returns:
            Dict with 'indexed' count.
        """
        if not docs:
            return {"indexed": 0}

        contents = [d["content"] for d in docs]
        doc_ids = [d["id"] for d in docs]

        if self.use_bm25:
            logger.info(f"Building BM25 index for {len(docs)} documents...")
            tokenized = [list(jieba.cut(c)) for c in contents]
            self.bm25 = BM25Okapi(tokenized)
            self.bm25_docs = docs
            self.bm25_id_map = {i: doc_ids[i] for i in range(len(docs))}

            self._bm25_persist.save(self.bm25, self.bm25_docs, self.bm25_id_map)
            logger.info("BM25 index built and saved")

        if self.use_vector:
            logger.info(f"Building vector index for {len(docs)} documents...")
            embedder = self._get_embedder()
            embeddings = embedder.encode(contents, normalize_embeddings=True)

            collection = self._get_collection()

            unique_ids = list(dict.fromkeys(doc_ids))
            if unique_ids:
                try:
                    existing_ids = set(collection.get(ids=unique_ids)["ids"])
                except Exception as e:
                    logger.warning(f"Failed to get existing IDs, reindexing: {e}")
                    existing_ids = set()
            else:
                existing_ids = set()
            
            new_ids = [doc_id for doc_id in doc_ids if doc_id not in existing_ids]

            if new_ids:
                new_indices = [doc_ids.index(doc_id) for doc_id in new_ids]
                collection.add(
                    ids=new_ids,
                    embeddings=[embeddings.tolist()[i] for i in new_indices],
                    documents=[contents[i] for i in new_indices],
                    metadatas=[
                        {
                            **docs[i].get("metadata", {}),
                            "timestamp": docs[i].get("timestamp", 0)
                        }
                        for i in new_indices
                    ]
                )
            logger.info(f"Vector index updated: {len(new_ids)} new documents")

        if self.use_graph and self._entity_extractor:
            logger.info(f"Extracting entities and relationships for {len(docs)} documents...")
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    logger.warning("Graph extraction skipped: cannot run async function in sync context")
                else:
                    graph_stats = asyncio.run(self._entity_extractor.extract_batch(docs))
                    logger.info(f"Graph extracted: {graph_stats}")
            except Exception as e:
                logger.warning(f"Graph extraction failed: {e}")

        for d in docs:
            self.time_index[d["id"]] = d.get("timestamp", 0)

        return {"indexed": len(docs)}

    def load_indexes(self) -> bool:
        """Load existing indexes from disk.

        Returns:
            True if indexes were loaded successfully.
        """
        if self.use_bm25:
            result = self._bm25_persist.load()
            if result:
                self.bm25, self.bm25_docs, self.bm25_id_map = result
                for d in self.bm25_docs:
                    self.time_index[d["id"]] = d.get("timestamp", 0)
                logger.info(f"BM25 index loaded: {len(self.bm25_docs)} documents")
                return True

        if self.use_vector:
            try:
                collection = self._get_collection()
                count = collection.count()
                if count > 0:
                    logger.info(f"Vector index available: {count} documents")
                    return True
            except Exception as e:
                logger.warning(f"Failed to load vector index: {e}")

        return False

    def search(
        self,
        query: str,
        top_k: int = 5,
        time_range: tuple[float, float] | None = None,
        search_type: str = "auto"
    ) -> list[dict[str, Any]]:
        """Search documents using the specified strategy.

        Args:
            query: Search query text.
            top_k: Number of results to return.
            time_range: Optional (start_ts, end_ts) tuple for time filtering.
            search_type: Search strategy:
                - "keyword": BM25 keyword search only
                - "semantic": Vector semantic search only
                - "time": Time range search only
                - "auto": Hybrid search with RRF fusion

        Returns:
            List of result dicts with keys:
                - id: Document ID
                - content: Document content
                - metadata: Document metadata
                - score: Relevance score
        """
        if self._cache:
            cached = self._cache.get(query, search_type, time_range)
            if cached:
                return cached[:top_k]

        if search_type == "keyword":
            results = self._bm25_search(query, top_k, time_range)
        elif search_type == "semantic":
            results = self._vector_search(query, top_k, time_range)
        elif search_type == "time":
            results = self._time_search(time_range, top_k)
        else:
            results = self._hybrid_search(query, top_k, time_range)

        if self._cache and results:
            self._cache.set(query, search_type, time_range, results)
        
        if self.use_graph and self._graph_store:
            try:
                graph_results = self._graph_search(query, top_k)
                if graph_results:
                    results = self._merge_with_graph(results, graph_results, top_k)
            except Exception as e:
                logger.warning(f"Graph search failed: {e}")

        return results[:top_k]

    def _bm25_search(
        self,
        query: str,
        top_k: int,
        time_range: tuple[float, float] | None
    ) -> list[dict[str, Any]]:
        """BM25 keyword search."""
        if self.bm25 is None:
            logger.warning("BM25 index not initialized")
            return []

        query_tokens = list(jieba.cut(query))
        scores = self.bm25.get_scores(query_tokens)

        results = []
        for idx, score in enumerate(scores):
            doc_id = self.bm25_id_map.get(idx)
            if doc_id is None:
                continue

            if time_range:
                doc_ts = self.time_index.get(doc_id, 0)
                if not (time_range[0] <= doc_ts <= time_range[1]):
                    continue

            results.append({
                "id": doc_id,
                "content": self.bm25_docs[idx]["content"],
                "metadata": self.bm25_docs[idx].get("metadata", {}),
                "bm25_score": float(score),
                "rank": 0
            })

        results.sort(key=lambda x: x["bm25_score"], reverse=True)
        for i, r in enumerate(results[:top_k * 2]):
            r["rank"] = i + 1

        return results[:top_k]

    def _vector_search(
        self,
        query: str,
        top_k: int,
        time_range: tuple[float, float] | None
    ) -> list[dict[str, Any]]:
        """Vector semantic search."""
        try:
            collection = self._get_collection()
            embedder = self._get_embedder()

            query_embedding = embedder.encode([query], normalize_embeddings=True)

            where_filter = None
            if time_range:
                where_filter = {
                    "timestamp": {
                        "$gte": time_range[0],
                        "$lte": time_range[1]
                    }
                }

            results = collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=top_k * 2,
                where=where_filter
            )

            formatted = []
            for i in range(len(results["ids"][0])):
                formatted.append({
                    "id": results["ids"][0][i],
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "vector_score": 1 - results["distances"][0][i],
                    "rank": i + 1
                })

            return formatted[:top_k]
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    def _hybrid_search(
        self,
        query: str,
        top_k: int,
        time_range: tuple[float, float] | None
    ) -> list[dict[str, Any]]:
        """Hybrid search with RRF fusion and result pre-checking."""
        bm25_results = []
        vector_results = []

        if self.use_bm25:
            bm25_results = self._bm25_search(query, top_k * 2, time_range)

        if self.use_vector:
            vector_results = self._vector_search(query, top_k * 2, time_range)

        if not bm25_results and not vector_results:
            return []

        if not bm25_results:
            return vector_results[:top_k]

        if not vector_results:
            return bm25_results[:top_k]

        return self._rrf_merge(bm25_results, vector_results, top_k)

    def _rrf_merge(
        self,
        bm25_results: list[dict[str, Any]],
        vector_results: list[dict[str, Any]],
        top_k: int
    ) -> list[dict[str, Any]]:
        """RRF (Reciprocal Rank Fusion) merge."""
        scores: dict[str, float] = {}
        doc_info: dict[str, dict[str, Any]] = {}

        for doc in bm25_results:
            doc_id = doc["id"]
            rank = doc.get("rank", 1)
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (self.rrf_k + rank)
            doc_info[doc_id] = doc

        for doc in vector_results:
            doc_id = doc["id"]
            rank = doc.get("rank", 1)
            scores[doc_id] = scores.get(doc_id, 0) + 1 / (self.rrf_k + rank)
            if doc_id not in doc_info:
                doc_info[doc_id] = doc

        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        results = []
        for doc_id in sorted_ids[:top_k]:
            doc = doc_info[doc_id].copy()
            doc["rrf_score"] = scores[doc_id]
            doc["score"] = scores[doc_id]
            results.append(doc)

        return results

    def _time_search(
        self,
        time_range: tuple[float, float] | None,
        top_k: int
    ) -> list[dict[str, Any]]:
        """Time range search."""
        if not time_range:
            return []

        results = []
        for doc in self.bm25_docs:
            doc_id = doc["id"]
            doc_ts = self.time_index.get(doc_id, 0)

            if time_range[0] <= doc_ts <= time_range[1]:
                results.append({
                    "id": doc_id,
                    "content": doc["content"],
                    "metadata": doc.get("metadata", {}),
                    "timestamp": doc_ts
                })

        results.sort(key=lambda x: x["timestamp"], reverse=True)
        return results[:top_k]

    def clear(self) -> None:
        """Clear all indexes."""
        self.bm25 = None
        self.bm25_docs = []
        self.bm25_id_map = {}
        self.time_index = {}

        if self._collection:
            try:
                self._chroma.delete_collection(self.COLLECTION_NAME)
                self._collection = None
            except Exception:
                pass

        self._bm25_persist.clear()

        if self._cache:
            self._cache.clear()

        logger.info("All indexes cleared")

    def get_stats(self) -> dict[str, Any]:
        """Get index statistics."""
        stats = {
            "bm25_docs": len(self.bm25_docs) if self.bm25_docs else 0,
            "bm25_enabled": self.use_bm25,
            "vector_enabled": self.use_vector,
            "model_name": self.model_name,
        }

        if self.use_vector:
            try:
                collection = self._get_collection()
                stats["vector_docs"] = collection.count()
            except Exception:
                stats["vector_docs"] = 0

        if self._cache:
            stats["cache_size"] = len(self._cache._cache)
        
        if self.use_graph and self._graph_store:
            stats["graph"] = self._graph_store.get_stats()
        
        return stats
    
    def _graph_search(self, query: str, top_k: int) -> list[dict[str, Any]]:
        """Search using graph knowledge.
        
        Args:
            query: Search query
            top_k: Number of results
            
        Returns:
            List of graph-based results
        """
        if not self._graph_store:
            return []
        
        results = []
        
        entities = self._graph_store.find_entity(query)
        for entity in entities[:top_k]:
            related = self._graph_store.get_related_entities(entity.name)
            for related_entity, relation in related:
                results.append({
                    "id": f"graph:{entity.name}:{related_entity}",
                    "content": f"{entity.name} -> {relation} -> {related_entity}",
                    "metadata": {
                        "type": "graph_relation",
                        "entity": entity.name,
                        "entity_type": entity.entity_type,
                        "related_entity": related_entity,
                        "relationship": relation,
                        "source": entity.source_file,
                    },
                    "score": 0.9,
                })
        
        return results
    
    def _merge_with_graph(
        self, 
        results: list[dict[str, Any]], 
        graph_results: list[dict[str, Any]],
        top_k: int
    ) -> list[dict[str, Any]]:
        """Merge hybrid search results with graph results using RRF.
        
        Args:
            results: Existing search results
            graph_results: Graph-based results
            top_k: Final number of results
            
        Returns:
            Merged and ranked results
        """
        if not results:
            return graph_results[:top_k]
        
        merged = {}
        
        for r in results:
            doc_id = r.get("id", "")
            merged[doc_id] = r
        
        for gr in graph_results:
            doc_id = gr.get("id", "")
            if doc_id in merged:
                merged[doc_id]["score"] = (merged[doc_id]["score"] + gr.get("score", 0)) / 2
                merged[doc_id]["metadata"]["graph_enhanced"] = True
                if "graph_relation" in gr.get("metadata", {}):
                    merged[doc_id]["metadata"]["graph_relation"] = gr["metadata"]["graph_relation"]
            else:
                merged[doc_id] = gr
        
        sorted_results = sorted(merged.values(), key=lambda x: x.get("score", 0), reverse=True)
        
        return sorted_results[:top_k]
