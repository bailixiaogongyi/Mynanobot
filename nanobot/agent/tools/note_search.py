"""Note search tool for hybrid retrieval."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from nanobot.agent.tools.base import Tool

if TYPE_CHECKING:
    from nanobot.knowledge.hybrid_retriever import HybridRetriever

logger = logging.getLogger(__name__)


class NoteSearchTool(Tool):
    """Tool for searching notes using hybrid retrieval.

    This tool provides search capabilities combining:
    - BM25 keyword search for exact matching
    - Semantic vector search for conceptual similarity
    - Time range filtering for temporal queries
    """

    def __init__(self, retriever: HybridRetriever):
        self.retriever = retriever

    @property
    def name(self) -> str:
        return "search_notes"

    @property
    def description(self) -> str:
        return (
            "从笔记中搜索相关信息。"
            "支持关键词搜索、语义搜索和时间范围过滤。"
            "可以找到项目笔记、个人笔记、主题笔记等。"
            "Use this tool when you need to find information from the user's notes."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询，描述你想找的内容 (Search query describing what you want to find)"
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回结果数量 (Number of results to return)",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 20
                },
                "search_type": {
                    "type": "string",
                    "description": "搜索类型 (Search type): keyword(关键词精确匹配), semantic(语义理解), auto(自动混合)",
                    "enum": ["keyword", "semantic", "auto"],
                    "default": "auto"
                },
                "time_range": {
                    "type": "string",
                    "description": (
                        "时间范围过滤 (Time range filter)，如: "
                        "'最近7天'、'上周'、'本周'、'2026年2月'"
                    )
                }
            },
            "required": ["query"]
        }

    async def execute(
        self,
        query: str,
        top_k: int = 5,
        search_type: str = "auto",
        time_range: str | None = None
    ) -> str:
        """Execute note search.

        Args:
            query: Search query text.
            top_k: Number of results to return.
            search_type: Search strategy (keyword/semantic/auto).
            time_range: Optional time range string.

        Returns:
            Formatted search results.
        """
        logger.info(f"Note search: query='{query[:50]}...', type={search_type}")

        parsed_time_range = None
        if time_range:
            parsed_time_range = self._parse_time_range(time_range)
            if parsed_time_range is None:
                logger.warning(f"Failed to parse time range: {time_range}")

        try:
            results = self.retriever.search(
                query=query,
                top_k=top_k,
                time_range=parsed_time_range,
                search_type=search_type
            )
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return f"搜索失败: {str(e)}"

        if not results:
            return "未找到相关笔记内容。\n\n建议:\n- 尝试使用不同的关键词\n- 检查搜索类型是否正确\n- 确认笔记已被索引"

        return self._format_results(results)

    def _format_results(self, results: list[dict[str, Any]]) -> str:
        """Format search results for display.

        Args:
            results: List of search result dicts.

        Returns:
            Formatted string output.
        """
        output = ["## 搜索结果\n"]

        for i, r in enumerate(results, 1):
            metadata = r.get("metadata", {})
            title = metadata.get("title", "")
            source = metadata.get("source", "未知")
            score = r.get("rrf_score", r.get("bm25_score", r.get("vector_score", 0)))

            if isinstance(score, float):
                score_str = f"{score:.4f}"
            else:
                score_str = str(score)

            content = r.get("content", "")
            content_preview = content[:500] + "..." if len(content) > 500 else content

            output.append(f"### {i}. {title or '无标题'}")
            output.append(f"- **来源**: `{source}`")
            output.append(f"- **相关性**: {score_str}")
            output.append(f"\n```\n{content_preview}\n```\n")
            output.append("---\n")

        return "\n".join(output)

    def _parse_time_range(self, time_str: str) -> tuple[float, float] | None:
        """Parse time range string to timestamp tuple.

        Supports formats:
        - "最近N天" / "过去N天"
        - "上周"
        - "本周" / "这周"
        - "YYYY年M月"

        Args:
            time_str: Time range string.

        Returns:
            Tuple of (start_ts, end_ts) or None if parsing fails.
        """
        now = datetime.now()

        if "最近" in time_str or "过去" in time_str:
            match = re.search(r'(\d+)天', time_str)
            if match:
                days = int(match.group(1))
                start = now - timedelta(days=days)
                return (start.timestamp(), now.timestamp())

        if "上周" in time_str:
            start = now - timedelta(days=now.weekday() + 7)
            end = start + timedelta(days=7)
            return (start.timestamp(), end.timestamp())

        if "本周" in time_str or "这周" in time_str:
            start = now - timedelta(days=now.weekday())
            return (start.timestamp(), now.timestamp())

        year_month_match = re.match(r'(\d{4})年(\d{1,2})月', time_str)
        if year_month_match:
            try:
                year = int(year_month_match.group(1))
                month = int(year_month_match.group(2))
                start = datetime(year, month, 1)
                if month == 12:
                    end = datetime(year + 1, 1, 1)
                else:
                    end = datetime(year, month + 1, 1)
                return (start.timestamp(), end.timestamp())
            except ValueError:
                pass

        days_match = re.match(r'(\d+)天', time_str)
        if days_match:
            days = int(days_match.group(1))
            start = now - timedelta(days=days)
            return (start.timestamp(), now.timestamp())

        return None


class NoteIndexTool(Tool):
    """Tool for indexing notes."""

    def __init__(
        self,
        retriever: HybridRetriever,
        workspace_path: Any,
        notes_dirs: list[str]
    ):
        self.retriever = retriever
        self.workspace_path = workspace_path
        self.notes_dirs = notes_dirs

    @property
    def name(self) -> str:
        return "index_notes"

    @property
    def description(self) -> str:
        return (
            "索引工作空间中的笔记文件。"
            "当用户添加新笔记或需要更新索引时使用此工具。"
            "Index notes in the workspace for search."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "要索引的目录名称 (Directory to index), 如 'daily', 'projects'。留空则索引所有目录。"
                },
                "force": {
                    "type": "boolean",
                    "description": "是否强制重建索引 (Force reindex)",
                    "default": False
                }
            },
            "required": []
        }

    async def execute(
        self,
        directory: str | None = None,
        force: bool = False
    ) -> str:
        """Execute note indexing.

        Args:
            directory: Optional specific directory to index.
            force: Whether to force reindex.

        Returns:
            Indexing result message.
        """
        from nanobot.knowledge.note_processor import NoteProcessor
        from nanobot.knowledge.incremental_indexer import IncrementalIndexer

        processor = NoteProcessor()
        indexer = IncrementalIndexer(self.retriever.persist_dir)

        dirs_to_index = []
        if directory:
            dir_path = self.workspace_path / directory
            if dir_path.exists():
                dirs_to_index = [dir_path]
            else:
                return f"目录不存在: {directory}"
        else:
            for note_dir in self.notes_dirs:
                dir_path = self.workspace_path / note_dir
                if dir_path.exists():
                    dirs_to_index.append(dir_path)

        if not dirs_to_index:
            return "未找到可索引的目录"

        all_chunks = []
        total_files = 0

        for dir_path in dirs_to_index:
            if force:
                chunks = processor.process_directory(dir_path)
            else:
                import pathlib
                files = list(dir_path.rglob("*.md")) + list(dir_path.rglob("*.txt"))
                changed, _ = indexer.get_changed_files(files)
                if changed:
                    chunks = processor.process_files(changed)
                else:
                    chunks = []

            all_chunks.extend(chunks)
            total_files += len(set(c["metadata"]["source"] for c in chunks)) if chunks else 0

        if not all_chunks:
            return "没有需要索引的新文件"

        result = self.retriever.index_documents(all_chunks)

        return f"索引完成: {result['indexed']} 个文档块，来自 {total_files} 个文件"
