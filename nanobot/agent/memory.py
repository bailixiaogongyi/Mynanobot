"""Memory system for persistent agent memory."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generator

from loguru import logger

from nanobot.utils.helpers import ensure_dir, get_data_path

if TYPE_CHECKING:
    from nanobot.providers.base import LLMProvider
    from nanobot.session.manager import Session
    from nanobot.knowledge.hybrid_retriever import HybridRetriever


def _glob_md_files(directory: Path, max_depth: int = 10) -> Generator[Path, None, None]:
    """Recursively find .md files with depth limit.
    
    Args:
        directory: The directory to search in.
        max_depth: Maximum directory depth to traverse (default 10).
    
    Yields:
        Path objects for .md files.
    """
    def _scan(path: Path, current_depth: int):
        if current_depth > max_depth:
            return
        try:
            for item in path.iterdir():
                if item.is_file() and item.suffix == ".md":
                    yield item
                elif item.is_dir() and not item.name.startswith("."):
                    yield from _scan(item, current_depth + 1)
        except PermissionError:
            pass
    
    if directory.exists() and directory.is_dir():
        yield from _scan(directory, 0)


_SAVE_MEMORY_TOOL = [
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "Save the memory consolidation result to persistent storage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "history_entry": {
                        "type": "string",
                        "description": "A paragraph (2-5 sentences) summarizing key events/decisions/topics. "
                        "Start with [YYYY-MM-DD HH:MM]. Include detail useful for grep search.",
                    },
                    "memory_update": {
                        "type": "string",
                        "description": "Full updated long-term memory as markdown. Include all existing "
                        "facts plus new ones. Return unchanged if nothing new.",
                    },
                },
                "required": ["history_entry", "memory_update"],
            },
        },
    }
]


class KnowledgeManager:
    """Manager for knowledge retrieval integration.

    This class provides a bridge between the existing memory system
    and the new hybrid retrieval system.
    """

    def __init__(
        self,
        workspace: Path,
        config: Any | None = None
    ):
        self.workspace = workspace
        self.config = config
        self._retriever: HybridRetriever | None = None
        self._initialized = False

    @property
    def retriever(self) -> HybridRetriever | None:
        """Get the hybrid retriever (lazy initialization)."""
        return self._retriever

    def initialize(self) -> bool:
        """Initialize the knowledge retrieval system.

        Returns:
            True if initialization succeeded.
        """
        if self._initialized:
            return self._retriever is not None

        try:
            from nanobot.knowledge.hybrid_retriever import HybridRetriever

            model_name = "BAAI/bge-small-zh-v1.5"
            use_bm25 = True
            use_vector = True
            use_graph = False
            rrf_k = 60
            cache_enabled = True
            persist_dir = get_data_path() / "knowledge"

            if self.config:
                index_config = getattr(self.config, 'index', None)
                if index_config:
                    model_name = getattr(index_config, 'embedding_model', model_name)
                    use_bm25 = getattr(index_config, 'use_bm25', use_bm25)
                    use_vector = getattr(index_config, 'use_vector', use_vector)
                    use_graph = getattr(index_config, 'use_graph', use_graph)
                    rrf_k = getattr(index_config, 'rrf_k', rrf_k)
                    config_persist_dir = getattr(index_config, 'persist_dir', None)
                    if config_persist_dir:
                        persist_dir = Path(config_persist_dir).expanduser()
                search_config = getattr(self.config, 'search', None)
                if search_config:
                    cache_enabled = getattr(search_config, 'cache_enabled', cache_enabled)

            self._retriever = HybridRetriever(
                persist_dir=persist_dir,
                model_name=model_name,
                use_bm25=use_bm25,
                use_vector=use_vector,
                use_graph=use_graph,
                rrf_k=rrf_k,
                cache_enabled=cache_enabled
            )

            self._retriever.load_indexes()

            self._initialized = True
            logger.info("Knowledge manager initialized")
            return True

        except ImportError as e:
            logger.warning(f"Knowledge dependencies not installed: {e}")
            self._initialized = True
            return False
        except Exception as e:
            logger.error(f"Failed to initialize knowledge manager: {e}")
            self._initialized = True
            return False

    def is_enabled(self) -> bool:
        """Check if knowledge retrieval is enabled and available."""
        if not self._initialized:
            self.initialize()
        return self._retriever is not None

    def search(
        self,
        query: str,
        top_k: int = 5,
        search_type: str = "auto",
        time_range: tuple[float, float] | None = None
    ) -> list[dict[str, Any]]:
        """Search knowledge base.

        Args:
            query: Search query.
            top_k: Number of results.
            search_type: Search type (keyword/semantic/auto).
            time_range: Optional time range filter.

        Returns:
            List of search results.
        """
        if not self.is_enabled():
            return []

        return self._retriever.search(
            query=query,
            top_k=top_k,
            time_range=time_range,
            search_type=search_type
        )

    def index_notes(self, notes_dirs: list[str] | None = None) -> dict[str, int]:
        """Index notes from specified directories.

        Args:
            notes_dirs: List of directory names to index.

        Returns:
            Dict with indexing statistics.
        """
        if not self.is_enabled():
            return {"indexed": 0, "error": "Knowledge system not initialized"}

        from nanobot.knowledge.note_processor import NoteProcessor

        if notes_dirs is None:
            notes_dirs = ["daily", "projects", "personal", "topics", "pending"]

        processor = NoteProcessor()
        all_chunks = []
        total_files = 0

        for note_dir in notes_dirs:
            dir_path = self.workspace / note_dir
            if dir_path.exists():
                chunks = processor.process_directory(dir_path)
                all_chunks.extend(chunks)
                total_files += len(set(c["metadata"]["source"] for c in chunks)) if chunks else 0

        if all_chunks:
            result = self._retriever.index_documents(all_chunks)
            result["files"] = total_files
            return result

        return {"indexed": 0, "files": 0}

    def get_stats(self) -> dict[str, Any]:
        """Get knowledge system statistics."""
        if not self.is_enabled():
            return {"enabled": False}

        stats = self._retriever.get_stats()
        stats["enabled"] = True
        return stats


class MemoryStore:
    """Enhanced memory with layered management and RAG support.

    Layers:
    - Working Memory: LRU cache for fast access
    - Session Memory: Temporary file storage
    - Long-term Memory: Persistent storage + RAG
    """

    def __init__(self, workspace: Path, config: Any | None = None):
        self.memory_dir = ensure_dir(workspace / "memory")
        self.memory_file = self.memory_dir / "MEMORY.md"
        self.history_file = self.memory_dir / "HISTORY.md"
        self.workspace = workspace

        from nanobot.agent.mem_layer import MemoryLayer, MemoryLayerConfig
        layer_config = MemoryLayerConfig()
        if config:
            layer_config.working_mem_size = getattr(config, 'working_mem_size', 100)
            layer_config.session_mem_ttl = getattr(config, 'session_mem_ttl', 3600)
        self._layer = MemoryLayer(workspace, layer_config)

        from nanobot.agent.mem_indexer import IndexState
        state_file = get_data_path() / "knowledge" / "index_state.json"
        self._index_state = IndexState(state_file)
        self._background_indexer = None

        self._knowledge: KnowledgeManager | None = None
        self._config = config

    @property
    def knowledge(self) -> KnowledgeManager:
        """Get the knowledge manager (lazy initialization)."""
        if self._knowledge is None:
            self._knowledge = KnowledgeManager(self.workspace, self._config)
        return self._knowledge

    def read_long_term(self) -> str:
        if self.memory_file.exists():
            return self.memory_file.read_text(encoding="utf-8")
        return ""

    def write_long_term(self, content: str) -> None:
        self.memory_file.write_text(content, encoding="utf-8")

    def append_history(self, entry: str) -> None:
        with open(self.history_file, "a", encoding="utf-8") as f:
            f.write(entry.rstrip() + "\n\n")

    def get_memory_context(self) -> str:
        long_term = self._layer.get("long_term") or self.read_long_term()
        if long_term:
            self._layer.set("long_term", long_term)
        return f"## Long-term Memory\n{long_term}" if long_term else ""

    async def index_notes_incremental(
        self,
        notes_dirs: list[str] | None = None,
        background: bool = True
    ) -> dict[str, Any]:
        """Incremental index notes.

        Args:
            notes_dirs: List of note directories.
            background: Whether to run in background.
        """
        if background:
            return await self._index_background(notes_dirs)
        else:
            return self._index_sync(notes_dirs)

    async def _index_background(self, notes_dirs: list[str] | None) -> dict:
        """Background indexing."""
        if self._background_indexer is None:
            retriever = self.knowledge.retriever
            if retriever:
                from nanobot.agent.mem_indexer import BackgroundIndexer
                self._background_indexer = BackgroundIndexer(retriever, self._index_state)
                await self._background_indexer.start()
            else:
                return {"status": "error", "message": "Retriever not initialized"}

        notes_dirs = notes_dirs or ["daily", "projects", "personal", "topics", "pending"]

        for note_dir in notes_dirs:
            dir_path = self.workspace / note_dir
            for md_file in _glob_md_files(dir_path):
                if self._index_state.needs_reindex(str(md_file)):
                    await self._background_indexer.add_file(str(md_file))

        return {"status": "queued", "message": "Indexing started in background"}

    def _index_sync(self, notes_dirs: list[str] | None) -> dict:
        """Synchronous indexing."""
        retriever = self.knowledge.retriever
        if not retriever:
            return {"status": "error", "message": "Retriever not initialized"}

        from nanobot.knowledge.note_processor import NoteProcessor
        processor = NoteProcessor()

        notes_dirs = notes_dirs or ["daily", "projects", "personal", "topics", "pending"]
        all_chunks = []
        total_files = 0

        for note_dir in notes_dirs:
            dir_path = self.workspace / note_dir
            for md_file in _glob_md_files(dir_path):
                if self._index_state.needs_reindex(str(md_file)):
                    chunks = processor.process_file(md_file)
                    if chunks:
                        all_chunks.extend(chunks)
                        total_files += 1

        if all_chunks:
            result = retriever.index_documents(all_chunks)
            result["files"] = total_files
            return result

        return {"indexed": 0, "files": 0}

    def get_layer_stats(self) -> dict:
        """Get memory layer statistics."""
        return self._layer.get_stats()

    def get_index_status(self) -> dict:
        """Get index status."""
        status = {"total_indexed": len(self._index_state.get_all_files())}
        if self._background_indexer:
            status["background"] = self._background_indexer.get_status()
        return status

    def get_full_context(self, include_knowledge: bool = False) -> str:
        """Get full memory context including optional knowledge search.

        Args:
            include_knowledge: Whether to include knowledge stats.

        Returns:
            Formatted memory context string.
        """
        parts = []

        memory_context = self.get_memory_context()
        if memory_context:
            parts.append(memory_context)

        if include_knowledge and self.knowledge.is_enabled():
            stats = self.knowledge.get_stats()
            if stats.get("bm25_docs", 0) > 0 or stats.get("vector_docs", 0) > 0:
                parts.append(f"## Knowledge Base\nIndexed documents: {stats.get('bm25_docs', 0)}")

        return "\n\n".join(parts) if parts else ""

    async def consolidate(
        self,
        session: Session,
        provider: LLMProvider,
        model: str,
        *,
        archive_all: bool = False,
        memory_window: int = 50,
    ) -> bool:
        """Consolidate old messages into MEMORY.md + HISTORY.md via LLM tool call.

        Returns True on success (including no-op), False on failure.
        """
        if archive_all:
            old_messages = session.messages
            keep_count = 0
            logger.info("Memory consolidation (archive_all): {} messages", len(session.messages))
        else:
            keep_count = memory_window // 2
            if len(session.messages) <= keep_count:
                return True
            if len(session.messages) - session.last_consolidated <= 0:
                return True
            old_messages = session.messages[session.last_consolidated:-keep_count]
            if not old_messages:
                return True
            logger.info("Memory consolidation: {} to consolidate, {} keep", len(old_messages), keep_count)

        lines = []
        for m in old_messages:
            if not m.get("content"):
                continue
            role = m.get("role", "unknown")
            timestamp = m.get("timestamp", "?")[:16] if m.get("timestamp") else "?"
            content = m.get("content", "")
            tools = f" [tools: {', '.join(m['tools_used'])}]" if m.get("tools_used") else ""
            lines.append(f"[{timestamp}] {role.upper()}{tools}: {content}")

        current_memory = self.read_long_term()
        prompt = f"""Process this conversation and call the save_memory tool with your consolidation.

## Current Long-term Memory
{current_memory or "(empty)"}

## Conversation to Process
{chr(10).join(lines)}"""

        try:
            response = await provider.chat(
                messages=[
                    {"role": "system", "content": "You are a memory consolidation agent. Call the save_memory tool with your consolidation of the conversation."},
                    {"role": "user", "content": prompt},
                ],
                tools=_SAVE_MEMORY_TOOL,
                model=model,
            )

            if not response.has_tool_calls:
                logger.warning("Memory consolidation: LLM did not call save_memory, skipping")
                return False

            args = response.tool_calls[0].arguments
            if isinstance(args, str):
                args = json.loads(args)
            if not isinstance(args, dict):
                logger.warning("Memory consolidation: unexpected arguments type {}", type(args).__name__)
                return False

            if entry := args.get("history_entry"):
                if not isinstance(entry, str):
                    entry = json.dumps(entry, ensure_ascii=False)
                self.append_history(entry)
            if update := args.get("memory_update"):
                if not isinstance(update, str):
                    update = json.dumps(update, ensure_ascii=False)
                if update != current_memory:
                    self.write_long_term(update)

            session.last_consolidated = 0 if archive_all else len(session.messages) - keep_count
            logger.info("Memory consolidation done: {} messages, last_consolidated={}", len(session.messages), session.last_consolidated)
            return True
        except Exception:
            logger.exception("Memory consolidation failed")
            return False
